from celery import Celery
import os
import sys
import logging
from datetime import datetime, timedelta

# Add project root to sys.path for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from celery.schedules import crontab
from app.db.database import SessionLocal
from app.db import models

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Broker configuration with fallback to SQLite for local development
BROKER_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
# If no redis is found, we'll use SQLAlchemy as a fallback broker
# This allows the app to run without a separate Redis instance
FALLBACK_BROKER_URL = "sqla+sqlite:///celery_broker.db"
RESULT_BACKEND = os.getenv("REDIS_URL", "db+sqlite:///celery_results.db")

celery_app = Celery(
    "intent_radar",
    broker=BROKER_URL,
    backend=RESULT_BACKEND
)

# Test connection and fallback if needed
try:
    import redis
    r = redis.from_url(BROKER_URL)
    r.ping()
except Exception:
    logger.warning("Redis not found. Falling back to SQLite broker.")
    celery_app.conf.broker_url = FALLBACK_BROKER_URL

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Nairobi",
    enable_utc=True,
    beat_schedule={
        "check-agents-every-15-min": {
            "task": "run_all_agents",
            "schedule": 900.0, # Run every 15 minutes
        },
        "cleanup-every-12-hours": {
            "task": "cleanup_old_leads",
            "schedule": 43200.0,
        },
    },
)

@celery_app.task(name="specialops_mission_task")
def specialops_mission_task(query: str, location: str = "Kenya", agent_id: int = None):
    """
    MASTER AGENT MISSION: Autonomous web intelligence routing.
    Follows the SpecialOps decision logic for search, crawl, and extraction.
    """
    from app.core.specialops import SpecialOpsAgent
    from app.utils.normalization import LeadValidator
    from app.nlp.duplicate_detector import DuplicateDetector
    
    agent_ops = SpecialOpsAgent()
    validator = LeadValidator()
    detector = DuplicateDetector()
    
    logger.info(f"Starting SpecialOps Mission: {query} in {location}")
    
    # 1. Execute Mission
    try:
        mission_results = agent_ops.execute_mission(query, location)
    except Exception as e:
        logger.error(f"SpecialOps Mission Failed: {e}")
        return f"Mission error: {e}"
    
    db = SessionLocal()
    processed_count = 0
    
    try:
        # Fetch recent leads for duplicate detection
        recent_leads = db.query(models.Lead).filter(
            models.Lead.timestamp >= datetime.now() - timedelta(hours=24)
        ).all()
        recent_texts = [l.buyer_request_snippet for l in recent_leads if l.buyer_request_snippet]

        logger.info(f"SpecialOps Mission found {len(mission_results)} potential results")
        
        for result in mission_results:
            try:
                # Prepare for normalization
                # Fix structure mismatch with specialops.py
                raw = {
                    "source": result.get("source", "specialops"),
                    "link": result.get("href") or result.get("url"),
                    "text": result.get("body") or result.get("text") or result.get("data", {}).get("raw_text", ""),
                    "title": result.get("title") or result.get("data", {}).get("title", ""),
                    "location": location
                }
                
                logger.info(f"Normalizing lead from {raw['source']}: {raw['text'][:50]}...")
                normalized = validator.normalize_lead(raw, db=db)
                if not normalized:
                    logger.info(f"Lead rejected by normalization")
                    continue
                
                # Duplicate Detection
                snippet = normalized.get("buyer_request_snippet", "")
                if snippet and detector.is_duplicate(snippet, recent_texts):
                    continue

                # Create lead record
                lead = models.Lead(
                id=normalized["id"],
                source_platform=normalized["source_platform"],
                post_link=normalized["post_link"],
                timestamp=normalized.get("timestamp", datetime.now()),
                location_raw=normalized.get("location_raw"),
                property_country="Kenya",
                latitude=normalized.get("latitude"),
                longitude=normalized.get("longitude"),
                buyer_request_snippet=normalized["buyer_request_snippet"],
                    product_category=normalized["product_category"],
                    buyer_name=normalized.get("buyer_name", "Anonymous"),
                    intent_score=normalized["intent_score"],
                    confidence_score=normalized["confidence_score"],
                    readiness_level=normalized.get("readiness_level"),
                    urgency_score=normalized.get("urgency_score"),
                    budget_info=normalized.get("budget_info"),
                    product_specs=normalized.get("product_specs"),
                    deal_probability=normalized.get("deal_probability"),
                    intent_type=normalized.get("intent_type", "BUYER"),
                    
                    # NEW: Special Ops Fields
                    is_hot_lead=1 if result.get("is_hot_lead") else 0,
                    whatsapp_ready_data=result.get("whatsapp_ready"),
                    
                    # Contact Verification
                    is_contact_verified=normalized.get("is_contact_verified", 0),
                    contact_reliability_score=normalized.get("contact_reliability_score", 0.0),
                    preferred_contact_method=normalized.get("preferred_contact_method")
                )
                
                db.merge(lead)
                processed_count += 1
                if snippet:
                    recent_texts.append(snippet)
                
            except Exception as e:
                logger.error(f"Error processing SpecialOps lead: {e}")
                continue
                
        db.commit()
        logger.info(f"SpecialOps Mission Complete: Found {processed_count} high-confidence leads.")
        return f"Processed {processed_count} leads via SpecialOps"
        
    except Exception as e:
        logger.error(f"Error in SpecialOps task: {e}")
        return f"Error: {e}"
    finally:
        db.close()

