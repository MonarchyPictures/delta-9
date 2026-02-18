from typing import List
from app.db.database import SessionLocal
from app.models.lead import Lead

def get_leads(limit: int): 
     db = SessionLocal() 
     leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all() 
     db.close() 
     return leads
