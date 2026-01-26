from celery import Celery
import os
import logging
from datetime import datetime, timedelta
from celery.schedules import crontab
from app.db.database import SessionLocal
from app.db import models

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Broker configuration with fallback to SQLite for local development
BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
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
        "daily-agents-run": {
            "task": "run_all_agents",
            "schedule": crontab(hour=2, minute=0),  # Run at 2 AM daily
        },
    },
)

@celery_app.task(name="run_all_agents")
def run_all_agents():
    """Trigger all active agents to run their searches."""
    db = SessionLocal()
    try:
        active_agents = db.query(models.Agent).filter(models.Agent.is_active == 1).all()
        for agent in active_agents:
            run_agent_task.delay(agent.id)
        return f"Triggered {len(active_agents)} agents"
    except Exception as e:
        logger.error(f"Error in run_all_agents: {e}")
        return f"Error: {e}"
    finally:
        db.close()

@celery_app.task(name="scrape_platform_task")
def scrape_platform_task(platform: str, query: str, location: str = "Kenya", agent_id: int = None):
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
        raw_results = scraper.scrape_platform(platform.lower(), query, location)
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
                    continue # Skip leads that fail strict contact verification
                
                # 3. Duplicate Detection
                if detector.is_duplicate(normalized["buyer_request_snippet"], recent_texts):
                    logger.info(f"Skipping duplicate lead from {platform}: {normalized['buyer_request_snippet'][:50]}...")
                    continue

                # STRICT KENYA FILTERING
                loc = normalized.get("location_raw", "").lower()
                is_kenya = "kenya" in loc or any(city.lower() in loc for city in ["nairobi", "mombasa", "kisumu", "nakuru", "eldoret"])
                
                if not is_kenya:
                    continue

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
                if not existing:
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
                        alert_count += 1
                    
                    db.add(lead)
                    processed_count += 1
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
            scrape_platform_task.delay(platform, agent.query, agent.location, agent.id)
            
        # Update last run timestamp
        agent.last_run = datetime.now()
        db.commit()
        return f"Agent {agent.name} triggered discovery on {len(platforms)} platforms"
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
