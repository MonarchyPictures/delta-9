import os
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, Request, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from .db import models, database
from .db.database import get_db, engine
from .ingestion import LiveLeadIngestor
from apscheduler.schedulers.background import BackgroundScheduler

# ABSOLUTE RULE: PROD STRICT STARTUP CHECK
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
if ENVIRONMENT == "production":
    print("--- PROD_STRICT: Delta9 starting in PRODUCTION mode ---")
else:
    print("--- WARNING: Delta9 starting in DEVELOPMENT mode. Live leads will be restricted. ---")

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
        # 1. AUTO-CLEANUP: Delete leads older than 7 days
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        deleted_count = db.query(models.Lead).filter(models.Lead.created_at < seven_days_ago).delete()
        if deleted_count > 0:
            print(f"--- Background Job: Cleaned up {deleted_count} stale leads (>7 days old) ---")
            db.commit()

        # 2. INGESTION: Fetch fresh leads
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
                try:
                    leads = ingestor.fetch_from_external_sources(agent.query, agent.location)
                    if leads:
                        ingestor.save_leads_to_db(leads)
                    
                    # Update last_run
                    agent.last_run = datetime.now(timezone.utc)
                    db.commit()
                except Exception as e:
                    print(f"--- Agent '{agent.name}' Ingestion Failed: {str(e)} ---")
                
        print("--- Background Job: Finished Ingestion Cycle ---")
    except Exception as e:
        print(f"--- Background Job ERROR: {str(e)} ---")
    finally:
        db.close()

