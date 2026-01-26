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
        logging.StreamHandler(),
        logging.FileHandler("radar_api.log")
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Buying Intent Radar API")

# CORS Configuration - Restricted for security
allowed_origins = os.getenv(
    "CORS_ALLOWED_ORIGINS", 
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://localhost:3001"
).split(",")

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
        # If we're using Redis, try to ping it. If SQLite, just check if we can connect to the DB.
        broker_url = celery_app.conf.broker_url
        if broker_url.startswith("redis"):
            celery_app.control.ping(timeout=1.0)
        health["services"]["celery"] = "up"
    except Exception:
        # If Redis ping fails, we check if we're in fallback mode
        from app.core.celery_worker import celery_app
        if "sqlite" in celery_app.conf.broker_url:
            health["services"]["celery"] = "up (fallback)"
        else:
            health["services"]["celery"] = "down"
            health["status"] = "degraded"
    return health

def check_redis():
    """Fast check for redis connectivity using a simple socket."""
    import socket
    from urllib.parse import urlparse
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    url = urlparse(redis_url)
    host = url.hostname or "localhost"
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
                    is_contact_verified=normalized.get("is_contact_verified", 0),
                    contact_reliability_score=normalized.get("contact_reliability_score", 0.0),
                    is_genuine_buyer=normalized.get("is_genuine_buyer", 1),
                    verification_badges=normalized.get("verification_badges", []),
                    status=models.ContactStatus.NOT_CONTACTED,
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

@app.get("/notifications", response_model=List[NotificationSchema])
def get_notifications(db: Session = Depends(get_db)):
    try:
        # Return all notifications, ordered by created_at desc
        return db.query(models.Notification).order_by(models.Notification.created_at.desc()).all()
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return []

