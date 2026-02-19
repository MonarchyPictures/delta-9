from typing import List
from app.db.database import SessionLocal
from app.models.lead import Lead

from datetime import datetime, timedelta
from sqlalchemy import func

def get_leads(limit: int): 
     db = SessionLocal() 
     leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all() 
     db.close() 
     return leads

def get_dashboard_stats():
    db = SessionLocal()
    try:
        # Calculate time threshold for 24h
        time_24h_ago = datetime.utcnow() - timedelta(hours=24)
        
        # 1. Active Listings (24h)
        active_listings_24h = db.query(Lead).filter(Lead.created_at >= time_24h_ago).count()
        
        # 2. Urgent Sellers (urgency_level='high' OR urgency_score > 0.7)
        urgent_sellers = db.query(Lead).filter(
            (Lead.urgency_level == 'high') | (Lead.urgency_score > 0.7)
        ).count()
        
        # 3. WhatsApp Taps (using response_count as proxy or random/0 if not tracked)
        # Since we don't strictly track taps in DB yet, we'll use leads with whatsapp_link
        # as a proxy for "potential" taps or just return a placeholder.
        # Let's count leads with whatsapp links for now.
        whatsapp_taps_today = db.query(Lead).filter(Lead.whatsapp_link.isnot(None)).count()
        
        # 4. High Intent Matches (intent_score > 0.8)
        high_intent_matches = db.query(Lead).filter(Lead.intent_score > 0.8).count()
        
        return {
            "active_listings_24h": active_listings_24h,
            "urgent_sellers": urgent_sellers,
            "whatsapp_taps_today": whatsapp_taps_today,
            "high_intent_matches": high_intent_matches
        }
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {
            "active_listings_24h": 0,
            "urgent_sellers": 0,
            "whatsapp_taps_today": 0,
            "high_intent_matches": 0
        }
    finally:
        db.close()

