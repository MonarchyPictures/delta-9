from app.db import models
from sqlalchemy.orm import Session
from sqlalchemy import or_
import json
from datetime import datetime

class OutreachEngine:
    def __init__(self):
        self.templates = {
            "urgent": "Hi {name}, I saw you're looking for {product} urgently. I might be able to help you out right away. Are you still searching?",
            "general": "Hello {name}, regarding your post about needing {product} - I have some options that might fit what you're looking for. Let me know if you're interested!",
            "bulk": "Hi {name}, I noticed your request for bulk {product}. We specialize in wholesale orders. Would you like to see our pricing list?"
        }

    def generate_message(self, lead_data):
        """Generate a personalized message based on lead attributes."""
        name = lead_data.get("buyer_name", "there")
        product = lead_data.get("product_category", "the item")
        intent_score = lead_data.get("intent_score", 0)
        
        # Select template based on intent score and keywords
        if intent_score > 0.8:
            template = self.templates["urgent"]
        elif "bulk" in lead_data.get("buyer_request_snippet", "").lower():
            template = self.templates["bulk"]
        else:
            template = self.templates["general"]
            
        return template.format(name=name, product=product)

    def select_leads_for_outreach(self, db: Session, min_intent=0.7):
        """Select top-tier leads that haven't been contacted yet."""
        return db.query(models.Lead).filter(
            models.Lead.status == models.ContactStatus.NOT_CONTACTED,
            models.Lead.intent_score >= min_intent
        ).order_by(models.Lead.intent_score.desc()).all()

    def mark_contacted(self, db: Session, lead_id: str):
        """Mark a lead as contacted and update timestamp."""
        try:
            lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
            if lead:
                lead.status = models.ContactStatus.CONTACTED
                lead.last_contact_attempt = datetime.now()
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Error marking lead as contacted: {e}")
            return False

    def track_response(self, db: Session, lead_id: str, response_text: str):
        """Track and analyze response from a buyer with detailed metrics."""
        try:
            lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
            if lead:
                now = datetime.now()
                
                # Update response metrics
                lead.response_count += 1
                
                if lead.last_contact_attempt:
                    # Calculate response time in minutes
                    diff = now - lead.last_contact_attempt
                    resp_time = diff.total_seconds() / 60
                    
                    if lead.average_response_time_mins:
                        # Rolling average
                        lead.average_response_time_mins = (lead.average_response_time_mins + resp_time) / 2
                    else:
                        lead.average_response_time_mins = resp_time
                
                lead.last_response_received = now
                
                # Improved conversion detection: Positive intent check
                # Check for positive signals while excluding negative context
                positive_words = ["interested", "price", "buy", "send", "yes", "deal", "whatsapp", "call"]
                negative_context = ["not interested", "too expensive", "no thanks", "stop", "wrong number"]
                
                text_lower = response_text.lower()
                is_positive = any(word in text_lower for word in positive_words)
                is_negative = any(context in text_lower for context in negative_context)
                
                if is_positive and not is_negative:
                    lead.status = models.ContactStatus.CONVERTED
                    # Real-world conversion signal: positive response received
                    lead.conversion_rate = 100.0 
                else:
                    lead.status = models.ContactStatus.CONTACTED
                    
                lead.notes = f"Response: {response_text}"
                db.commit()
                return lead.status
            return None
        except Exception as e:
            db.rollback()
            print(f"Error tracking response: {e}")
            return None

    def check_non_response_history(self, db: Session, phone: str = None, email: str = None):
        """Check if this contact has a history of not responding to outreach."""
        if not phone and not email:
            return False
            
        query = db.query(models.Lead)
        filters = []
        if phone:
            filters.append(models.Lead.contact_phone == phone)
        if email:
            filters.append(models.Lead.contact_email == email)
            
        # Look for leads that were contacted but have 0 responses
        history = query.filter(
            or_(*filters),
            models.Lead.status == models.ContactStatus.CONTACTED,
            models.Lead.response_count == 0
        ).all()
        
        return len(history) >= 2 # Flag if they've ignored us twice before

    def get_conversion_analytics(self, db: Session):
        """Get analytics for conversion rates across platforms."""
        stats = {}
        platforms = db.query(models.Lead.source_platform).distinct().all()
        for (platform,) in platforms:
            total = db.query(models.Lead).filter(models.Lead.source_platform == platform).count()
            contacted = db.query(models.Lead).filter(
                models.Lead.source_platform == platform,
                models.Lead.status != models.ContactStatus.NOT_CONTACTED
            ).count()
            converted = db.query(models.Lead).filter(
                models.Lead.source_platform == platform,
                models.Lead.status == models.ContactStatus.CONVERTED
            ).count()
            
            stats[platform] = {
                "total_leads": total,
                "outreach_sent": contacted,
                "conversions": converted,
                "conversion_rate": (converted / contacted * 100) if contacted > 0 else 0
            }
        return stats

