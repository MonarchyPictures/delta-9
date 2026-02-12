from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks, Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import os
import logging

from app.db import models
from app.db.database import get_db, SessionLocal
from app.ingestion import LiveLeadIngestor
from app.config import PIPELINE_MODE

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
    agents = db.query(models.Agent).all()
    # Attach unread notification counts to each agent
    results = []
    for agent in agents:
        agent_dict = agent.to_dict()
        unread_count = db.query(models.Notification).filter(
            models.Notification.agent_id == agent.id,
            models.Notification.is_read == 0
        ).count()
        agent_dict["unread_count"] = unread_count
        results.append(agent_dict)
    return results

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
            interval_hours=data.get("interval_hours", 2),
            duration_days=data.get("duration_days", 7),
            next_run_at=datetime.now(), # Run immediately
            is_active=1,
            enable_alerts=1
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        
        # In modern version, Celery handles the execution
        from app.core.celery_worker import run_agent_task
        run_agent_task.delay(new_agent.id)
            
        return new_agent
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/agents/{agent_id}", dependencies=[Depends(verify_api_key)])
def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    """Delete an agent."""
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Also delete associated notifications
    db.query(models.Notification).filter(models.Notification.agent_id == agent_id).delete()
    db.delete(agent)
    db.commit()
    return {"status": "ok"}

@router.get("/agents/{agent_id}/export", dependencies=[Depends(verify_api_key)])
@router.get("/agent/{agent_id}/export", dependencies=[Depends(verify_api_key)])
def export_agent_leads(agent_id: int, db: Session = Depends(get_db)):
    """Export leads found by this agent as a .txt file download."""
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get leads associated with this agent through AgentLead table
    agent_leads = db.query(models.AgentLead).filter(models.AgentLead.agent_id == agent_id).all()
    lead_ids = [al.lead_id for al in agent_leads]
    
    # 🎯 DISPLAY LAYER FILTERING (Export)
    # We filter the export based on the agent's min_intent_score, but the leads are already saved.
    leads = db.query(models.Lead).filter(
        models.Lead.id.in_(lead_ids),
        models.Lead.intent_score >= agent.min_intent_score
    ).order_by(models.Lead.created_at.desc()).all()
    
    # Header: Name – Location
    content = f"{agent.name} – {agent.location}\n"
    content += "-" * 33 + "\n"
    
    for lead in leads:
        content += f"Name: {lead.buyer_name or 'Anonymous'}\n"
        content += f"Phone: {lead.contact_phone or 'N/A'}\n"
        content += f"Snippet: {lead.buyer_request_snippet or 'N/A'}\n"
        content += f"Source: {lead.source_platform or 'N/A'}\n"
        # Date: YYYY-MM-DD
        date_str = lead.created_at.strftime("%Y-%m-%d") if lead.created_at else "N/A"
        content += f"Date: {date_str}\n"
        content += "-" * 33 + "\n"
        
    filename = f"{agent.name.replace(' ', '_')}_leads.txt"
    
    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

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

@router.get("/notifications", dependencies=[Depends(verify_api_key)])
def get_notifications(db: Session = Depends(get_db)):
    """Fetch recent notifications."""
    try:
        # Check if the table exists first to avoid startup crashes if migration is pending
        notifs = db.query(models.Notification).order_by(models.Notification.created_at.desc()).limit(20).all()
        # Ensure we return objects that can be serialized to JSON
        return [
            {
                "id": n.id,
                "lead_id": n.lead_id,
                "agent_id": n.agent_id,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None
            }
            for n in notifs
        ]
    except Exception as e:
        logging.getLogger(__name__).error(f"Error fetching notifications: {str(e)}")
        # If table doesn't exist yet, return empty list instead of 500
        if "no such table" in str(e).lower():
            return []
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/{notification_id}/read", dependencies=[Depends(verify_api_key)])
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    """Mark a notification as read."""
    notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if notif:
        notif.is_read = 1
        db.commit()
    return {"status": "ok"}

@router.delete("/notifications/clear", dependencies=[Depends(verify_api_key)])
def clear_notifications(db: Session = Depends(get_db)):
    """Clear all notifications."""
    db.query(models.Notification).delete()
    db.commit()
    return {"status": "ok"}
