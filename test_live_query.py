
import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta

# Add parent directory to path to import app
sys.path.append(os.getcwd())

from app.db import models, database

def test_live_query():
    db = database.SessionLocal()
    try:
        location = "Kenya"
        live = True
        verified_only = False
        
        db_query = db.query(models.Lead)
        
        # Strict Verification Filter
        if verified_only: # Frontend sends verified_only=false
            db_query = db_query.filter(models.Lead.is_contact_verified == 1)
            db_query = db_query.filter(models.Lead.contact_reliability_score >= 10)
        
        # Live Feed Logic
        if live:
            db_query = db_query.order_by(models.Lead.created_at.desc())
            db_query = db_query.filter(models.Lead.confidence_score >= 0.5)
        
        # Location Filtering
        if location:
            if location.lower() == "kenya":
                db_query = db_query.filter(or_(
                    models.Lead.location_raw.ilike("%Kenya%"),
                    models.Lead.location_raw == "Unknown",
                    models.Lead.location_raw == None
                ))
            else:
                db_query = db_query.filter(models.Lead.location_raw.ilike(f"%{location}%"))
        
        count = db_query.count()
        print(f"Total leads passing live=true filter: {count}")
        
        leads = db_query.limit(5).all()
        for i, lead in enumerate(leads):
            print(f"{i+1}. {lead.source_platform} | Confidence: {lead.confidence_score} | Location: {lead.location_raw} | Created: {lead.created_at}")
            print(f"   Snippet: {lead.buyer_request_snippet[:100]}...")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_live_query()
