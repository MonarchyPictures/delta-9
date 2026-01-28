import logging
import os
import uuid
import socket
import json
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timedelta
from app.db import models, database
from app.db.database import get_db
from app.utils.outreach import OutreachEngine
from app.utils.geo_service import GeoService
from app.utils.market_service import MarketIntelligenceService
from app.utils.normalization import LeadValidator
from app.nlp.intent_service import BuyingIntentNLP
from app.nlp.keyword_expansion import KeywordExpander
from app.nlp.ranking_engine import RankingEngine
from app.nlp.demand_forecaster import DemandForecaster
from app.nlp.duplicate_detector import DuplicateDetector
from app.core.compliance import ComplianceManager

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Buying Intent Radar API")

# CORS Configuration - Permissive for development
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize NLP and Services (Instances used for stateless operations)
nlp = BuyingIntentNLP()
geo = GeoService()
market = MarketIntelligenceService()
validator = LeadValidator()
expander = KeywordExpander()
ranker = RankingEngine()
detector = DuplicateDetector()

@app.delete("/leads/{lead_id}")
def delete_lead(lead_id: str, db: Session = Depends(get_db)):
    try:
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        db.delete(lead)
        db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting lead: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete lead")

@app.get("/health")
def health_check():
    """System health check including Redis/Celery status and system metrics."""
    import psutil
    import time
    
    health = {
        "status": "healthy", 
        "services": {"database": "up"},
        "metrics": {
            "memory_usage": f"{psutil.virtual_memory().percent}%",
            "cpu_usage": f"{psutil.cpu_percent()}%",
            "uptime_seconds": int(time.time() - psutil.boot_time())
        }
    }
    try:
        from app.core.celery_worker import celery_app
        broker_url = celery_app.conf.broker_url
        
        # Fast check: Is the broker reachable?
        if broker_url.startswith("redis"):
            if check_redis():
                health["services"]["celery"] = "up (Redis)"
            else:
                # If redis failed, it might have fallen back to sqla
                from app.core.celery_worker import FALLBACK_BROKER_URL
                if celery_app.conf.broker_url == FALLBACK_BROKER_URL:
                    health["services"]["celery"] = "up (SQLite Fallback)"
                else:
                    health["services"]["celery"] = "down"
                    health["status"] = "degraded"
        elif "sqlite" in broker_url or "sqla" in broker_url:
            health["services"]["celery"] = "up (SQLite)"
        else:
            health["services"]["celery"] = "up"
    except Exception as e:
        logger.error(f"Health check error: {e}")
        health["services"]["celery"] = "down"
        health["status"] = "degraded"
    return health

def check_redis():
    """Fast check for redis connectivity using a simple socket."""
    import socket
    from urllib.parse import urlparse
    
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    url = urlparse(redis_url)
    host = url.hostname or "127.0.0.1"
    port = url.port or 6379
    
    try:
        # 1 second timeout for socket connection
        socket.setdefaulttimeout(1.0)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def sync_scrape_and_save(query: str, location: str, db: Session):
    """Synchronous fallback: Scrape one platform and save results immediately."""
    from scraper import LeadScraper
    from app.utils.normalization import LeadValidator
    
    scraper = LeadScraper()
    validator = LeadValidator()
    
    # Try multiple platforms for better coverage in sync fallback
    platforms_to_try = ["google", "duckduckgo"]
    all_raw_results = []
    
    for platform in platforms_to_try:
        logger.info(f"SYNC FALLBACK: Scraping {platform} for '{query}' in {location}")
        try:
            if platform == "duckduckgo":
                raw_results = scraper.duckduckgo_search(query, location)
            else:
                raw_results = scraper.scrape_platform(platform, query, location)
            
            logger.info(f"SYNC FALLBACK: Found {len(raw_results)} raw results from {platform}")
            all_raw_results.extend(raw_results)
        except Exception as e:
            logger.error(f"SYNC FALLBACK: Error scraping {platform}: {e}")
    
    processed_count = 0
    try:
        for raw in all_raw_results:
            normalized = validator.normalize_lead(raw, db=db)
            if not normalized:
                logger.info(f"SYNC FALLBACK: Skipping result (normalization returned None): {raw.get('link')}")
                continue
                
            # Check for duplicates by link
            existing = db.query(models.Lead).filter(models.Lead.post_link == normalized["post_link"]).first()
            if not existing:
                lead = models.Lead(
                    id=normalized["id"],
                    source_platform=normalized["source_platform"],
                    post_link=normalized["post_link"],
                    location_raw=normalized.get("location_raw"),
                    buyer_request_snippet=normalized["buyer_request_snippet"],
                    product_category=normalized["product_category"],
                    buyer_name=normalized.get("buyer_name", "Anonymous"),
                    contact_phone=normalized.get("contact_phone"),
                    contact_email=normalized.get("contact_email"),
                    intent_score=normalized["intent_score"],
                    confidence_score=normalized["confidence_score"],
                    intent_type=normalized.get("intent_type", "BUYER"),
                    is_contact_verified=normalized.get("is_contact_verified", 0),
                    contact_reliability_score=normalized.get("contact_reliability_score", 0.0),
                    is_genuine_buyer=normalized.get("is_genuine_buyer", 1),
                    verification_badges=normalized.get("verification_badges", []),
                    status=models.CRMStatus.NEW,
                    created_at=datetime.now()
                )
                db.add(lead)
                processed_count += 1
        
        db.commit()
        return processed_count
    except Exception as e:
        logger.error(f"Sync fallback failed: {e}")
        return 0

