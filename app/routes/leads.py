from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging

from app.db import models
from app.db.database import get_db
from app.routes.admin import verify_api_key

from pydantic import BaseModel
import io
from fastapi.responses import StreamingResponse

from app.intelligence_v2.thresholds import FLOOR, HIGH_INTENT, STRICT_PUBLIC

class ExportRequest(BaseModel):
    ids: List[str]

router = APIRouter(tags=["Leads"])
logger = logging.getLogger(__name__)

@router.get("/export", dependencies=[Depends(verify_api_key)])
async def export_leads_by_type(
    type: str = Query(..., pattern="^(active|high_intent|bootstrap)$"),
    format: str = Query("txt", pattern="^txt$"),
    db: Session = Depends(get_db)
):
    """Export leads by intelligence tier as a .txt file."""
    try:
        def iter_leads():
            yield f"--- DELTA-9 LEAD EXPORT ({type.upper()}) ---\n"
            yield f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            
            query = db.query(models.Lead)
            if type == "active":
                query = query.filter(models.Lead.confidence_score >= STRICT_PUBLIC)
            elif type == "high_intent":
                query = query.filter(models.Lead.confidence_score >= HIGH_INTENT, models.Lead.confidence_score < STRICT_PUBLIC)
            elif type == "bootstrap":
                query = query.filter(models.Lead.confidence_score < HIGH_INTENT)

            # Stream results to avoid memory spikes
            for lead in query.yield_per(100):
                yield f"ID: {lead.id}\n"
                yield f"Product: {lead.product_category}\n"
                yield f"Location: {lead.location_raw}\n"
                yield f"Score: {lead.confidence_score}\n"
                yield f"Snippet: {lead.buyer_intent_snippet}\n"
                yield f"WhatsApp: {lead.contact_whatsapp or 'N/A'}\n"
                yield "---\n\n"

        filename = f"delta9-{type}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.txt"
        
        return StreamingResponse(
            iter_leads(),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        # Soft failure: Return a text file with the error
        error_content = f"Error generating export: {str(e)}"
        return StreamingResponse(
            io.BytesIO(error_content.encode('utf-8')),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=error_log.txt"}
        )

@router.get("/events", dependencies=[Depends(verify_api_key)])
def get_events(
    type: str = Query(..., pattern="^(whatsapp|all)$"),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Fetch tracked events (e.g. WhatsApp taps)."""
    try:
        query = db.query(models.ActivityLog)
        if type == "whatsapp":
            query = query.filter(models.ActivityLog.event_type == "WHATSAPP_TAP")
        
        events = query.order_by(models.ActivityLog.timestamp.desc()).limit(limit).all()
        return [
            {
                "id": e.id,
                "event": e.event_type,
                "lead_id": e.lead_id,
                "timestamp": e.timestamp.isoformat(),
                "metadata": e.extra_metadata
            }
            for e in events
        ]
    except Exception as e:
        logger.error(f"Failed to fetch events: {str(e)}")
        # Soft failure: Return empty list
        return []

@router.post("/leads/export", dependencies=[Depends(verify_api_key)])
async def export_leads(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """Export selected leads as a clean .txt file stream."""
    try:
        leads = db.query(models.Lead).filter(models.Lead.id.in_(request.ids)).all()
        
        if not leads:
            # Soft failure: Return empty file
            logger.warning("No leads found for export")
            return StreamingResponse(
                io.BytesIO(b"No leads found for provided IDs."),
                media_type="text/plain",
                headers={"Content-Disposition": "attachment; filename=empty_export.txt"}
            )
            
        output = io.StringIO()
        for l in leads:
            l_dict = l.to_dict()
            output.write(f"Source: {l_dict.get('source', 'N/A')}\n")
            output.write(f"Product: {l_dict.get('product', 'N/A')}\n")
            output.write(f"Text: {l_dict.get('text', 'N/A')}\n")
            output.write(f"Phone: {l_dict.get('phone', 'N/A')}\n")
            output.write(f"Intent Score: {l_dict.get('intent_score', 0)}\n")
            output.write(f"WhatsApp: {l_dict.get('whatsapp_url', 'N/A')}\n")
            output.write("---\n\n")
            
        output.seek(0)
        
        filename = f"delta9-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        # Soft failure instead of 500
        error_content = f"Export failed: {str(e)}"
        return StreamingResponse(
            io.BytesIO(error_content.encode('utf-8')),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=error_log.txt"}
        )

@router.get("/leads", dependencies=[Depends(verify_api_key)])
def get_leads(
    location: Optional[str] = None,
    query: Optional[str] = None,
    type: Optional[str] = None,
    filter: Optional[str] = None, # User-requested parameter
    time_range: Optional[str] = "2h",
    high_intent: Optional[bool] = False,
    has_whatsapp: Optional[bool] = False,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Generic leads feed with universal filtering aligned with Intelligence tiers."""
    try:
        now = datetime.now(timezone.utc)
        
        # Base query: Prioritize leads with source URLs but allow verified signals without them
        db_query = db.query(models.Lead)

        # 1. Intelligence Tier Filters (using 'filter' or 'type')
        tier = filter or type
        if tier == "active":
            db_query = db_query.filter(models.Lead.confidence_score >= STRICT_PUBLIC)
        elif tier == "high_intent":
            db_query = db_query.filter(models.Lead.confidence_score >= HIGH_INTENT, models.Lead.confidence_score < STRICT_PUBLIC)
        elif tier == "bootstrap":
            db_query = db_query.filter(models.Lead.confidence_score < HIGH_INTENT)
        elif tier == "whatsapp":
            db_query = db_query.filter(models.Lead.whatsapp_link.isnot(None))
        elif tier == "urgent":
            db_query = db_query.filter(models.Lead.urgency_level == "high")

        # 2. Boolean Filters
        if high_intent:
            db_query = db_query.filter(models.Lead.confidence_score >= HIGH_INTENT)
        if has_whatsapp:
            db_query = db_query.filter(models.Lead.whatsapp_link.isnot(None))

        # 3. Search Query
        if query:
            db_query = db_query.filter(or_(
                models.Lead.product_category.ilike(f"%{query}%"),
                models.Lead.buyer_request_snippet.ilike(f"%{query}%"),
                models.Lead.buyer_name.ilike(f"%{query}%")
            ))
        
        # 4. Location Filter (Generic)
        if location and location.lower() != "all":
             db_query = db_query.filter(or_(
                models.Lead.location_raw.ilike(f"%{location}%"),
                models.Lead.property_country.ilike(f"%{location}%")
            ))

        # 5. Time Window Sequence: 2h -> 6h -> 12h -> 24h -> 7d
        windows = {
            "2h": now - timedelta(hours=2),
            "6h": now - timedelta(hours=6),
            "12h": now - timedelta(hours=12),
            "24h": now - timedelta(days=1),
            "7d": now - timedelta(days=7)
        }

        target_range = time_range if time_range in windows else "2h"
        window_sequence = ["2h", "6h", "12h", "24h", "7d"]
        start_idx = window_sequence.index(target_range)
        
        leads = []
        final_window = target_range
        
        for label in window_sequence[start_idx:]:
            final_window = label
            # Intelligent Ranking: Sort by ranked_score first (which includes freshness), then timestamp
            temp_leads = db_query.filter(models.Lead.created_at >= windows[label])\
                                 .order_by(models.Lead.ranked_score.desc(), models.Lead.created_at.desc())\
                                 .limit(limit).all()
            if temp_leads:
                leads = temp_leads
                break
        
        results = [l.to_dict() for l in leads]
        
        # Ensure is_hot_lead is set in results
        for r in results:
            r["is_hot_lead"] = r.get("confidence", 0) >= STRICT_PUBLIC
            
        return {
            "count": len(results),
            "leads": results,
            "message": f"Showing {tier or 'live'} signals from last {final_window}",
            "window": final_window
        }
    except Exception as e:
        logger.error(f"API ERROR: Failed to fetch leads: {str(e)}")
        # Soft failure: Return empty list instead of 500 crash
        return {
            "count": 0,
            "leads": [],
            "message": f"Error fetching leads: {str(e)}",
            "window": time_range
        }

@router.get("/success/stats", dependencies=[Depends(verify_api_key)])
def get_success_stats(db: Session = Depends(get_db)):
    """Fetch live market metrics for the dashboard aligned with Intelligence tiers."""
    try:
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(days=1)
        
        # 1. ACTIVE LEADS (STRICT_PUBLIC >= 0.8) in last 24h
        active_count = db.query(models.Lead).filter(
            models.Lead.confidence_score >= STRICT_PUBLIC,
            models.Lead.created_at >= last_24h
        ).count()
        
        # 2. HIGH INTENT (0.6 <= score < 0.8)
        high_intent_count = db.query(models.Lead).filter(
            models.Lead.confidence_score >= HIGH_INTENT
        ).count()
        
        # 3. URGENT BUYERS (High urgency level)
        urgent_count = db.query(models.Lead).filter(
            models.Lead.urgency_level == "high",
            models.Lead.created_at >= last_24h
        ).count()
        
        # 4. WHATSAPP TAPS (Total tracked events today)
        from sqlalchemy import func
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # Use try/except for tap_count column existence if schema migration pending
        try:
            whatsapp_taps = db.query(func.sum(models.Lead.tap_count)).filter(
                models.Lead.created_at >= start_of_day
            ).scalar() or 0
        except Exception:
            whatsapp_taps = 0
        
        return {
            "active_listings_24h": active_count,
            "high_intent_matches": high_intent_count,
            "urgent_sellers": urgent_count,
            "whatsapp_taps_today": int(whatsapp_taps)
        }
    except Exception as e:
        # Log error and return empty stats to prevent frontend crash
        print(f"Stats Error: {e}")
        return {
            "active_listings_24h": 0,
            "high_intent_matches": 0,
            "urgent_sellers": 0,
            "whatsapp_taps_today": 0
        }

@router.patch("/leads/{lead_id}/status", dependencies=[Depends(verify_api_key)])
def update_lead_status(lead_id: str, status: str, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        return JSONResponse(status_code=200, content={"status": "error", "message": "Lead not found"})
    
    try:
        lead.status = models.CRMStatus(status)
        db.commit()
        return {"status": "success", "new_status": lead.status.value}
    except ValueError:
        return JSONResponse(status_code=200, content={"status": "error", "message": f"Invalid status: {status}"})

@router.post("/leads/{lead_id}/tap", dependencies=[Depends(verify_api_key)])
def track_lead_tap(lead_id: str, db: Session = Depends(get_db)):
    """Increment tap count and mark as contacted."""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        return {"status": "error", "message": "Lead not found"}
    
    # Increment tap count
    if lead.tap_count is None:
        lead.tap_count = 0
    lead.tap_count += 1
    
    # Mark as contacted if it's still new
    if lead.status == models.CRMStatus.NEW:
        lead.status = models.CRMStatus.CONTACTED
    
    # Log activity
    new_log = models.ActivityLog(
        event_type="WHATSAPP_TAP",
        lead_id=lead_id,
        extra_metadata={
            "product": lead.product_category,
            "source": lead.source_platform,
            "tap_count": lead.tap_count
        }
    )
    db.add(new_log)
    db.commit()
    
    return {
        "status": "success",
        "lead_id": lead_id,
        "tap_count": lead.tap_count,
        "lead_status": lead.status.value
    }
