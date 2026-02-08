import os
import logging
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from .db import models, database
from .db.database import get_db, engine, SessionLocal
from .ingestion import LiveLeadIngestor
from .utils.outreach import OutreachEngine
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from .db import models, database
from .db.database import engine, SessionLocal
from .ingestion import LiveLeadIngestor
from .services.pipeline import LeadPipeline
from .config import PIPELINE_MODE, PROD_STRICT
from .scrapers.registry import refresh_scraper_states
from .scrapers.metrics import record_verified
from .scrapers.supervisor import revive_scrapers

# Import new routers
from .routes.search import router as search_router
from .routes.scrapers import router as scrapers_router
from .routes.admin import router as admin_router
from .routes.pipeline import router as pipeline_router

# Import database initialization helper if needed
from .db.database import engine
from .db import models

from fastapi.responses import JSONResponse

from .intelligence.buyer_profile import BuyerProfile, BuyerBehaviorEngine

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ABSOLUTE RULE: PROD STRICT STARTUP CHECK
if PROD_STRICT:
    logger.info("--- PROD_STRICT: Delta9 starting in PRODUCTION mode ---")
else:
    logger.warning("--- WARNING: Delta9 starting in DEVELOPMENT mode. Auto-downgrading to bootstrap. ---")

# Create tables on startup
try:
    logger.info("--- Attempting database connection and table creation ---")
    models.Base.metadata.create_all(bind=engine)
    logger.info("--- Database initialized successfully ---")
except Exception as e:
    logger.error(f"--- Database initialization FAILED: {str(e)} ---")

app = FastAPI(title="Delta9 Production API", version="1.0.0")

# 🔐 Search Middleware: Role-based access for search operations
@app.middleware("http")
async def search_middleware(request: Request, call_next):
    if request.url.path == "/leads":
        role = request.headers.get("x-role")
        if role == "user":
            logger.info(f"AUTHORIZED SEARCH: User role detected for search.")
            # Add role to request state so routers can use it
            request.state.role = "user"
        else:
            # If no role, we might still allow it if they have an API key, 
            # but we track it as 'unprivileged'.
            request.state.role = "guest"
            
    response = await call_next(request)
    return response

# Register routers
app.include_router(search_router)
app.include_router(scrapers_router)
app.include_router(admin_router)
app.include_router(pipeline_router)

# Ensure database tables exist
models.Base.metadata.create_all(bind=engine)