# Initialize DB
models.Base.metadata.create_all(bind=database.engine)

# Outreach Engine Instance
outreach_engine = OutreachEngine()
compliance = ComplianceManager()

# Pydantic Schemas
class LeadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    source_platform: str
    post_link: str
    location_raw: Optional[str]
    buyer_request_snippet: str
    product_category: str
    buyer_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    intent_score: float
    confidence_score: float = 0.0
    
    # Hyper-Specific Intent Intelligence
    readiness_level: Optional[str] = "RESEARCHING"
    urgency_score: float = 0.0
    budget_info: Optional[str] = None
    product_specs: Optional[dict] = {}
    deal_probability: float = 0.0
    
    # NEW: Smart Matching
    match_score: float = 0.0
    compatibility_status: Optional[str] = None
    match_details: Optional[dict] = {}
    
    # NEW: Intent Extensions
    quantity_requirement: Optional[str] = None
    payment_method_preference: Optional[str] = None
    
    # NEW: Local Advantage
    delivery_range_score: float = 0.0
    neighborhood: Optional[str] = None
    local_pickup_preference: int = 0
    delivery_constraints: Optional[str] = None
    
    # NEW: Deal Readiness
    decision_authority: int = 0
    prior_research_indicator: int = 0
    comparison_indicator: int = 0
    upcoming_deadline: Optional[datetime] = None
    
    # Real-Time & Competitive Intelligence
    availability_status: str = "Available Now"
    competition_count: int = 0
    is_unique_request: int = 0
    optimal_response_window: Optional[str] = None
    peak_response_time: Optional[str] = None
    
    # Contact Verification & Reliability
    is_contact_verified: int = 0
    contact_reliability_score: float = 0.0
    preferred_contact_method: Optional[str] = None
    disposable_email_flag: int = 0
    contact_metadata: Optional[dict] = {}
    
    # Response Tracking System
    response_count: int = 0
    average_response_time_mins: Optional[float] = None
    last_contact_attempt: Optional[datetime] = None
    last_response_received: Optional[datetime] = None
    conversion_rate: float = 0.0
    non_response_flag: int = 0
    
    # Verification & Badges
    verification_badges: Optional[List[str]] = []
    account_age_days: Optional[int] = None
    is_genuine_buyer: int = 1
    last_activity: Optional[datetime] = None
    rank_score: Optional[float] = None
    distance_km: Optional[float] = None

    # NEW: Comprehensive Lead Intelligence
    buyer_history: Optional[dict] = None
    platform_activity_level: Optional[str] = None
    past_response_rate: Optional[float] = 0.0
    market_price_range: Optional[str] = None
    seasonal_demand: Optional[str] = None
    supply_status: Optional[str] = None
    conversion_signals: Optional[List[str]] = []
    talking_points: Optional[List[str]] = []
    competitive_advantages: Optional[List[str]] = []
    pricing_strategy: Optional[str] = None

    status: str
    is_saved: int = 0
    notes: Optional[str] = None
    created_at: datetime

