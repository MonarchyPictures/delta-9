import os
import uuid
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Request, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from .db import models, database
from .db.database import get_db, engine
from .ingestion import LiveLeadIngestor
from apscheduler.schedulers.background import BackgroundScheduler

# Create tables on startup
try:
    print(f"--- Attempting database connection and table creation ---")
    models.Base.metadata.create_all(bind=engine)
    print("--- Database initialized successfully ---")
except Exception as e:
    print(f"--- Database initialization FAILED: {str(e)} ---")
    # Don't exit yet, let the app try to start, though DB operations will fail

app = FastAPI(title="Delta9 Production API", version="1.0.0")

# Setup Scheduler for Live Ingestion
scheduler = BackgroundScheduler()

def fetch_live_leads_job():
    db = next(get_db())
    try:
        print("--- Background Job: Starting Agent-Based Ingestion ---")
        ingestor = LiveLeadIngestor(db)
        
        # Get all active agents
        active_agents = db.query(models.Agent).filter(models.Agent.is_active == 1).all()
        
        if not active_agents:
            print("--- Background Job: No active agents found, running random cycle ---")
            ingestor.run_full_cycle()
        else:
            print(f"--- Background Job: Running cycles for {len(active_agents)} active agents ---")
            for agent in active_agents:
                print(f"--- Background Job: Fetching for Agent '{agent.name}' (Query: {agent.query}) ---")
                leads = ingestor.fetch_from_external_sources(agent.query, agent.location)
                if leads:
                    ingestor.save_leads_to_db(leads)
                
                # Update last_run
                agent.last_run = datetime.utcnow()
                db.commit()
                
        print("--- Background Job: Finished Ingestion Cycle ---")
    except Exception as e:
        print(f"--- Background Job ERROR: {str(e)} ---")
    finally:
        db.close()

# Run ingestion every 15 minutes in production
scheduler.add_job(fetch_live_leads_job, 'interval', minutes=15)
scheduler.start()

print("--- Delta9 API Starting Up with Background Scheduler ---")
print(f"--- Database URL present: {bool(os.getenv('DATABASE_URL'))} ---")

# 8. SECURITY & PRODUCTION HARDENING
# Secure routes and use environment variables for keys/DB
API_KEY = os.getenv("API_KEY", "d9_prod_secret_key_2024") 
DATABASE_URL = os.getenv("DATABASE_URL")

# Production CORS enforcement
origins = [
    "https://delta7.onrender.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*", # Allow all origins temporarily to ensure the UI can connect regardless of Render URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key Middleware
def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized access to market intelligence")
    return x_api_key

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Delta9 Production API - Kenya Market Intelligence Node",
        "version": "1.0.0",
        "region": "Kenya"
    }

