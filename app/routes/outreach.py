from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..db import models
from ..intelligence.outreach import generate_message
from ..utils.outreach import whatsapp_link

router = APIRouter(prefix="/outreach", tags=["outreach"])

@router.get("/{lead_id}/whatsapp")
def open_whatsapp(lead_id: str, db: Session = Depends(get_db)):
    """Generates a WhatsApp link for a lead with a prefilled message."""
    try:
        lead_id_int = int(lead_id)
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id_int).first()
    except ValueError:
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    
    if not lead:
        # Soft failure
        return {"url": None, "error": "Lead not found", "detail": f"No lead with ID {lead_id}"}
    
    # Generate the personalized message
    message = generate_message(lead)
    
    # Normalize phone number from lead data
    # We check multiple possible fields for phone numbers
    phone = lead.phone or lead.contact or getattr(lead, 'buyer_contact', None)
    
    if not phone:
        # Fallback: check if the link itself is a whatsapp link
        if lead.link and "wa.me" in lead.link:
            return {"url": lead.link}
        # Soft failure instead of 400
        return {
            "url": None, 
            "error": "No phone number available", 
            "detail": "Lead has no contact phone number"
        }
        
    return {
        "url": whatsapp_link(phone, message)
    }

@router.post("/{lead_id}")
def outreach(lead_id: str, db: Session = Depends(get_db)):
    # Try to find lead by ID
    try:
        lead_id_int = int(lead_id)
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id_int).first()
    except ValueError:
        lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    
    if not lead:
        return {"error": "Lead not found", "lead_id": lead_id}
    
    # 📝 INJECT CALCULATED SCORES FOR MESSAGE LOGIC
    # The OutreachEngine needs buyer_match_score to decide which message to send.
    # We calculate it here using the same brutal scoring logic.
    from app.intelligence.buyer_score import buyer_score
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    lead_time = lead.created_at
    if lead_time.tzinfo is None:
        lead_time = lead_time.replace(tzinfo=timezone.utc)
    hours_old = (now - lead_time).total_seconds() / 3600
    
    # Temporarily add these to the lead object for the engine
    lead.hours_since_post = hours_old
    lead.buyer_match_score = buyer_score(lead)
    
    message = generate_message(lead)
    
    return {
        "lead_id": lead_id,
        "message": message,
        "buyer_match_score": lead.buyer_match_score
    }
