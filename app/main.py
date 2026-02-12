import os
import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, Depends, HTTPException, Header, BackgroundTasks
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

# Import new routers
from .routes.leads import router as leads_router
from .routes.search import router as search_router
from .routes.scrapers import router as scrapers_router
from .routes.admin import router as admin_router
from .routes.pipeline import router as pipeline_router
from .routes.outreach import router as outreach_router

from .intelligence.buyer_profile import BuyerProfile, BuyerBehaviorEngine

# Setup Logging
logging.basicConfig(level=logging.INFO)
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

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
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

# --- Endpoints ---
@app.on_event("startup")
async def startup_event():
    # 1. Sync scraper states from DB
    logger.info("--- Syncing scraper states from database ---")
    try:
        from .scrapers.metrics import sync_metrics_from_db
        sync_metrics_from_db()
        refresh_scraper_states()
    except Exception as e:
        logger.error(f"Scraper sync failed: {str(e)}")

    # 2. Start Background Scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(revive_scrapers, 'interval', hours=1)
    scheduler.start()
    logger.info("--- Background scheduler started (Revive Scrapers every 1h) ---")

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
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id,
        models.Lead.source_url.isnot(None),
        models.Lead.http_status == 200
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found or lacks proof-of-life proof")
    return lead

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
