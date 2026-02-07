from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import os
import logging

from app.db import models
from app.db.database import get_db, SessionLocal
from app.ingestion import LiveLeadIngestor
from app.config import DELTA9_ENV

router = APIRouter(tags=["Admin"])

# API Key verification
API_KEY = os.getenv("API_KEY", "d9_prod_secret_key_2024")

def verify_api_key(request: Request, x_api_key: str = Header(None)):
    if request.method == "OPTIONS":
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

@router.get("/agents", dependencies=[Depends(verify_api_key)])
def get_agents(db: Session = Depends(get_db)):
    return db.query(models.Agent).all()

@router.post("/agents", dependencies=[Depends(verify_api_key)])
async def create_agent(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        
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
        
        def run_initial_ingestion(agent_id):
            bg_db = SessionLocal()
            try:
                agent = bg_db.query(models.Agent).filter(models.Agent.id == agent_id).first()
                if not agent:
                    return
                ingestor = LiveLeadIngestor(bg_db)
                leads = ingestor.fetch_from_external_sources(agent.query, agent.location)
                if leads:
                    ingestor.save_leads_to_db(leads)
                agent.last_run = datetime.now(timezone.utc)
                bg_db.commit()
            except Exception as e:
                logging.getLogger(__name__).error(f"Initial ingestion failed: {str(e)}")
            finally:
                bg_db.close()

        if DELTA9_ENV == "prod":
            background_tasks.add_task(run_initial_ingestion, new_agent.id)
            
        return new_agent
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings", dependencies=[Depends(verify_api_key)])
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