class OutreachResponseSchema(BaseModel):
    lead_id: str
    response_text: str

class AgentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    name: str
    query: str
    location: str = "Kenya"
    radius: int = 50
    min_intent_score: float = 0.7
    is_active: int = 1
    enable_alerts: int = 1
    signals_count: int = 0
    created_at: Optional[datetime] = None

class NotificationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    lead_id: str
    agent_id: int
    message: str
    is_read: int
    created_at: datetime

@app.get("/")
def read_root():
    return {"status": "Radar Online", "mission": "Aggressive Lead Gen"}

@app.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Fetch core dashboard metrics."""
    try:
        total_leads = db.query(models.Lead).count()
        active_agents = db.query(models.Agent).filter(models.Agent.is_active == 1).count()
        today_activity = db.query(models.Lead).filter(
            models.Lead.created_at >= datetime.now() - timedelta(hours=24)
        ).count()
        
        return {
            "totalLeads": str(total_leads),
            "activeAgents": str(active_agents),
            "todayActivity": str(today_activity),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return {
            "totalLeads": "0",
            "activeAgents": "0",
            "todayActivity": "0",
            "status": "partial",
            "message": "Metrics partially unavailable"
        }

@app.get("/agents", response_model=List[AgentSchema])
def list_agents(db: Session = Depends(get_db)):
    try:
        agents = db.query(models.Agent).all()
        # Add signals_count to each agent object
        for agent in agents:
            try:
                agent.signals_count = db.query(models.Notification).filter(models.Notification.agent_id == agent.id).count()
            except Exception:
                agent.signals_count = 0
        return agents
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return []

@app.patch("/leads/{lead_id}/save")
def toggle_save_lead(lead_id: str, db: Session = Depends(get_db)):
    """Toggle the is_saved status of a lead."""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.is_saved = 1 if lead.is_saved == 0 else 0
    db.commit()
    return {"status": "success", "is_saved": lead.is_saved}

class LeadUpdateSchema(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    personalized_message: Optional[str] = None

@app.patch("/leads/{lead_id}")
def update_lead(lead_id: str, data: LeadUpdateSchema, db: Session = Depends(get_db)):
    """Update lead status, notes, or personalized message."""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if data.status:
        try:
            lead.status = models.ContactStatus(data.status.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {data.status}")
            
    if data.notes is not None:
        lead.notes = data.notes

    if data.personalized_message is not None:
        lead.personalized_message = data.personalized_message
        
    db.commit()
    return {"status": "success", "lead_id": lead_id}

@app.get("/notifications", response_model=List[NotificationSchema])
def list_notifications(db: Session = Depends(get_db)):
    """List all notifications."""
    try:
        notifications = db.query(models.Notification).order_by(models.Notification.created_at.desc()).all()
        return notifications
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return []

@app.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Fetch current system settings."""
    try:
        settings = db.query(models.SystemSetting).all()
        result = {}
        for s in settings:
            # Handle boolean strings/values from DB
            val = s.value
            if isinstance(val, str):
                if val.lower() == 'true': val = True
                elif val.lower() == 'false': val = False
            result[s.key] = val
            
        # Ensure defaults if not in DB
        if "notifications_enabled" not in result: result["notifications_enabled"] = True
        if "sound_enabled" not in result: result["sound_enabled"] = True
        
        return result
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        return {"notifications_enabled": True, "sound_enabled": True}

@app.post("/settings")
def update_settings(settings: dict, db: Session = Depends(get_db)):
    """Update system settings."""
    try:
        for key, value in settings.items():
            setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
            if setting:
                setting.value = value
            else:
                setting = models.SystemSetting(key=key, value=value)
                db.add(setting)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")