@celery_app.task(name="run_all_agents")
def run_all_agents():
    """Trigger active agents that are due for discovery."""
    db = SessionLocal()
    try:
        now = datetime.now()
        # Find active agents where next_run_at is reached or never set
        active_agents = db.query(models.Agent).filter(
            models.Agent.is_active == 1,
            (models.Agent.next_run_at <= now) | (models.Agent.next_run_at == None)
        ).all()
        
        for agent in active_agents:
            # Check if agent has expired (duration_days reached)
            if agent.created_at:
                expiry_time = agent.created_at + timedelta(days=agent.duration_days)
                if now > expiry_time:
                    logger.info(f"Agent '{agent.name}' (ID: {agent.id}) has expired. Deactivating.")
                    agent.is_active = 0
                    db.commit()
                    continue
            
            run_agent_task.delay(agent.id)
            
        return f"Triggered {len(active_agents)} agents"
    except Exception as e:
        logger.error(f"Error in run_all_agents: {e}")
        return f"Error: {e}"
    finally:
        db.close()

@celery_app.task(name="scrape_platform_task")
def scrape_platform_task(platform: str, query: str, location: str = "Kenya", agent_id: int = None, radius: int = 50, min_intent: float = 0.7):
    """Background task to scrape a platform and save leads."""
    from scraper import LeadScraper
    from app.utils.normalization import LeadValidator
    from app.utils.outreach import OutreachEngine
    from app.nlp.duplicate_detector import DuplicateDetector
    from app.core.compliance import ComplianceManager
    
    scraper = LeadScraper()
    validator = LeadValidator()
    outreach = OutreachEngine()
    detector = DuplicateDetector()
    compliance = ComplianceManager()
    
    # 1. Platform Compliance (Throttling)
    try:
        compliance.wait_for_rate_limit(platform.lower())
    except Exception as e:
        logger.error(f"Compliance check failed for {platform}: {e}")
    
    # 2. Scrape
    try:
        # Pass radius to scraper if supported
        raw_results = scraper.scrape_platform(platform.lower(), query, location, radius=radius)
    except Exception as e:
        logger.error(f"Scraper failed for {platform}: {e}")
        return f"Scraper error on {platform}"
    
    db = SessionLocal()
    processed_count = 0
    alert_count = 0
    
    try:
        # Fetch agent if id provided
        agent = None
        if agent_id:
            agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()

        # Fetch recent leads for duplicate detection (last 24h)
        recent_leads = db.query(models.Lead).filter(
            models.Lead.created_at >= datetime.now() - timedelta(hours=24)
        ).all()
        recent_texts = [l.buyer_request_snippet for l in recent_leads]

        for raw in raw_results:
            try:
                if "source" not in raw:
                    raw["source"] = platform.capitalize()
                    
                normalized = validator.normalize_lead(raw, db=db)
                if not normalized:
                    logger.info(f"Skipping empty normalization for lead from {platform}")
                    continue
                
                # Metadata check (Replaces hard skip)
                if normalized.get("intent_score", 0) < min_intent:
                    logger.info(f"Signal recorded with low intent score: {normalized.get('intent_score')} < {min_intent} (threshold for agent {agent_id})")

                # 3. Duplicate Detection
                if detector.is_duplicate(normalized["buyer_request_snippet"], recent_texts):
                    logger.info(f"Skipping duplicate lead from {platform}: {normalized['buyer_request_snippet'][:50]}...")
                    continue

                # Metadata check for Kenya (Replaces hard skip)
                loc = normalized.get("location_raw", "").lower()
                is_kenya = "kenya" in loc or any(city.lower() in loc for city in ["nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", "naivasha"])
                
                if not is_kenya:
                    other_countries = ["nigeria", "uganda", "tanzania", "usa", "uk", "india", "ghana", "south africa"]
                    mentions_other = any(c in loc for c in other_countries)
                    if not mentions_other and (location.lower() == "kenya" or "kenya" in query.lower()):
                        is_kenya = True
                
                if not is_kenya:
                    logger.info(f"Signal recorded from outside primary geo: {loc}")
                    # We save it anyway, but we might want to flag it

                # Check for history of non-response
                has_bad_history = outreach.check_non_response_history(
                    db, 
                    phone=normalized.get("contact_phone"), 
                    email=normalized.get("contact_email")
                )

                # Create lead record
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
                    non_response_flag=1 if has_bad_history else 0,
                    
                    # Hyper-Specific Intent Intelligence
                    readiness_level=normalized.get("readiness_level"),
                    urgency_score=normalized.get("urgency_score"),
                    budget_info=normalized.get("budget_info"),
                    product_specs=normalized.get("product_specs"),
                    deal_probability=normalized.get("deal_probability"),
                    intent_type=normalized.get("intent_type", "BUYER"),
                    
                    # NEW: Smart Matching
                    match_score=normalized.get("match_score", 0.0),
                    compatibility_status=normalized.get("compatibility_status"),
                    match_details=normalized.get("match_details"),
                    
                    # NEW: Intent Analysis Extensions
                    quantity_requirement=normalized.get("quantity_requirement"),
                    payment_method_preference=normalized.get("payment_method_preference"),
                    
                    # NEW: Local Advantage
                    delivery_range_score=normalized.get("delivery_range_score", 0.0),
                    neighborhood=normalized.get("neighborhood"),
                    local_pickup_preference=normalized.get("local_pickup_preference", 0),
                    delivery_constraints=normalized.get("delivery_constraints"),
                    
                    # NEW: Deal Readiness
                    decision_authority=normalized.get("decision_authority", 0),
                    prior_research_indicator=normalized.get("prior_research_indicator", 0),
                    comparison_indicator=normalized.get("comparison_indicator", 0),
                    upcoming_deadline=normalized.get("upcoming_deadline"),
                    
                    # Real-Time & Competitive Intelligence
                    availability_status=normalized.get("availability_status"),
                    competition_count=normalized.get("competition_count"),
                    is_unique_request=normalized.get("is_unique_request"),
                    optimal_response_window=normalized.get("optimal_response_window"),
                    peak_response_time=normalized.get("peak_response_time"),
                    
                    # Contact Verification & Reliability
                    is_contact_verified=normalized.get("is_contact_verified", 0),
                    contact_reliability_score=normalized.get("contact_reliability_score", 0.0),
                    preferred_contact_method=normalized.get("preferred_contact_method"),
                    disposable_email_flag=normalized.get("disposable_email_flag", 0),
                    contact_metadata=normalized.get("contact_metadata", {}),
                    
                    # Response Tracking System
                    response_count=normalized.get("response_count", 0),
                    average_response_time_mins=normalized.get("average_response_time_mins"),
                    conversion_rate=normalized.get("conversion_rate", 0.0),
                    
                    # NEW: Comprehensive Lead Intelligence
                    buyer_history=normalized.get("buyer_history"),
                    platform_activity_level=normalized.get("platform_activity_level"),
                    past_response_rate=normalized.get("past_response_rate", 0.0),
                    market_price_range=normalized.get("market_price_range"),
                    seasonal_demand=normalized.get("seasonal_demand"),
                    supply_status=normalized.get("supply_status"),
                    conversion_signals=normalized.get("conversion_signals", []),
                    talking_points=normalized.get("talking_points", []),
                    competitive_advantages=normalized.get("competitive_advantages", []),
                    pricing_strategy=normalized.get("pricing_strategy"),
                    
                    verification_badges=normalized.get("verification_badges", []),
                    is_genuine_buyer=normalized.get("is_genuine_buyer", 1),
                    last_activity=normalized.get("last_activity"),
                    status=models.ContactStatus.NOT_CONTACTED,
                    notes=normalized.get("notes", "")
                )
                
                # Check if lead exists by link
                existing = db.query(models.Lead).filter(models.Lead.post_link == lead.post_link).first()
                
                # Check if this phone already exists for this agent (Duplicate Prevention)
                is_phone_duplicate = False
                if agent and lead.contact_phone:
                    # Check across all leads this agent has found
                    existing_agent_leads = db.query(models.AgentLead).join(models.Lead).filter(
                        models.AgentLead.agent_id == agent.id,
                        models.Lead.contact_phone == lead.contact_phone
                    ).first()
                    if existing_agent_leads:
                        is_phone_duplicate = True
                        logger.info(f"Skipping lead for agent {agent.id}: Phone {lead.contact_phone} already discovered by this agent.")

                if not existing and not is_phone_duplicate:
                    # REAL-TIME ALERT LOGIC
                    if agent and agent.enable_alerts:
                        # Update notes with alert info
                        lead.notes = f"ALERT MATCH: '{agent.query}' in {agent.location}. Found via {platform} Agent '{agent.name}'.\n" + (lead.notes or "")
                        
                        # Create notification
                        notification = models.Notification(
                            lead_id=lead.id,
                            agent_id=agent.id,
                            message=f"🚨 REAL-TIME ALERT: New lead for '{agent.query}' found on {platform}!"
                        )
                        db.add(notification)
                        
                        # Store in AgentLead table
                        agent_lead = models.AgentLead(
                            agent_id=agent.id,
                            lead_id=lead.id
                        )
                        db.add(agent_lead)
                        
                        alert_count += 1
                    
                    db.add(lead)
                    processed_count += 1
                elif existing and not is_phone_duplicate:
                    # Lead exists in system but first time for this specific agent
                    if agent and agent.enable_alerts:
                        # Check if agent already has this specific lead record
                        already_linked = db.query(models.AgentLead).filter(
                            models.AgentLead.agent_id == agent.id,
                            models.AgentLead.lead_id == existing.id
                        ).first()
                        
                        if not already_linked:
                            # Create notification for existing lead
                            notification = models.Notification(
                                lead_id=existing.id,
                                agent_id=agent.id,
                                message=f"🚨 RADAR MATCH: Agent '{agent.name}' found an existing lead matching '{agent.query}'!"
                            )
                            db.add(notification)
                            
                            # Store link
                            agent_lead = models.AgentLead(
                                agent_id=agent.id,
                                lead_id=existing.id
                            )
                            db.add(agent_lead)
                            alert_count += 1
            except Exception as e:
                logger.error(f"Error processing lead from {platform}: {e}")
                continue

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving leads from {platform}: {e}")
        return f"Error saving leads: {e}"
    finally:
        db.close()
        
    return f"Processed {processed_count} leads ({alert_count} alerts) from {platform} in {location}"

