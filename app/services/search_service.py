
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.scrapers.registry import get_active_scrapers
from app.models.lead import Lead
from app.db.database import SessionLocal
from app.config import runtime as settings
from app.scrapers.intent_scoring import score_intent

logger = logging.getLogger(__name__)

async def search(query: str, location: str):
    all_results = []
    scrapers = get_active_scrapers()
    for scraper in scrapers:
        results = await scraper.search(query, location)
        all_results.extend(results)
    
    verified_leads = []
    for result in all_results:
        intent_score = score_intent(result["title"])
        
        if settings.PIPELINE_MODE == "strict":
             if intent_score < settings.MIN_INTENT_SCORE:
                 continue
                 
        verified_leads.append({
            **result,
            "intent_score": intent_score
        })
        
    save_leads_to_db(verified_leads)
    return verified_leads

def save_leads_to_db(leads): 
    db = SessionLocal() 

    for lead in leads: 
        existing = db.query(Lead).filter_by(url=lead["url"]).first() 
        if existing: 
            continue 

        db_lead = Lead( 
            title=lead["title"], 
            price=lead.get("price"), 
            location="Kenya", 
            source=lead["source"], 
            url=lead["url"], 
            intent_score=lead["intent_score"] 
        ) 

        db.add(db_lead) 

    db.commit() 
    db.close()
