
import sys
import os
from datetime import datetime, timedelta
import uuid

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal, engine
from app.db import models

def seed_live_leads():
    # Ensure tables exist
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    now = datetime.now()
    
    test_leads = [
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Facebook",
            "post_link": "https://fb.com/live1",
            "location_raw": "Nairobi, Kenya",
            "buyer_request_snippet": "Need a water tank 10,000L urgently! Contact me at 0712345678",
            "product_category": "Water Tanks",
            "intent_score": 0.95,
            "availability_status": "Available Now",
            "competition_count": 1,
            "is_unique_request": 1,
            "optimal_response_window": "Next 5 mins",
            "peak_response_time": "6PM - 9PM",
            "created_at": now - timedelta(minutes=2),
            "is_contact_verified": 1,
            "contact_reliability_score": 95.0,
            "preferred_contact_method": "WhatsApp",
            "readiness_level": "HOT",
            "deal_probability": 90.0,
            "confidence_score": 9.0,
            "is_genuine_buyer": 1,
            "status": "NOT_CONTACTED"
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Reddit",
            "post_link": "https://reddit.com/r/kenya/live2",
            "location_raw": "Mombasa, Kenya",
            "buyer_request_snippet": "Looking for a used Toyota Camry 2005. PM me or call 0733123456",
            "product_category": "Vehicles",
            "intent_score": 0.85,
            "availability_status": "Available Now",
            "competition_count": 3,
            "is_unique_request": 0,
            "optimal_response_window": "Next 30 mins",
            "peak_response_time": "9AM - 12PM",
            "created_at": now - timedelta(minutes=10),
            "is_contact_verified": 1,
            "contact_reliability_score": 85.0,
            "preferred_contact_method": "Phone",
            "readiness_level": "WARM",
            "deal_probability": 75.0,
            "confidence_score": 8.0,
            "is_genuine_buyer": 1,
            "status": "NOT_CONTACTED"
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "TikTok",
            "post_link": "https://tiktok.com/@user/live3",
            "location_raw": "Kisumu, Kenya",
            "buyer_request_snippet": "I want to buy a high-end laptop for design work. Budget is 150k. Email: designer@gmail.com",
            "product_category": "Electronics",
            "intent_score": 0.7,
            "availability_status": "Recently Contacted",
            "competition_count": 5,
            "is_unique_request": 0,
            "optimal_response_window": "Next 1 hour",
            "peak_response_time": "2PM - 5PM",
            "created_at": now - timedelta(hours=1),
            "is_contact_verified": 1,
            "contact_reliability_score": 60.0,
            "preferred_contact_method": "Email",
            "readiness_level": "RESEARCHING",
            "deal_probability": 40.0,
            "confidence_score": 7.0,
            "is_genuine_buyer": 1,
            "status": "NOT_CONTACTED"
        }
    ]
    
    for lead_data in test_leads:
        lead = models.Lead(**lead_data)
        db.add(lead)
    
    db.commit()
    db.close()
    print(f"Successfully seeded {len(test_leads)} live leads.")

if __name__ == "__main__":
    seed_live_leads()