@celery_app.task(name="run_agent_task")
def run_agent_task(agent_id: int):
    """Run discovery for a single agent."""
    db = SessionLocal()
    try:
        agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
        if not agent:
            logger.error(f"Agent {agent_id} not found in database.")
            return f"Agent {agent_id} not found"
        
        logger.info(f"EXECUTING: Agent '{agent.name}' (ID: {agent.id}) - Query: '{agent.query}' in {agent.location}")
        
        platforms = ["google", "facebook", "reddit", "tiktok", "twitter"]
        for platform in platforms:
            scrape_platform_task.delay(
                platform, 
                agent.query, 
                agent.location, 
                agent.id,
                radius=agent.radius,
                min_intent=agent.min_intent_score
            )
            
        # Update last run and next run timestamps
        agent.last_run = datetime.now()
        agent.next_run_at = agent.last_run + timedelta(hours=agent.interval_hours or 2)
        db.commit()
        return f"Agent {agent.name} triggered discovery on {len(platforms)} platforms. Next run: {agent.next_run_at}"
    except Exception as e:
        db.rollback()
        logger.error(f"CRITICAL: Agent {agent_id} execution failed. Error: {e}")
        return f"Error: {e}"
    finally:
        db.close()

@celery_app.task(name="cleanup_old_leads")
def cleanup_old_leads():
    """Remove leads older than 4 days to maintain freshness."""
    db = SessionLocal()
    try:
        four_days_ago = datetime.now() - timedelta(days=4)
        deleted = db.query(models.Lead).filter(models.Lead.created_at < four_days_ago).delete()
        db.commit()
        logger.info(f"Cleaned up {deleted} old leads.")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
    finally:
        db.close()

@celery_app.task(name="update_lead_availability")
def update_lead_availability():
    """Update availability status based on time passed."""
    db = SessionLocal()
    try:
        # Leads older than 48 hours are "Likely Closed"
        forty_eight_hours_ago = datetime.now() - timedelta(hours=48)
        db.query(models.Lead).filter(
            models.Lead.created_at < forty_eight_hours_ago,
            models.Lead.availability_status == "Available Now"
        ).update({"availability_status": "Likely Closed"})
        
        db.commit()
    except Exception as e:
        logger.error(f"Update availability failed: {e}")
    finally:
        db.close()

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Run cleanup every 12 hours
    sender.add_periodic_task(43200.0, cleanup_old_leads.s(), name='cleanup-every-12-hours')
    # Update availability every hour
    sender.add_periodic_task(3600.0, update_lead_availability.s(), name='update-availability-hourly')