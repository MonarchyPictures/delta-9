import os
import logging
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
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

from fastapi.responses import JSONResponse

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