def generate_synthetic_leads(query: str, location: str, db: Session):
    """Generate AI-inferred demand signals based on historical patterns."""
    try:
        forecaster = DemandForecaster(db)
        # Find similar categories if the exact query yields nothing
        trends = forecaster.get_market_trends(days=30)
        
        synthetic = []
        
        # Look for categories that match the query
        matching_categories = [cat for cat in trends.keys() if query.lower() in cat.lower()]
        
        for cat in matching_categories[:3]:
            stats = forecaster.predict_demand_spikes(cat)
            if stats.get("status") != "insufficient_data":
                synthetic.append({
                    "id": f"synthetic-{uuid.uuid4().hex[:8]}",
                    "product_category": cat,
                    "buyer_request_snippet": f"High likelihood demand detected for {cat} in {location}. {stats.get('current_demand', 5)} people recently searched for this.",
                    "location_raw": location,
                    "intent_score": 0.85,
                    "readiness_level": "AI-INFERRED",
                    "confidence_score": 0.9,
                    "is_genuine_buyer": 1,
                    "timestamp": datetime.now(),
                    "is_synthetic": True,
                    "metadata": stats
                })
        
        # If still nothing, look for emerging markets
        if not synthetic:
            emerging = forecaster.get_emerging_markets()
            for market in emerging[:2]:
                synthetic.append({
                    "id": f"synthetic-{uuid.uuid4().hex[:8]}",
                    "product_category": "Trending Market",
                    "buyer_request_snippet": f"Rapidly increasing demand signal in {market['location']}. Activity up by {market['growth_index']}x.",
                    "location_raw": market['location'],
                    "intent_score": 0.8,
                    "readiness_level": "AI-INFERRED",
                    "confidence_score": 0.85,
                    "is_genuine_buyer": 1,
                    "timestamp": datetime.now(),
                    "is_synthetic": True
                })
                
        return synthetic
    except Exception as e:
        logger.error(f"Error generating synthetic leads: {e}")
        return []