@app.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Get all system settings."""
    try:
        settings = db.query(models.SystemSetting).all()
        return {s.key: s.value for s in settings}
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        return {}

@app.get("/leads/search")
def search_leads(
    query: Optional[str] = None,
    location: str = "Kenya",
    page: int = 1,
    limit: int = 10,
    hours: Optional[int] = None,
    readiness: Optional[str] = None,
    min_prob: Optional[float] = None,
    live: bool = False,
    verified_only: bool = True,
    smart_match: bool = True,
    local_advantage: bool = False,
    db: Session = Depends(get_db)
):
    """
    SEARCH PIPELINE:
    User Query -> Location Processing -> Lead Search -> Hyper-Specific Filters -> Ranking Engine -> Results API
    """
    try:
        db_query = db.query(models.Lead)
        
        # Strict Verification Filter
        if verified_only:
            db_query = db_query.filter(models.Lead.is_contact_verified == 1)
            db_query = db_query.filter(models.Lead.contact_reliability_score >= 10) # Minimum reliability threshold (allows social links)
        
        # Live Feed Logic: Order by detection time (created_at) if live
        if live:
            db_query = db_query.order_by(models.Lead.created_at.desc())
        
        # 1. Location Filtering
        if location:
            if location.lower() == "kenya":
                db_query = db_query.filter(or_(
                    models.Lead.location_raw.ilike("%Kenya%"),
                    models.Lead.location_raw == "Unknown"
                ))
            else:
                db_query = db_query.filter(models.Lead.location_raw.ilike(f"%{location}%"))
        else:
            db_query = db_query.filter(or_(
                models.Lead.location_raw.ilike("%Kenya%"),
                models.Lead.location_raw == "Unknown"
            ))

        # 2. Time Filtering
        max_age_threshold = datetime.now() - timedelta(days=4)
        db_query = db_query.filter(models.Lead.created_at >= max_age_threshold)

        if hours:
            time_threshold = datetime.now() - timedelta(hours=hours)
            db_query = db_query.filter(models.Lead.created_at >= time_threshold)

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
        # Relaxed for initial discovery
        db_query = db_query.filter(models.Lead.confidence_score >= 1.0, models.Lead.is_genuine_buyer == 1)

        # 5. Local Advantage Filter
        if local_advantage:
            db_query = db_query.filter(models.Lead.delivery_range_score >= 70)

        # 6. Query Filtering
        if query:
            filters = [
                models.Lead.product_category.ilike(f"%{query}%"),
                models.Lead.buyer_request_snippet.ilike(f"%{query}%"),
                models.Lead.neighborhood.ilike(f"%{query}%")
            ]
            db_query = db_query.filter(or_(*filters))
        
        # 7. Ranking & Pagination
        offset = (page - 1) * limit
        if not live:
            if smart_match:
                # Rank by Match Score first, then Deal Probability
                db_query = db_query.order_by(
                    models.Lead.match_score.desc(),
                    models.Lead.deal_probability.desc(),
                    models.Lead.created_at.desc()
                )
            else:
                db_query = db_query.order_by(
                    models.Lead.contact_reliability_score.desc(),
                    models.Lead.created_at.desc()
                )
        
        leads = db_query.offset(offset).limit(limit).all()
        
        # RELAXED FALLBACK: If no results found, try with relaxed filters
        if not leads and query:
            logger.info(f"No leads found for '{query}' with strict filters. Retrying with relaxed filters...")
            relaxed_query = db.query(models.Lead)
            
            # Filter 1: Basic Location
            if location:
                if location.lower() == "kenya":
                    relaxed_query = relaxed_query.filter(or_(
                        models.Lead.location_raw.ilike("%Kenya%"),
                        models.Lead.location_raw == "Unknown"
                    ))
                else:
                    relaxed_query = relaxed_query.filter(or_(
                        models.Lead.location_raw.ilike(f"%{location}%"),
                        models.Lead.location_raw == "Unknown"
                    ))
            
            # Filter 2: Basic Query
            filters = [
                models.Lead.product_category.ilike(f"%{query}%"),
                models.Lead.buyer_request_snippet.ilike(f"%{query}%")
            ]
            relaxed_query = relaxed_query.filter(or_(*filters))
            
            # Filter 3: Lower Confidence Threshold (anything above 1.0)
            relaxed_query = relaxed_query.filter(models.Lead.confidence_score >= 1.0)
            
            # Sort by creation date to show newest first
            leads = relaxed_query.order_by(models.Lead.created_at.desc()).offset(offset).limit(limit).all()
            logger.info(f"Relaxed search found {len(leads)} potential signals.")

        return {
            "results": leads,
            "count": len(leads),
            "page": page,
            "limit": limit
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
    """Trigger background search across platforms, or sync fallback if Redis is down."""
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
        
    platforms = ["google", "reddit", "facebook", "tiktok", "twitter"]
    
    # Check for Redis connectivity
    redis_available = check_redis()
    
    if redis_available:
        try:
            from app.core.celery_worker import scrape_platform_task
            from celery.exceptions import CeleryError
            
            task_ids = []
            for platform in platforms:
                task = scrape_platform_task.delay(platform, query, location)
                task_ids.append(task.id)
                
            return {
                "status": "Search initiated in background",
                "mode": "background",
                "platforms": platforms,
                "task_count": len(platforms)
            }
        except CeleryError as e:
            logger.error(f"Celery error during task dispatch: {e}")
            # Fall through to sync fallback
        except Exception as e:
            logger.error(f"Redis check passed but delay failed: {e}")
            # Fall through to sync fallback if delay() fails unexpectedly
    
    # Synchronous Fallback (Redis is down or failed)
    logger.warning(f"Task queue unavailable. Running synchronous fallback search for '{query}'")
    processed = sync_scrape_and_save(query, location, db)
    
    return {
        "status": "Synchronous search completed",
        "mode": "sync_fallback",
        "processed_count": processed,
        "warning": "Task queue (Redis) is currently unavailable. Using limited synchronous discovery."
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