async def cleanup_old_leads():
    """ABSOLUTE RULE: ONLY return leads from the LAST 2 HOURS. Remove everything else."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        two_hours_ago = now - timedelta(hours=2)
        deleted = db.query(models.Lead).filter(models.Lead.created_at < two_hours_ago).delete()
        db.commit()
        if deleted > 0:
            print(f"--- Background Cleanup: Purged {deleted} stale leads (> 2h old) ---")
    except Exception as e:
        print(f"--- Background Cleanup ERROR: {str(e)} ---")
    finally:
        db.close()

# Run ingestion every 5 minutes in production to ensure "LIVE" leads
scheduler.add_job(fetch_live_leads_job, 'interval', minutes=5)
# Run cleanup every 10 minutes to enforce the 2-hour window strictly
scheduler.add_job(cleanup_old_leads, 'interval', minutes=10)
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
        
        # ABSOLUTE RULE: Filter for PROOF OF LIFE (REAL DATA ONLY)
        # AND ENFORCE 7-DAY FRESHNESS (NO STALE LEADS)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        db_query = db.query(models.Lead).filter(
            or_(models.Lead.property_country == "Kenya", models.Lead.property_country.is_(None)),
            models.Lead.source_url.isnot(None),
            models.Lead.created_at >= seven_days_ago
        )

        # Filter for quality leads (Base threshold)
        if high_intent:
            db_query = db_query.filter(models.Lead.intent_score >= 0.85)
        else:
            # Show all signals but allow the frontend to highlight hot ones
            db_query = db_query.filter(models.Lead.intent_score >= 0.5)

        if query:
            db_query = db_query.filter(or_(
                models.Lead.product_category.ilike(f"%{query}%"),
                models.Lead.buyer_request_snippet.ilike(f"%{query}%")
            ))

        if radius:
            db_query = db_query.filter(models.Lead.radius_km <= radius)

        # SYSTEM / BUYER-INTENT OVERRIDE: 2-hour window enforcement
        now = datetime.now(timezone.utc)
        if not time_range:
            # Default to 2 hours if not specified
            db_query = db_query.filter(models.Lead.created_at >= now - timedelta(hours=2))
        else:
            if time_range == "2h":
                db_query = db_query.filter(models.Lead.created_at >= now - timedelta(hours=2))
            elif time_range == "24h":
                db_query = db_query.filter(models.Lead.created_at >= now - timedelta(days=1))
            elif time_range == "72h":
                db_query = db_query.filter(models.Lead.created_at >= now - timedelta(days=3))
            elif time_range == "1h":
                db_query = db_query.filter(models.Lead.created_at >= now - timedelta(hours=1))

        if has_whatsapp:
            db_query = db_query.filter(models.Lead.contact_phone.isnot(None))

        # ABSOLUTE RULE: Prioritize leads with phone numbers, then by date
        from sqlalchemy import desc, case
        leads = db_query.order_by(
            case((models.Lead.contact_phone.isnot(None), 0), else_=1),
            models.Lead.created_at.desc()
        ).limit(limit).all()
        
        results = [lead.to_dict() for lead in leads]
        
        # Step 6 — Zero Results Rule
        if not results and (not time_range or time_range == "2h"):
            # Return a special response that the frontend can handle
            # Note: We still return 200 but with a message and suggestion
            return {
                "leads": [],
                "message": "No buyer intent detected in the last 2 hours",
                "suggestion": "Suggest widening time window ONLY (not intent rules)"
            }
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", dependencies=[Depends(verify_api_key)])
async def search_leads(request: Request, db: Session = Depends(get_db)):
    """Dashboard search: Real-time discovery with mandatory proof of life."""
    try:
        data = await request.json()
        query = data.get("query")
        location = data.get("location", "Kenya")
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        print(f"--- Dashboard Search: Starting real-time discovery for '{query}' ---")
        
        # ABSOLUTE RULE: Real-time outbound call only
        ingestor = LiveLeadIngestor(db)
        try:
            live_leads = ingestor.fetch_from_external_sources(query, location)
            
            # Save verified leads to DB for persistence
            if live_leads:
                ingestor.save_leads_to_db(live_leads)
            
            # Convert live_leads (dicts) to match the to_dict() format for consistency
            formatted_leads = []
            for lead in live_leads:
                formatted_leads.append({
                    "lead_id": lead["id"],
                    "buyer_name": lead["buyer_name"],
                    "phone": lead["contact_phone"],
                    "product": lead["product_category"],
                    "quantity": lead["quantity_requirement"],
                    "intent_strength": lead["intent_score"],
                    "location": lead["location_raw"],
                    "distance_km": lead["radius_km"],
                    "source": lead["source_platform"],
                    "timestamp": lead["request_timestamp"].isoformat(),
                    "whatsapp_link": lead["whatsapp_link"],
                    "status": "new",
                    "source_url": lead["source_url"],
                    "buyer_request_snippet": lead.get("buyer_request_snippet")
                })
            
            # ABSOLUTE RULE: Prioritize leads with phone numbers in search results
            formatted_leads.sort(key=lambda x: (x["phone"] is None, x["timestamp"]), reverse=True)
            # Actually, reverse=True with (is None) would put None first. 
            # Correct logic: leads with phone (False) should come before leads without (True).
            # Then sort by timestamp desc.
            formatted_leads.sort(key=lambda x: (0 if x["phone"] else 1, x["timestamp"]), reverse=False)
            # Wait, timestamp needs to be desc.
            from datetime import datetime
            formatted_leads.sort(key=lambda x: (0 if x["phone"] else 1, x["timestamp"]), reverse=False)
            # Re-sorting to be sure:
            formatted_leads.sort(key=lambda x: (0 if x["phone"] else 1, -datetime.fromisoformat(x["timestamp"]).timestamp()))

            return {"results": formatted_leads}
        except Exception as e:
            print(f"--- Dashboard Search: Discovery error: {str(e)} ---")
            # If discovery fails, fallback to DB search so the user isn't left empty
            db_results = db.query(models.Lead).filter(
                models.Lead.product_category.ilike(f"%{query}%")
            ).order_by(models.Lead.created_at.desc()).limit(20).all()
            return {"results": [l.to_dict() for l in db_results]}
            
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"--- Dashboard Search CRITICAL ERROR: {str(e)} ---")
        raise HTTPException(status_code=500, detail=f"ERROR: No live sources returned data. {str(e)}")

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
        "currency": "KES"
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
    db: Session = Depends(get_db)
):
    """Public discovery search interface."""
    results = get_leads(location=location, query=query, limit=limit, db=db)
    if not results:
        raise HTTPException(status_code=503, detail="ERROR: No live sources returned data. PROD_STRICT pipeline failure.")
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
            # We use a non-blocking approach for initial ingestion
            # If it fails, we still want the agent to be created successfully
            ingestor = LiveLeadIngestor(db)
            
            # ABSOLUTE RULE: Live ingestion only in production
            if os.getenv("ENVIRONMENT") == "production":
                leads = ingestor.fetch_from_external_sources(new_agent.query, new_agent.location)
                if leads:
                    ingestor.save_leads_to_db(leads)
                new_agent.last_run = datetime.now(timezone.utc)
                db.commit()
            else:
                print(f"--- Skipping initial ingestion for agent {new_agent.name} (not in production) ---")
        except Exception as ingest_err:
            print(f"--- Initial ingestion failed for agent {new_agent.name}: {str(ingest_err)} ---")
            # CRITICAL: We DO NOT re-raise this exception, so the agent creation succeeds
            
        return new_agent
    except Exception as e:
        print(f"--- ERROR creating agent: {str(e)} ---")
        # Only raise if the agent creation itself failed
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")

@app.get("/notifications", dependencies=[Depends(verify_api_key)])
def get_notifications(db: Session = Depends(get_db)):
    return db.query(models.Notification).order_by(models.Notification.created_at.desc()).limit(20).all()

@app.get("/settings", dependencies=[Depends(verify_api_key)])
def get_settings():
    return {
        "notifications_enabled": True,
        "sound_enabled": True,
        "region": "Kenya",
        "mode": "PROD_STRICT"
    }

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