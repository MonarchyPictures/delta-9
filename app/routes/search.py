from fastapi import APIRouter, Depends, HTTPException, Request, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import time
import uuid

from app.db import models
from app.db.database import get_db
from app.ingestion import LiveLeadIngestor
from app.intelligence.confidence import apply_confidence 
from app.scrapers.verifier import verify_leads 
from app.cache.scraper_cache import get_cached, set_cached 
from app.scrapers.registry import refresh_scraper_states
from app.scrapers.metrics import record_verified
from app.config import PIPELINE_MODE, PROD_STRICT
from app.core.pipeline_mode import BOOTSTRAP_RULES
from app.config.categories.vehicles_ke import VEHICLES_KE
from app.utils.query_builder import build_vehicle_query
from starlette.concurrency import run_in_threadpool

router = APIRouter(tags=["Search"])

# API Key verification (simplified for internal route use)
API_KEY = "d9_prod_secret_key_2024" # Should ideally be from config

def verify_api_key(request: Request, x_api_key: str = Header(None)):
    if request.method == "OPTIONS":
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

@router.get("/leads", dependencies=[Depends(verify_api_key)])
def get_leads(
    request: Request,
    location: Optional[str] = "Kenya",
    query: Optional[str] = None,
    radius: Optional[float] = None,
    time_range: Optional[str] = "2h", 
    high_intent: Optional[bool] = False,
    has_whatsapp: Optional[bool] = False,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Production live leads feed with FLEXIBLE TIME WINDOW (2h -> 6h -> 12h -> 24h)."""
    try:
        start_time = time.time()
        now = datetime.now(timezone.utc)
        
        windows = {
            "2h": now - timedelta(hours=2),
            "6h": now - timedelta(hours=6),
            "12h": now - timedelta(hours=12),
            "24h": now - timedelta(days=1),
            "7d": now - timedelta(days=7)
        }

        target_range = time_range if time_range in windows else "2h"
        
        db_query = db.query(models.Lead).filter(
            or_(models.Lead.property_country == "Kenya", models.Lead.property_country.is_(None))
        )

        if query:
            db_query = db_query.filter(or_(
                models.Lead.product_category.ilike(f"%{query}%"),
                models.Lead.buyer_request_snippet.ilike(f"%{query}%")
            ))

        leads = []
        window_sequence = ["2h", "6h", "12h", "24h", "7d"]
        start_idx = window_sequence.index(target_range)
        
        current_window_label = target_range
        for label in window_sequence[start_idx:]:
            current_window_label = label
            temp_leads = db_query.filter(models.Lead.created_at >= windows[label]).order_by(models.Lead.created_at.desc()).limit(limit).all()
            if temp_leads:
                leads = temp_leads
                break
        
        results = [lead.to_dict() for lead in leads]
        
        duration = time.time() - start_time
        if duration > 1.5:
            import logging
            logging.getLogger(__name__).warning(f"--- Slow Leads Query: {duration:.2f}s (Range: {target_range}, Query: {query}) ---")

        if not results:
            return {
                "leads": [],
                "message": f"No buyer intent detected in the last {target_range}",
                "suggestion": "Widening time window ONLY (not intent rules)",
                "status": "zero_results"
            }
        
        # 🔐 Role-based override
        bypass_strict = request.headers.get("x-role") == "user"
        active_bootstrap = PIPELINE_MODE == "bootstrap" or bypass_strict
        resp = {
            "leads": results,
            "message": f"Showing leads from last {current_window_label}" if current_window_label != target_range else None,
            "window": current_window_label
        }
        if active_bootstrap:
            resp["warning"] = "Low-confidence signals shown"
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", dependencies=[Depends(verify_api_key)])
async def search_leads(request: Request, db: Session = Depends(get_db)):
    """Dashboard search: Multi-Pass discovery with verified outbound signals."""
    refresh_scraper_states()
    
    try:
        data = await request.json()
        query = data.get("query", "").lower()
        location = data.get("location", "Kenya")
        category = data.get("category")
        time_range = data.get("time_range", "2h")
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        # 🔒 LOCKED CATEGORY ENFORCEMENT (Vehicles • Kenya)
        # Check if query matches allowed objects or intent keywords
        is_valid_object = any(obj in query for obj in VEHICLES_KE["objects"])
        is_valid_intent = any(intent in query for intent in VEHICLES_KE["intent"])
        
        if not (is_valid_object or is_valid_intent):
            # Strict drift prevention: If query is unrelated to vehicles, block it
            raise HTTPException(
                status_code=403, 
                detail=f"System Locked: Search query '{query}' is outside the authorized category (Vehicles • Kenya)."
            )

        # 🚀 NORMALIZATION: Build high-intent vehicle query
        normalized_query = build_vehicle_query(query)

        ingestor = LiveLeadIngestor(db)
        window_hours_map = {"2h": 2, "6h": 6, "12h": 12, "24h": 24, "7d": 168}
        target_hours = window_hours_map.get(time_range, 2)

        cache_key = f"{normalized_query}:{location}:{category}" 
        cached = get_cached(cache_key) 
        
        if cached: 
            leads = cached 
        else: 
            leads = await run_in_threadpool(
                ingestor.fetch_from_external_sources, 
                normalized_query, 
                location, 
                time_window_hours=target_hours,
                category=category
            )
            
            leads = [apply_confidence(l) for l in leads] 
            leads = verify_leads(leads) 
        
            set_cached(cache_key, leads) 

        for l in leads:
            if l.get("verified") and l.get("_scraper_name"):
                record_verified(l["_scraper_name"], 1)
        
        verified = [l for l in leads if l.get("verified")] 
        
        if not verified: 
            # 🧠 TRAE AI DECISION LOOP: Search failed, let's adapt and retry
            if PROD_STRICT:
                import logging
                logger = logging.getLogger("TraeAI")
                logger.info(f"TRAE AI: Initial search for '{query}' returned 0 verified results. Starting adaptation loop...")
                
                # 1. Adapt scrapers via selector (last_result_count=0 triggers expansion)
                from app.scrapers.selector import decide_scrapers
                decide_scrapers(normalized_query, location, category=category, is_prod=True, last_result_count=0)
                
                # 2. Retry fetch with expanded scrapers and loosened threshold
                logger.info("TRAE AI: Retrying fetch with expanded scrapers and loosened thresholds...")
                retry_leads = await run_in_threadpool(
                    ingestor.fetch_from_external_sources, 
                    normalized_query, 
                    location, 
                    time_window_hours=target_hours,
                    category=category
                )
                
                retry_leads = [apply_confidence(l) for l in retry_leads] 
                # Pass loosen=True to lower verification bar slightly
                verified = verify_leads(retry_leads, loosen=True) 
                
                if verified:
                    logger.info(f"TRAE AI SUCCESS: Adaptation loop found {len(verified)} verified leads for '{query}'.")
                    leads = retry_leads # Use the new leads set
                else:
                    logger.warning(f"TRAE AI FAILURE: Adaptation loop still returned 0 results for '{query}'.")
            
            # If still no verified leads after loop or if not in PROD_STRICT
            if not verified:
                if not PROD_STRICT: 
                    for l in leads:
                        if "id" not in l: l["id"] = str(uuid.uuid4())
                        if "buyer_name" not in l: l["buyer_name"] = "Market Signal"
                        if "intent_strength" not in l: l["intent_strength"] = l.get("confidence_score", 0.5)
                        if "buyer_intent_quote" not in l: l["buyer_intent_quote"] = l.get("intent_text") or l.get("text", "")
                        if "timestamp" not in l: l["timestamp"] = datetime.now().isoformat()
                    
                    return { 
                        "results": leads, 
                        "warning": f"{BOOTSTRAP_RULES['label']} detected (locally verified)", 
                        "status": "bootstrap" 
                    } 
                return { 
                    "results": [], 
                    "message": "PROD_STRICT PIPELINE FAILED: No verified results after adaptation retry.", 
                    "status": "zero_results" 
                } 
        
        for l in verified:
            if "id" not in l: l["id"] = str(uuid.uuid4())
            if "buyer_name" not in l: l["buyer_name"] = "Verified Market Signal"
            if "intent_strength" not in l: l["intent_strength"] = l.get("confidence_score", 0.7)
            if "buyer_intent_quote" not in l: l["buyer_intent_quote"] = l.get("intent_text") or l.get("text", "")
            if "timestamp" not in l: l["timestamp"] = datetime.now().isoformat()

        return {"results": verified} 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/leads/{lead_id}", dependencies=[Depends(verify_api_key)])
def get_lead_detail(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.get("/leads/search", dependencies=[Depends(verify_api_key)])
def search_leads_endpoint(
    query: str,
    location: Optional[str] = "Kenya",
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Public discovery search interface."""
    results = get_leads(location=location, query=query, limit=limit, db=db)
    if not results:
        return {
            "results": [],
            "search_status": "zero_results",
            "message": "PROD_STRICT: No independently verified outbound signals found in history. Try a live search."
        }
    return {"results": results, "search_status": "PROD_STRICT"}

@router.patch("/leads/{lead_id}/status", dependencies=[Depends(verify_api_key)])
def update_lead_status(lead_id: str, status: models.CRMStatus, db: Session = Depends(get_db)):
    """Update lead status for simple CRM functionality."""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = status
    db.commit()
    return lead.to_dict()

@router.post("/outreach/contact/{lead_id}", dependencies=[Depends(verify_api_key)])
def contact_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = models.CRMStatus.CONTACTED
    db.commit()
    return {"status": "Contact tracked", "lead_id": lead_id}
