import os
import asyncio
import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, Depends, HTTPException, Header, BackgroundTasks
from app.services.agent_scheduler import scheduler_loop
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import io
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
from .db import models, database
from .db.database import get_db, engine, SessionLocal
from .ingestion import LiveLeadIngestor
from .intelligence.outreach import OutreachEngine
from .intelligence.pricing import undercut_score
from .utils.email import send_email
from apscheduler.schedulers.background import BackgroundScheduler
from .services.pipeline import LeadPipeline
from .config import PIPELINE_MODE, PROD_STRICT, PIPELINE_CATEGORY
import uuid
from starlette.concurrency import run_in_threadpool
from .scrapers.registry import SCRAPER_REGISTRY, update_scraper_state, update_scraper_mode, refresh_scraper_states
from .config.scrapers import SCRAPER_CONFIG
from .scrapers.metrics import record_verified
from .scrapers.supervisor import revive_scrapers
from .routes.admin import verify_api_key
from .utils.logging import setup_logging

# Import new routers
from .routes.leads import router as leads_router
from .routes.search import router as search_router
from .routes.scrapers import router as scrapers_router
from .routes.admin import router as admin_router
from .routes.pipeline import router as pipeline_router
from .routes.outreach import router as outreach_router
from .api.routes import agents as agents_router
from .api.routes import notifications as notifications_router

from .intelligence.buyer_profile import BuyerProfile, BuyerBehaviorEngine

# Setup Logging (Structured JSON for Production)
setup_logging()
logger = logging.getLogger(__name__)

# ABSOLUTE RULE: Delta9 is now fully generic.
logger.info(f"--- Delta9 Intelligence Node active ---")

# Create tables on startup
try:
    logger.info("--- Attempting database connection and table creation ---")
    models.Base.metadata.create_all(bind=engine)
    logger.info("--- Database initialized successfully ---")
except Exception as e:
    logger.error(f"--- Database initialization FAILED: {str(e)} ---")

app = FastAPI(title="Delta9 Production API", version="1.0.0")

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Response

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.request_counts = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        
        # Get current count and start time for this IP
        current_data = self.request_counts.get(client_ip, (0, now))
        count, start_time = current_data
        
        # Check if window has expired (1 minute)
        if now - start_time > 60:
            # Reset window
            count = 1
            start_time = now
        else:
            # Increment count
            count += 1
            # RELAXED LIMIT: 1000 req/min to prevent frontend polling from getting blocked
            if count > 1000: 
                 return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})
            
        # Update storage
        self.request_counts[client_ip] = (count, start_time)
            
        response = await call_next(request)
        return response

app.add_middleware(RateLimitMiddleware)

# Add CORS Middleware with strict validation
# In strict production mode, we default to NO origins if not specified.
# In dev/bootstrap, we allow localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(leads_router)
app.include_router(search_router)
app.include_router(scrapers_router)
app.include_router(admin_router)
app.include_router(pipeline_router)
app.include_router(outreach_router)
app.include_router(agents_router.router, prefix="/agents", tags=["agents"])
app.include_router(notifications_router.router, prefix="/notifications", tags=["notifications"])

@app.get("/health")
async def health_check():
    """Simple health check for load balancers."""
    return {
        "status": "ok", 
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_mode": PIPELINE_MODE,
        "strict_mode": PROD_STRICT,
        "relaxed_mode": PIPELINE_MODE == "relaxed"
    }