# Production CORS enforcement
origins = [
    "https://delta7.onrender.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173", # Vite default
]

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="http://localhost:.*", # Allow all localhost ports for dev
    allow_origins=[o for o in origins if o != "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background Scheduler setup
scheduler = BackgroundScheduler()

def fetch_live_leads_job():
    db = SessionLocal()
    try:
        # 1. AUTO-CLEANUP: Delete leads older than 7 days
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        deleted_count = db.query(models.Lead).filter(models.Lead.created_at < seven_days_ago).delete()
        if deleted_count > 0:
            logger.info(f"--- Background Job: Cleaned up {deleted_count} stale leads (>7 days old) ---")
            db.commit()

        # 2. INGESTION: Fetch fresh leads
        logger.info("--- Background Job: Starting Agent-Based Ingestion (PROD_STRICT) ---")
        
        ingestor = LiveLeadIngestor(db)
        pipeline = LeadPipeline(db)
        
        # Get all active agents
        active_agents = db.query(models.Agent).filter(models.Agent.is_active == 1).all()
        
        if not active_agents:
            logger.info("--- Background Job: No active agents found, running random cycle (2h window) ---")
            ingestor.run_full_cycle()
        else:
            logger.info(f"--- Background Job: Running cycles for {len(active_agents)} active agents ---")
            import random
            random.shuffle(active_agents)
            
            for agent in active_agents[:2]:
                logger.info(f"--- Background Job: Fetching for Agent '{agent.name}' (Query: {agent.query}) ---")
                try:
                    leads = ingestor.fetch_from_external_sources(agent.query, agent.location, time_window_hours=2)
                    
                    if leads:
                        strict_mode = PIPELINE_MODE == "strict"
                        verified_leads, verification_warnings = pipeline.verify_leads(leads, strict_mode=strict_mode)
                        
                        logger.info(f"✅ Background Job: Verified leads: {len(verified_leads)}, Warnings: {len(verification_warnings)}")
                        
                        if verified_leads:
                            for l in verified_leads:
                                if l.get("_scraper_name"):
                                    record_verified(l["_scraper_name"], 1)
                                    
                            ingestor.save_leads_to_db(verified_leads)
                    
                    agent.last_run = datetime.now(timezone.utc)
                    db.commit()
                except Exception as e:
                    logger.error(f"--- Agent '{agent.name}' Ingestion Failed: {str(e)} ---")
                
        logger.info("--- Background Job: Finished Ingestion Cycle ---")
    except Exception as e:
        logger.error(f"--- Background Job ERROR: {str(e)} ---")
    finally:
        db.close()

async def cleanup_old_leads():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        deleted = db.query(models.Lead).filter(models.Lead.created_at < seven_days_ago).delete()
        db.commit()
        if deleted > 0:
            logger.info(f"--- Background Cleanup: Purged {deleted} stale leads (> 7d old) ---")
    except Exception as e:
        logger.error(f"--- Background Cleanup ERROR: {str(e)} ---")
    finally:
        db.close()

# Run ingestion every 15 minutes
scheduler.add_job(fetch_live_leads_job, 'interval', minutes=15)
# Run cleanup every 10 minutes
scheduler.add_job(cleanup_old_leads, 'interval', minutes=10)
# 🔁 SELF-HEALING: Auto re-enable smart scrapers hourly
scheduler.add_job(revive_scrapers, 'interval', hours=1)
scheduler.start()

@app.get("/")
def read_root():
    # Use absolute path to ensure we find the frontend dist
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_path = os.path.join(base_dir, "frontend", "dist", "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
        
    return {
        "status": "online",
        "message": "Delta9 Production API - Kenya Market Intelligence Node",
        "version": "1.0.0",
        "region": "Kenya"
    }

<<<<<<< HEAD
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
=======
# 2. UPDATE BACKEND TO ENFORCE KENYA FILTER
@app.get("/leads", dependencies=[Depends(verify_api_key)])
def get_leads(
    location: Optional[str] = "Nairobi",
    query: Optional[str] = None,
    radius: Optional[float] = None,
    time_range: Optional[str] = "2h", # Default to 2h as per Step 4
    high_intent: Optional[bool] = False,
    has_whatsapp: Optional[bool] = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    session_id: Optional[str] = None
):
    """Production live leads feed with Buyer-Match Scoring."""
    try:
        start_time = time.time()
        now = datetime.now(timezone.utc)
        
        # 1. Infer Buyer Profile if session_id is present
        buyer_profile = None
        if session_id:
            logs = db.query(models.ActivityLog).filter(
                models.ActivityLog.session_id == session_id
            ).order_by(models.ActivityLog.timestamp.desc()).limit(20).all()
            if logs:
                buyer_profile = BuyerBehaviorEngine.infer_profile(logs)
                logger.info(f"Inferred Buyer Profile: {buyer_profile}")

        # Strategy: 2h (Strict) -> 6h -> 12h -> 24h -> 7d
        windows = {
            "2h": now - timedelta(hours=2),
            "6h": now - timedelta(hours=6),
            "12h": now - timedelta(hours=12),
            "24h": now - timedelta(days=1),
            "7d": now - timedelta(days=7)
        }

        # If user explicitly requested a range, use it, otherwise use 2h default
        target_range = time_range if time_range in windows else "2h"
        
        # Base query
        db_query = db.query(models.Lead).filter(
            or_(models.Lead.property_country == "Kenya", models.Lead.property_country.is_(None)),
            models.Lead.source_url.isnot(None)
        )

        if query:
            db_query = db_query.filter(or_(
                models.Lead.product_category.ilike(f"%{query}%"),
                models.Lead.buyer_request_snippet.ilike(f"%{query}%")
            ))

        # AUTO-WINDOW: Try the target range first, then expand if zero results
        leads = []
        # Define the sequence of windows to try
        window_sequence = ["2h", "6h", "12h", "24h", "7d"]
        start_idx = window_sequence.index(target_range)
        
        current_window_label = target_range
        for label in window_sequence[start_idx:]:
            current_window_label = label
            temp_leads = db_query.filter(models.Lead.created_at >= windows[label]).order_by(models.Lead.created_at.desc()).limit(limit).all()
            if temp_leads:
                leads = temp_leads
                break
        
        results = []
        for lead in leads:
            l_dict = lead.to_dict()
            if buyer_profile:
                match_score = buyer_profile.calculate_match_score(l_dict)
                l_dict["buyer_match_score"] = match_score
            else:
                l_dict["buyer_match_score"] = 0.0
            results.append(l_dict)
            
        # Re-sort results by match_score if profile exists
        if buyer_profile:
            results.sort(key=lambda x: x["buyer_match_score"], reverse=True)
        
        duration = time.time() - start_time
        if duration > 1.5: # Slightly higher threshold for leads due to auto-window expansion
            logger.warning(f"--- Slow Leads Query: {duration:.2f}s (Range: {target_range}, Query: {query}) ---")

        # 🛑 ZERO RESULTS RULE (Step 6)
        if not results:
            return {
                "leads": [],
                "message": f"No buyer intent detected in the last {target_range}",
                "suggestion": "Widening time window ONLY (not intent rules)",
                "status": "zero_results"
            }
            
        return {
            "leads": results,
            "message": f"Showing leads from last {current_window_label}" if current_window_label != target_range else None,
            "window": current_window_label
        }
    except Exception as e:
        logger.error(f"--- Error fetching leads: {str(e)} ---")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", dependencies=[Depends(verify_api_key)])
async def search_leads(request: Request, db: Session = Depends(get_db), x_session_id: Optional[str] = Header(None)):
    """Dashboard search: Multi-Pass discovery with verified outbound signals."""
    try:
        data = await request.json()
        query = data.get("query")
        location = data.get("location", "Kenya")
        time_range = data.get("time_range", "2h") # Default 2h
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        # Track search activity
        new_log = models.ActivityLog(
            event_type="SEARCH_PERFORMED",
            session_id=x_session_id,
            extra_metadata={"query": query, "location": location}
        )
        db.add(new_log)
        db.commit()

        # PART B: VEHICLES LAUNCH MODE - Lock to Vehicles category
        vehicle_keywords = [
            "car", "vehicle", "toyota", "nissan", "subaru", "isuzu", "mazda", "honda", "mitsubishi",
            "prado", "vitz", "land cruiser", "hilux", "demio", "note", "forester", "truck", "pickup",
            "van", "bus", "spare parts", "engine", "gearbox", "tyre", "rim", "brakes"
        ]
        is_vehicle_query = any(kw in query.lower() for kw in vehicle_keywords)
        
        if not is_vehicle_query:
            return {
                "results": [],
                "message": f"Platform locked to Vehicles category during Launch Mode. '{query}' is currently disabled.",
                "suggestion": "Try searching for vehicle brands like 'Toyota', 'Nissan', or 'Subaru'.",
                "status": "category_locked",
                "window": time_range
            }

        logger.info(f"--- Dashboard Search: Starting Multi-Pass Discovery for '{query}' (Range: {time_range}) ---")
        
        ingestor = LiveLeadIngestor(db)
        try:
            # Map time_range string to hours for ingestor
            window_hours_map = {"2h": 2, "6h": 6, "12h": 12, "24h": 24, "7d": 168}
            target_hours = window_hours_map.get(time_range, 2)
            
            # 1. Fetch leads (auto-expansion happens inside fetch_from_external_sources)
            # Use run_in_threadpool to avoid Playwright Sync/Async conflict in FastAPI's main event loop
            live_leads = await run_in_threadpool(
                ingestor.fetch_from_external_sources, 
                query, 
                location, 
                time_window_hours=target_hours
            )
            
            # Determine which window actually returned data
            current_range = time_range
            if live_leads:
                current_range = live_leads[0].get("discovery_window", time_range)
                # Ensure each lead has a proper UUID if missing
                for l in live_leads:
                    if "id" not in l:
                        l["id"] = str(uuid.uuid4())
                
                # Save verified leads to DB
                ingestor.save_leads_to_db(live_leads)
            
            if not live_leads:
                return {
                    "results": [], 
                    "message": f"No buyer intent detected for '{query}' in {location} (last {current_range}). PROD_STRICT: Only independently verified outbound signals permitted.",
                    "suggestion": "Try a broader query or check back later.",
                    "status": "zero_results",
                    "window": current_range
                }
            
            # Infer Buyer Profile for scoring
            buyer_profile = None
            if x_session_id:
                logs = db.query(models.ActivityLog).filter(
                    models.ActivityLog.session_id == x_session_id
                ).order_by(models.ActivityLog.timestamp.desc()).limit(20).all()
                if logs:
                    buyer_profile = BuyerBehaviorEngine.infer_profile(logs)
            
            # Fallback: If no profile yet, create a temporary one from current search
            if not buyer_profile:
                buyer_profile = BuyerProfile(vehicle_type=query, location=location, urgency=0.5)

            # Convert to frontend format (Step 5 requirements)
            formatted_leads = []
            outreach_engine = OutreachEngine()
            for lead in live_leads:
                f_lead = {
                    "lead_id": lead.get("id", str(uuid.uuid4())),
                    "buyer_name": lead.get("buyer_name", "Verified Market Signal"),
                    "phone": lead.get("contact_phone"),
                    "product": lead.get("product_category", query),
                    "quantity": lead.get("quantity_requirement", "1 unit"),
                    "intent_strength": lead.get("intent_score", 0.7),
                    "location": lead.get("location_raw", location),
                    "distance_km": lead.get("radius_km", 0),
                    "source": lead.get("source_platform", "Search"),
                    "timestamp": lead.get("request_timestamp", datetime.now()).isoformat() if isinstance(lead.get("request_timestamp"), datetime) else datetime.now().isoformat(),
                    "minutes_ago": lead.get("minutes_ago", 0),
                    "whatsapp_link": lead.get("whatsapp_link"),
                    "status": "new",
                    "source_url": lead.get("source_url"),
                    "buyer_intent_quote": lead.get("buyer_request_snippet") or lead.get("text", "")[:200],
                    "urgency_level": lead.get("urgency_level", "low"),
                    "contact_method": lead.get("whatsapp_link") or f"DM via {lead.get('source_platform', 'Social')}"
                }
                # Attach outreach suggestion
                f_lead["outreach_suggestion"] = outreach_engine.generate_message(f_lead)
                
                # Apply scoring (always calculated now)
                f_lead["buyer_match_score"] = buyer_profile.calculate_match_score(f_lead)
                
                formatted_leads.append(f_lead)
            
            # ALWAYS Sort by match score first (ranked by relevance)
            formatted_leads.sort(key=lambda x: (x["buyer_match_score"], 0 if x["phone"] else -1), reverse=True)

            return {
                "results": formatted_leads,
                "message": f"Showing closest valid buyer signals (last {current_range})" if current_range != time_range else None,
                "window": current_range,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"CRITICAL INGESTION ERROR: {str(e)}")
            # Even on error, return a structured 200 OK for the frontend to handle gracefully
            return {
                "results": [], 
                "message": f"Live feed temporarily unavailable. {str(e)}",
                "suggestion": "Please refresh or try again in 2 minutes.",
                "status": "error",
                "error_detail": str(e)
            }
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {str(e)}")
        return {
            "results": [], 
            "message": f"System error. {str(e)}",
            "status": "error"
        }

@app.patch("/leads/{lead_id}/status", dependencies=[Depends(verify_api_key)])
def update_lead_status(lead_id: str, status: models.CRMStatus, db: Session = Depends(get_db)):
    """Update lead status for simple CRM functionality."""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = status
    db.commit()
    return lead.to_dict()

@app.get("/settings", dependencies=[Depends(verify_api_key)])
def get_settings():
    """Return platform settings."""
    return {
        "notifications_enabled": True,
        "sound_enabled": True,
        "region": "Kenya",
        "currency": "KES",
        "geo_lock": "Kenya",
        "mode": "PROD_STRICT"
    }

@app.get("/leads/{lead_id}", dependencies=[Depends(verify_api_key)])
def get_lead_detail(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id,
        models.Lead.source_url.isnot(None),
        models.Lead.http_status == 200
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found or lacks proof-of-life proof")
    return lead

@app.get("/leads/search", dependencies=[Depends(verify_api_key)])
def search_leads_endpoint(
    query: str,
    location: Optional[str] = "Nairobi",
    limit: int = 50,
    db: Session = Depends(get_db),
    x_session_id: Optional[str] = Header(None)
):
    """Public discovery search interface."""
    results = get_leads(location=location, query=query, limit=limit, db=db, session_id=x_session_id)
    if not results:
        return {
            "results": [],
            "search_status": "zero_results",
            "message": "PROD_STRICT: No independently verified outbound signals found in history. Try a live search."
        }
    return {"results": results, "search_status": "PROD_STRICT"}

@app.post("/outreach/contact/{lead_id}", dependencies=[Depends(verify_api_key)])
def contact_lead(lead_id: str, db: Session = Depends(get_db), x_session_id: Optional[str] = Header(None)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Track the status change
    lead.status = models.CRMStatus.CONTACTED
    
    # Track the activity event
    new_log = models.ActivityLog(
        event_type="WHATSAPP_TAP",
        lead_id=lead_id,
        session_id=x_session_id,
        extra_metadata={
            "product": lead.product_category,
            "location": lead.location_raw,
            "source": lead.source_platform,
            "price": getattr(lead, "price", None)
        }
    )
    db.add(new_log)
    db.commit()
    return {"status": "Contact tracked", "lead_id": lead_id}

@app.get("/success/stats", dependencies=[Depends(verify_api_key)])
def get_success_stats(db: Session = Depends(get_db)):
    """Calculate high-impact metrics that drive money."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_24h = now - timedelta(hours=24)
    one_hour_ago = now - timedelta(hours=1)
    
    # 1. 🔥 Active vehicle listings (last 24h)
    active_listings_24h = db.query(models.Lead).filter(
        models.Lead.created_at >= last_24h
    ).count()
    
    # 2. ⚡ Urgent sellers
    urgent_sellers = db.query(models.Lead).filter(
        models.Lead.urgency_level == "high"
    ).count()
    
    # 3. 💬 WhatsApp taps today
    taps_today = db.query(models.ActivityLog).filter(
        models.ActivityLog.event_type == "WHATSAPP_TAP",
        models.ActivityLog.timestamp >= today_start
    ).count()
    
    # 4. 🎯 Matches above 0.8
    high_intent_matches = db.query(models.Lead).filter(
        models.Lead.intent_score >= 0.8
    ).count()
    
    # Keep some historical/internal metrics for target checking
    taps_last_hour = db.query(models.ActivityLog).filter(
        models.ActivityLog.event_type == "WHATSAPP_TAP",
        models.ActivityLog.timestamp >= one_hour_ago
    ).count()
    
    return {
        "active_listings_24h": active_listings_24h,
        "urgent_sellers": urgent_sellers,
        "whatsapp_taps_today": taps_today,
        "high_intent_matches": high_intent_matches,
        "taps_last_hour": taps_last_hour,
        "success_status": {
            "leads_target_met": active_listings_24h >= 5,
            "taps_target_met": taps_last_hour >= 1
        }
    }

# Internal routes secured with API_KEY
@app.get("/agents", dependencies=[Depends(verify_api_key)])
def get_agents(db: Session = Depends(get_db)):
    return db.query(models.Agent).all()

@app.post("/agents", dependencies=[Depends(verify_api_key)])
async def create_agent(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        logger.info(f"--- Creating Agent: {data.get('name')} ---")
        
        new_agent = models.Agent(
            name=data.get("name"),
            query=data.get("query"),
            location=data.get("location", "Kenya"),
            radius=data.get("radius", 50),
            min_intent_score=data.get("min_intent_score", 0.7),
            is_active=1,
            enable_alerts=1
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        
        # Trigger an immediate search for this new agent in the background
        # USE BackgroundTasks to avoid blocking the event loop
        def run_initial_ingestion(agent_id):
            # Create a new DB session for the background task
            bg_db = SessionLocal()
            try:
                agent = bg_db.query(models.Agent).filter(models.Agent.id == agent_id).first()
                if not agent:
                    return
                logger.info(f"--- [Background] Triggering initial search for agent: {agent.name} ---")
                ingestor = LiveLeadIngestor(bg_db)
                leads = ingestor.fetch_from_external_sources(agent.query, agent.location)
                if leads:
                    ingestor.save_leads_to_db(leads)
                agent.last_run = datetime.now(timezone.utc)
                bg_db.commit()
                logger.info(f"--- [Background] Initial search complete for agent: {agent.name} ---")
            except Exception as e:
                logger.error(f"--- [Background] Initial ingestion failed: {str(e)} ---")
            finally:
                bg_db.close()

        if ENVIRONMENT == "production":
            background_tasks.add_task(run_initial_ingestion, new_agent.id)
            
        return new_agent
    except Exception as e:
        logger.error(f"--- ERROR creating agent: {str(e)} ---")
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")

@app.get("/notifications", dependencies=[Depends(verify_api_key)])
def get_notifications(db: Session = Depends(get_db)):
    try:
        start_time = time.time()
        notifs = db.query(models.Notification).order_by(models.Notification.created_at.desc()).limit(20).all()
        duration = time.time() - start_time
        if duration > 1.0:
            logger.warning(f"--- Slow Notifications Query: {duration:.2f}s ---")
        return notifs
    except Exception as e:
        logger.error(f"--- Error fetching notifications: {str(e)} ---")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/notifications/{notification_id}/read", dependencies=[Depends(verify_api_key)])
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if notif:
        notif.is_read = 1
        db.commit()
    return {"status": "ok"}

@app.delete("/notifications/clear", dependencies=[Depends(verify_api_key)])
def clear_notifications(db: Session = Depends(get_db)):
    db.query(models.Notification).delete()
    db.commit()
    return {"status": "ok"}

@app.post("/settings", dependencies=[Depends(verify_api_key)])  
async def update_settings(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    return {"status": "Settings updated", "data": data}

# 9. SERVE FRONTEND (SPA Support)
# Mount static files from the frontend build directory
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dist_path = os.path.join(base_dir, "frontend", "dist")

if os.path.exists(dist_path):
    # Check for assets directory before mounting
    assets_path = os.path.join(dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Skip if path is an API endpoint
        if full_path.startswith("api/") or full_path.startswith("notifications") or full_path.startswith("leads") or full_path.startswith("agents"):
            raise HTTPException(status_code=404)
            
        file_path = os.path.join(dist_path, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        index_file = os.path.join(dist_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        
        raise HTTPException(status_code=404)
else:
    logger.warning(f"--- SPA dist directory not found at {dist_path} ---")
>>>>>>> 29fc54e (feat: vehicle-only mode, success metrics, and buyer-match scoring engine.)