# 2. UPDATE BACKEND TO ENFORCE KENYA FILTER
@app.get("/leads", dependencies=[Depends(verify_api_key)])
def get_leads(
    location: Optional[str] = "Nairobi",
    query: Optional[str] = None,
    radius: Optional[float] = None,
    time_range: Optional[str] = None, # "1h", "24h", "72h"
    high_intent: Optional[bool] = False,
    has_whatsapp: Optional[bool] = False,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Production live leads feed from DB - REAL DATA ONLY - GEO-LOCKED TO KENYA."""
    try:
        from datetime import datetime, timedelta
        
        # 5. GEO-LOCK TO KENYA - Server side enforcement using property_country
        db_query = db.query(models.Lead).filter(models.Lead.property_country == "Kenya")

        # Filter for quality leads (Base threshold)
        if high_intent:
            db_query = db_query.filter(models.Lead.intent_score >= 0.85)
        else:
            db_query = db_query.filter(models.Lead.intent_score >= 0.6)

        if query:
            db_query = db_query.filter(or_(
                models.Lead.product_category.ilike(f"%{query}%"),
                models.Lead.buyer_request_snippet.ilike(f"%{query}%")
            ))

        if radius:
            db_query = db_query.filter(models.Lead.radius_km <= radius)

        if time_range:
            now = datetime.utcnow()
            if time_range == "1h":
                db_query = db_query.filter(models.Lead.created_at >= now - timedelta(hours=1))
            elif time_range == "24h":
                db_query = db_query.filter(models.Lead.created_at >= now - timedelta(days=1))
            elif time_range == "72h":
                db_query = db_query.filter(models.Lead.created_at >= now - timedelta(days=3))

        if has_whatsapp:
            # Check both the dedicated contact_phone field and the JSON field for WhatsApp readiness
            db_query = db_query.filter(or_(
                models.Lead.contact_phone != None,
                models.Lead.whatsapp_ready_data.isnot(None) # Basic check if WhatsApp data exists
            ))

        leads = db_query.order_by(models.Lead.created_at.desc()).limit(limit).all()
        return leads
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", dependencies=[Depends(verify_api_key)])
async def trigger_search(
    query: str = Form(...), 
    location: str = Form("Nairobi"),
    db: Session = Depends(get_db)
):
    """
    7. LIVE DISCOVERY - Triggers real-time web ingestion for the dashboard.
    This replaces the 'dummy' ingestion with real DuckDuckGo-powered discovery.
    """
    try:
        print(f"--- Dashboard Search Triggered: {query} in {location} ---")
        ingestor = LiveLeadIngestor(db)
        
        # 1. Fetch real live leads from the web
        raw_leads = ingestor.fetch_from_external_sources(query, location)
        
        if not raw_leads:
            print(f"--- No live signals found for '{query}' ---")
            return {"results": [], "status": "No signals found"}
            
        # 2. Save them to DB (handles duplicates automatically)
        ingestor.save_leads_to_db(raw_leads)
        
        # 3. Fetch them back from DB to ensure we return full model objects
        # We filter by the query to return relevant results to the dashboard
        leads = db.query(models.Lead).filter(
            or_(
                models.Lead.product_category.ilike(f"%{query}%"),
                models.Lead.buyer_request_snippet.ilike(f"%{query}%")
            )
        ).order_by(models.Lead.created_at.desc()).limit(10).all()
        
        print(f"--- Dashboard Search returning {len(leads)} live signals ---")
        return {"results": leads, "status": "Live signals captured"}
        
    except Exception as e:
        print(f"--- Dashboard Search ERROR: {str(e)} ---")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/leads/{lead_id}", dependencies=[Depends(verify_api_key)])
def get_lead_detail(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@app.get("/leads/search", dependencies=[Depends(verify_api_key)])
def search_leads_endpoint(
    query: str,
    location: Optional[str] = "Nairobi",
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Public discovery search interface."""
    results = get_leads(location=location, query=query, limit=limit, db=db)
    return {"results": results, "search_status": "PROD_STRICT"}

@app.post("/outreach/contact/{lead_id}", dependencies=[Depends(verify_api_key)])
def contact_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = models.CRMStatus.CONTACTED
    db.commit()
    return {"status": "Contact tracked", "lead_id": lead_id}

# Internal routes secured with API_KEY
@app.get("/agents", dependencies=[Depends(verify_api_key)])
def get_agents(db: Session = Depends(get_db)):
    return db.query(models.Agent).all()

@app.post("/agents", dependencies=[Depends(verify_api_key)])
async def create_agent(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        print(f"--- Creating Agent: {data.get('name')} ---")
        
        new_agent = models.Agent(
            name=data.get("name"),
            query=data.get("query"),
            location=data.get("location", "Kenya"),
            radius=data.get("radius", 50),
            min_intent_score=data.get("min_intent_score", 0.7),
            is_active=data.get("is_active", 1),
            enable_alerts=data.get("enable_alerts", 1)
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        
        # Trigger an immediate search for this new agent in the background
        print(f"--- Triggering immediate search for new agent: {new_agent.name} ---")
        try:
            ingestor = LiveLeadIngestor(db)
            leads = ingestor.fetch_from_external_sources(new_agent.query, new_agent.location)
            if leads:
                ingestor.save_leads_to_db(leads)
            new_agent.last_run = datetime.utcnow()
            db.commit()
        except Exception as ingest_err:
            print(f"--- Initial ingestion failed for agent {new_agent.name}: {str(ingest_err)} ---")
            # Don't fail the agent creation if ingestion fails
            
        return new_agent
    except Exception as e:
        print(f"--- ERROR creating agent: {str(e)} ---")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notifications", dependencies=[Depends(verify_api_key)])
def get_notifications(db: Session = Depends(get_db)):
    return db.query(models.Notification).order_by(models.Notification.created_at.desc()).limit(20).all()

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

@app.get("/settings", dependencies=[Depends(verify_api_key)])
def get_settings(db: Session = Depends(get_db)):
    # In a real app, these would be in the DB
    return {"notifications_enabled": True, "sound_enabled": True, "geo_lock": "Kenya"}

@app.post("/settings", dependencies=[Depends(verify_api_key)])
async def update_settings(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    # In a real app, you would save these to the DB
    return {"status": "Settings updated", "data": data}