@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Deep readiness check including database connectivity."""
    try:
        # Check DB connection
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return JSONResponse(status_code=503, content={"status": "not_ready", "error": "Database unavailable"})

# --- Endpoints ---
@app.on_event("startup")
async def startup_event():
    # Enforce Environment Sanity
    # DATABASE_URL is now handled with a default in database.py
    required_vars = ["ADMIN_SECRET_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.critical(f"FATAL: Missing required environment variables: {missing}")
        # Soft failure: Log critical error but attempt to continue (or use defaults if possible)
        # raise RuntimeError(f"Cannot start application without: {missing}")
        logger.warning("Continuing despite missing variables (Relaxed Mode)")
        
    if os.getenv("DEBUG", "false").lower() == "true" and PROD_STRICT:
        logger.warning("PRODUCTION WARNING: DEBUG mode is enabled in strict production!")

    # 0. Reset Agent States (Zombie Protection)
    # Using dedicated startup logic
    from app.services.agent_scheduler import scheduler_loop, reset_agents_on_startup
    reset_agents_on_startup()

    # 1. Start Async Agent Supervisor
    # We do NOT await scheduler_loop() directly as it is an infinite loop
    asyncio.create_task(scheduler_loop())
    logger.info("--- Async Agent Supervisor started ---")

    # 2. Sync scraper states from DB
    logger.info("--- Syncing scraper states from database ---")
    try:
        from app.scrapers.metrics import sync_metrics_from_db
        sync_metrics_from_db()
        refresh_scraper_states()
    except Exception as e:
        logger.error(f"Scraper sync failed: {str(e)}")

    # 3. Start Background Scheduler (Maintenance Only)
    scheduler = BackgroundScheduler()
    scheduler.add_job(revive_scrapers, 'interval', hours=1)
    
    # NOTE: Removed redundant run_all_agents job. 
    # The async scheduler_loop handles agent execution now.
        
    scheduler.start()

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Hide internal server errors in production
    logger.error(f"Global Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "request_id": str(uuid.uuid4())}
    )

    # 2. Sync scraper states from DB
    logger.info("--- Syncing scraper states from database ---")
    try:
        from .scrapers.metrics import sync_metrics_from_db
        sync_metrics_from_db()
        refresh_scraper_states()
    except Exception as e:
        logger.error(f"Scraper sync failed: {str(e)}")

    # 3. Start Background Scheduler (Maintenance Only)
    scheduler = BackgroundScheduler()
    scheduler.add_job(revive_scrapers, 'interval', hours=1)
    
    # NOTE: Removed redundant run_all_agents job. 
    # The async scheduler_loop handles agent execution now.
        
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("--- Background maintenance scheduler started ---")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("--- Delta9 Intelligence Node shutting down ---")
    if hasattr(app.state, "scheduler"):
        logger.info("--- Stopping Background Scheduler ---")
        app.state.scheduler.shutdown()

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check for Delta9 node.
    Checks DB connectivity and scraper performance.
    """
    health = {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
    try:
        # Check DB
        db.execute(text("SELECT 1"))
        health["database"] = "connected"
    except Exception as e:
        health["status"] = "unhealthy"
        health["database"] = f"error: {str(e)}"

    # Check Active Scrapers
    from .scrapers.registry import get_active_scrapers
    active = get_active_scrapers()
    health["active_scrapers"] = len(active)
    
    return health

@app.get("/")
def read_root():
    # Use absolute path to ensure we find the frontend dist
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_path = os.path.join(base_dir, "frontend", "dist", "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
        
    return {
        "status": "online",
        "message": "Delta9 Production API - Generic Market Intelligence Node",
        "version": "1.0.0"
    }

@app.get("/api/agent/me", dependencies=[Depends(verify_api_key)])
def get_current_agent(db: Session = Depends(get_db)):
    """Return the current agent profile."""
    # Mock user for now
    user = db.query(models.Agent).first()
    if not user:
        # Create a default agent if none exists for testing
        user = models.Agent(name="Global Agent", email="agent@delta9.ai")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_paying": True # Default to True now that wallet is removed
    }

@app.get("/leads/{lead_id}", dependencies=[Depends(verify_api_key)])
def get_lead_detail(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    
    if not lead:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Lead not found"})
        
    # Soft flag for missing source URL or bad HTTP status
    if not lead.source_url or lead.http_status != 200:
        lead.contact_flag = "verification_pending"
        
    return lead

@app.post("/outreach/contact/{lead_id}", dependencies=[Depends(verify_api_key)])
def contact_lead(lead_id: str, db: Session = Depends(get_db), x_session_id: Optional[str] = Header(None)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Lead not found"})
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