@app.patch("/leads/{lead_id}/status")
def update_lead_status(lead_id: str, status: str, db: Session = Depends(get_db)):
    """Update CRM status of a lead."""
    try:
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Validate status
        try:
            lead.status = models.CRMStatus(status.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
            
        db.commit()
        return {"status": "success", "new_status": lead.status.value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating lead status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update status")

@app.get("/leads/search")
def search_leads(
    query: Optional[str] = None,
    location: str = "Kenya",
    radius: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
    hours: Optional[int] = None,
    readiness: Optional[str] = None,
    min_prob: Optional[float] = None,
    live: bool = Query(True),
    verified_only: bool = Query(False),
    smart_match: bool = Query(True),
    local_advantage: bool = False,
    is_saved: Optional[bool] = None,
    hot_only: bool = False,
    buyer_only: bool = Query(True),
    has_whatsapp: Optional[bool] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    SEARCH PIPELINE:
    User Query -> Location Processing -> Lead Search -> Hyper-Specific Filters -> Ranking Engine -> Results API
    """
    try:
        db_query = db.query(models.Lead)
        
        # Category Filter
        if category and category.lower() != "all":
            db_query = db_query.filter(models.Lead.product_category.ilike(f"%{category}%"))

        # Buyer Only Filter (Strict Intent Classifier)
        if buyer_only:
            # ENFORCEMENT: Only show leads marked as genuine buyers with high intent
            db_query = db_query.filter(models.Lead.is_genuine_buyer == 1)
            # Threshold for intent: No guessing. Must be at least 0.4 (WARM) or higher
            db_query = db_query.filter(models.Lead.intent_score >= 0.4)

        # Radius Filter (Simplistic: filter by lead's radius_km if provided)
        if radius and radius.lower() != "anywhere":
            try:
                radius_val = float(radius.replace('km', ''))
                db_query = db_query.filter(models.Lead.radius_km <= radius_val)
            except ValueError:
                pass
        
        # Hot Leads Toggle
        if hot_only:
            db_query = db_query.filter(models.Lead.intent_score >= 0.7)
            db_query = db_query.filter(models.Lead.readiness_level.in_(["HOT"]))

        # WhatsApp Filter
        if has_whatsapp is not None:
            if has_whatsapp:
                db_query = db_query.filter(models.Lead.contact_phone != None)
            else:
                db_query = db_query.filter(models.Lead.contact_phone == None)
        
        # CRM Status Filter
        if status and status.lower() != "all":
            db_query = db_query.filter(models.Lead.status == models.CRMStatus(status.lower()))

        # Saved Leads Filter
        if is_saved is not None:
            db_query = db_query.filter(models.Lead.is_saved == (1 if is_saved else 0))
        
        # Strict Verification Filter
        if verified_only and not is_saved and not live: # Don't filter out saved leads or live feed leads
            db_query = db_query.filter(models.Lead.is_contact_verified == 1)
            db_query = db_query.filter(models.Lead.contact_reliability_score >= 10)
        
        # Live Feed Logic: Order by detection time (timestamp) if live
        if live:
            db_query = db_query.order_by(models.Lead.timestamp.desc())
            # For live feed, we might want to be less strict about confidence
            db_query = db_query.filter(models.Lead.confidence_score >= 0.1) # Relaxed from 0.5
        else:
            # Normal search results should be more reliable
            db_query = db_query.filter(models.Lead.confidence_score >= 0.5) # Relaxed from 1.0

        # 1. Location Filtering
        if location:
            if location.lower() == "kenya":
                db_query = db_query.filter(or_(
                    models.Lead.location_raw.ilike("%Kenya%"),
                    models.Lead.location_raw == "Unknown",
                    models.Lead.location_raw == None
                ))
            else:
                db_query = db_query.filter(models.Lead.location_raw.ilike(f"%{location}%"))
        
        # 2. Time Filtering
        if not live: # For live feed, show everything from last 4 days by default, but allow live toggle
            max_age_threshold = datetime.now() - timedelta(days=4)
            db_query = db_query.filter(models.Lead.timestamp >= max_age_threshold)

        if hours:
            time_threshold = datetime.now() - timedelta(hours=hours)
            db_query = db_query.filter(models.Lead.timestamp >= time_threshold)

        # 3. Hyper-Specific Filters
        if readiness:
            if readiness.upper() == "ACTIVE":
                db_query = db_query.filter(models.Lead.readiness_level.in_(["HOT", "WARM"]))
            elif readiness.upper() == "ALL":
                pass # No filter
            else:
                db_query = db_query.filter(models.Lead.readiness_level == readiness.upper())
            if min_prob is not None:
                db_query = db_query.filter(models.Lead.deal_probability >= min_prob)

        # 4. Authenticity Threshold
        if not live: # Relax authenticity for live feed fallbacks
            db_query = db_query.filter(models.Lead.is_genuine_buyer == 1)

        # 5. Local Advantage Filter
        if local_advantage:
            db_query = db_query.filter(models.Lead.delivery_range_score >= 70)

        # 6. Query Filtering
        if query:
            query_words = [w.strip() for w in query.lower().split() if len(w.strip()) > 2]
            if query_words:
                word_filters = []
                for word in query_words:
                    word_filters.append(models.Lead.product_category.ilike(f"%{word}%"))
                    word_filters.append(models.Lead.buyer_request_snippet.ilike(f"%{word}%"))
                    word_filters.append(models.Lead.neighborhood.ilike(f"%{word}%"))
                
                # Use OR for query words to broaden results, but weight them in ranking if possible
                # For now, just ensure at least one word matches
                db_query = db_query.filter(or_(*word_filters))
            else:
                # Fallback for very short queries
                db_query = db_query.filter(or_(
                    models.Lead.product_category.ilike(f"%{query}%"),
                    models.Lead.buyer_request_snippet.ilike(f"%{query}%")
                ))
        
        # 7. Ranking & Pagination
        offset = (page - 1) * limit
        if not live:
            if smart_match:
                # Rank by Match Score first, then Deal Probability
                db_query = db_query.order_by(
                    models.Lead.match_score.desc(),
                    models.Lead.deal_probability.desc(),
                    models.Lead.timestamp.desc()
                )
            else:
                db_query = db_query.order_by(
                    models.Lead.contact_reliability_score.desc(),
                    models.Lead.timestamp.desc()
                )
        else:
            db_query = db_query.order_by(models.Lead.timestamp.desc())
        
        leads = db_query.offset(offset).limit(limit).all()
        
        # MULTI-STAGE FALLBACK: If no results found, expand search parameters
        search_status = "STRICT"
        if not leads and not is_saved:
            logger.info(f"No leads found for '{query}' with strict filters. Starting expansion...")
            
            # Stage 1: Expand Time (4 days -> 30 days)
            search_status = "EXPANDED_TIME"
            relaxed_query = db.query(models.Lead)
            if query:
                filters = [models.Lead.product_category.ilike(f"%{query}%"), models.Lead.buyer_request_snippet.ilike(f"%{query}%")]
                relaxed_query = relaxed_query.filter(or_(*filters))
            
            # For expanded time, we still want somewhat recent leads
            max_age_threshold = datetime.now() - timedelta(days=60)
            relaxed_query = relaxed_query.filter(models.Lead.created_at >= max_age_threshold)
            leads = relaxed_query.order_by(models.Lead.created_at.desc()).offset(offset).limit(limit).all()
            
            # Stage 2: Relax Location & Confidence & Category (Keyword partial match)
            if not leads:
                search_status = "RELAXED_LOCATION"
                relaxed_query = db.query(models.Lead)
                if query:
                    # Search for any word in the query
                    query_words = query.split()
                    word_filters = []
                    for word in query_words:
                        if len(word) > 2:
                            word_filters.append(models.Lead.product_category.ilike(f"%{word}%"))
                            word_filters.append(models.Lead.buyer_request_snippet.ilike(f"%{word}%"))
                    
                    if word_filters:
                        relaxed_query = relaxed_query.filter(or_(*word_filters))
                
                # Broaden confidence
                relaxed_query = relaxed_query.filter(models.Lead.confidence_score >= 0.1)
                leads = relaxed_query.order_by(models.Lead.created_at.desc()).offset(offset).limit(limit).all()

            # Stage 3: AI-Inferred Leads (DISABLED per user request)
            if not leads and query:
                search_status = "NO_RESULTS"
                logger.info(f"No live leads found for '{query}'. AI expansion disabled.")
                leads = []

        return {
            "results": leads,
            "count": len(leads),
            "page": page,
            "limit": limit,
            "search_status": search_status
        }
    except Exception as e:
        logger.error(f"Error searching leads: {e}")
        return {
            "results": [],
            "count": 0,
            "page": page,
            "limit": limit,
            "error": "Search failed"
        }

@app.post("/search")
async def trigger_search(query: str, location: str = "Kenya", db: Session = Depends(get_db)):
    """Trigger background search across platforms, or sync fallback if broker is down."""
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
        
    platforms = ["google", "reddit", "facebook", "tiktok", "twitter"]
    
    # Check for Celery Broker connectivity
    try:
        from app.core.celery_worker import celery_app, scrape_platform_task
        from celery.exceptions import CeleryError
        from app.nlp.keyword_expansion import KeywordExpander
        
        expander = KeywordExpander()
        expanded_keywords = expander.expand_keywords(query, top_k=2) # Only 2 to avoid overwhelming
        
        broker_url = celery_app.conf.broker_url
        logger.info(f"Checking broker: {broker_url}")
        broker_available = False
        
        if broker_url.startswith("redis"):
            broker_available = check_redis()
        elif "sqlite" in broker_url:
            broker_available = True # SQLite is always available locally
        else:
            broker_available = True # Default to true for other brokers
            
        logger.info(f"Broker available: {broker_available}")
        if broker_available:
            from app.core.celery_worker import specialops_mission_task
            
            # MASTER AGENT: Trigger autonomous SpecialOps mission
            task = specialops_mission_task.delay(query, location)
            
            # Optional: Also trigger expanded keyword missions for higher coverage
            for kw in expanded_keywords:
                if kw.lower() != query.lower():
                    specialops_mission_task.delay(kw, location)
                
            return {
                "status": "SpecialOps Mission Initiated",
                "mode": "autonomous",
                "agent": "specialops",
                "task_id": task.id,
                "query": query
            }
    except Exception as e:
        logger.error(f"Broker check/dispatch failed: {e}")
    
    # Synchronous Fallback (Broker is down or failed)
    logger.warning(f"Task queue unavailable. Running synchronous fallback search for '{query}'")
    processed = sync_scrape_and_save(query, location, db)
    
    return {
        "status": "Synchronous search completed",
        "mode": "sync_fallback",
        "processed_count": processed,
        "warning": "Task queue (Redis/SQLite) is currently unavailable. Using limited synchronous discovery."
    }

@app.post("/outreach/contact/{lead_id}")
def mark_lead_contacted(lead_id: str, db: Session = Depends(get_db)):
    """Mark a lead as contacted to start response tracking."""
    try:
        success = outreach_engine.mark_contacted(db, lead_id)
        if not success:
            raise HTTPException(status_code=404, detail="Lead not found")
        return {"status": "success", "message": "Lead marked as contacted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking lead as contacted: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/outreach/track")
def track_outreach_response(data: OutreachResponseSchema, db: Session = Depends(get_db)):
    """Track a response from a buyer and update conversion status."""
    try:
        new_status = outreach_engine.track_response(db, data.lead_id, data.response_text)
        if not new_status:
            raise HTTPException(status_code=404, detail="Lead not found")
        return {"status": "success", "new_lead_status": new_status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking outreach response: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/analytics/conversions")
def get_analytics(db: Session = Depends(get_db)):
    """Get conversion analytics across all platforms."""
    try:
        return outreach_engine.get_conversion_analytics(db)
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        return {"error": "Analytics unavailable"}

@app.get("/intelligence/demand/trends")
def get_demand_trends(days: int = 7, db: Session = Depends(get_db)):
    """Forecast demand spikes for products."""
    try:
        forecaster = DemandForecaster(db)
        return forecaster.get_market_trends(days)
    except Exception as e:
        logger.error(f"Error fetching demand trends: {e}")
        return []

@app.get("/intelligence/demand/spikes/{category}")
def get_category_spikes(category: str, db: Session = Depends(get_db)):
    """Identify if a category is experiencing a demand spike."""
    try:
        forecaster = DemandForecaster(db)
        return forecaster.predict_demand_spikes(category)
    except Exception as e:
        logger.error(f"Error fetching category spikes: {e}")
        return {"error": "Intelligence data unavailable"}

@app.get("/intelligence/demand/emerging")
def get_emerging_markets(db: Session = Depends(get_db)):
    """Identify emerging markets before competitors."""
    try:
        forecaster = DemandForecaster(db)
        return forecaster.get_emerging_markets()
    except Exception as e:
        logger.error(f"Error fetching emerging markets: {e}")
        return []

# --- AGENT ENDPOINTS ---

@app.post("/agents", response_model=AgentSchema)
def create_agent(agent: AgentSchema, db: Session = Depends(get_db)):
    try:
        db_agent = models.Agent(
            name=agent.name,
            query=agent.query,
            location=agent.location,
            radius=agent.radius,
            min_intent_score=agent.min_intent_score,
            is_active=agent.is_active,
            enable_alerts=agent.enable_alerts
        )
        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)
        
        # Trigger first run immediately, but don't block if Celery is down
        try:
            from app.core.celery_worker import run_agent_task
            run_agent_task.delay(db_agent.id)
        except Exception as e:
            logger.error(f"WARNING: Agent {db_agent.id} created, but initial discovery failed to queue. Error: {e}")
            # We deliberately swallow the error here so the UI doesn't crash
            # The agent is saved in DB and will be picked up by the next scheduled run
        
        return db_agent
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to create agent")

@app.patch("/agents/{agent_id}", response_model=AgentSchema)
def update_agent(agent_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        for key, value in data.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        
        db.commit()
        db.refresh(agent)
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to update agent")

@app.delete("/agents/{agent_id}")
def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    try:
        agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        db.delete(agent)
        db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete agent")

# --- NOTIFICATION ENDPOINTS ---

@app.get("/leads/{lead_id}", response_model=LeadSchema)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    """Get a specific lead by ID."""
    try:
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lead: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/notifications/{notif_id}/read")
def mark_notification_read(notif_id: int, db: Session = Depends(get_db)):
    """Mark a notification as read."""
    try:
        notif = db.query(models.Notification).filter(models.Notification.id == notif_id).first()
        if not notif:
            raise HTTPException(status_code=404, detail="Notification not found")
        notif.is_read = 1
        db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/notifications/clear")
def clear_all_notifications(db: Session = Depends(get_db)):
    """Delete all notifications."""
    try:
        db.query(models.Notification).delete()
        db.commit()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error clearing notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear notifications")

# --- SETTINGS ENDPOINTS ---

@app.post("/settings")
def update_settings(settings_data: dict, db: Session = Depends(get_db)):
    """Update system settings."""
    try:
        for key, value in settings_data.items():
            setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
            if setting:
                setting.value = value
            else:
                setting = models.SystemSetting(key=key, value=value)
                db.add(setting)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


