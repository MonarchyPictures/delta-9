from app.db.database import SessionLocal, engine
from app.db import models, database
from datetime import datetime, timedelta
import uuid


def seed_data():
    # Create tables
    models.Base.metadata.create_all(bind=database.engine)
    db = SessionLocal()
    
    # Sample leads
    sample_leads = [
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Reddit",
            "post_link": "https://reddit.com/r/tires/1",
            "location_raw": "New York, NY",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "buyer_request_snippet": "Looking for winter tires for my SUV, need them ASAP!",
            "product_category": "Tires",
            "intent_score": 0.9,
            "status": models.CRMStatus.NEW,
            "created_at": datetime.utcnow() - timedelta(hours=2)
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Facebook",
            "post_link": "https://facebook.com/groups/2",
            "location_raw": "Brooklyn, NY",
            "latitude": 40.6782,
            "longitude": -73.9442,
            "buyer_request_snippet": "Anyone selling bulk sugar? Need 500kg for my bakery.",
            "product_category": "Sugar",
            "intent_score": 0.85,
status=models.CRMStatus.NEW,
            "created_at": datetime.utcnow() - timedelta(hours=24)
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Twitter",
            "post_link": "https://twitter.com/user/3",
            "location_raw": "Los Angeles, CA",
            "latitude": 34.0522,
            "longitude": -118.2437,
            "buyer_request_snippet": "ISO furniture for my new apartment. Buying today!",
            "product_category": "Furniture",
            "intent_score": 0.95,
            "status": models.ContactStatus.NOT_CONTACTED,
            "created_at": datetime.utcnow() - timedelta(hours=48)
        }
    ]
    
    for lead_data in sample_leads:
        lead = models.Lead(**lead_data)
        db.add(lead)
    
    try:
        db.commit()
        print("Database seeded successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()