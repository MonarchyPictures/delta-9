
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from ..db import models
from ..intelligence_v2 import (
    calculate_intent_score,
    calculate_final_intelligence_score,
    classify_lead_priority,
    extract_contact_info,
    FLOOR,
    STRICT_PUBLIC
)

logger = logging.getLogger(__name__)

def ingest_signal(db: Session, signal: Dict[str, Any], product_query: str = "Unknown"):
    """
    Standardized Ingestion Gate:
    1. Receives DUMB signal from scraper.
    2. Runs Intelligence Layer (v2).
    3. Enforces FLOOR threshold.
    4. Maps to 10-field Lead schema.
    """
    raw_text = signal.get("text", "")
    source = signal.get("source", "unknown")
    
    # 1. 🧠 Intelligence Layer: Intent Detection
    raw_intent = calculate_intent_score(raw_text)
    
    # 2. 🧠 Intelligence Layer: Semantic/Confidence Scoring
    # For raw signals, semantic_score is a baseline of 0.5 unless we have comparison data
    semantic_baseline = 0.5 
    
    final_score = calculate_final_intelligence_score(
        raw_intent_score=raw_intent,
        semantic_score=semantic_baseline,
        text=raw_text,
        source_name=source,
        lead_data={
            "location_raw": signal.get("location", "Kenya"),
            "contact_phone": signal.get("contact", {}).get("phone"),
            "buyer_request_snippet": raw_text
        }
    )
    
    # 3. 🚦 Threshold Enforcement
    if final_score < FLOOR:
        logger.info(f"SIGNAL REJECTED: Score {final_score} below floor {FLOOR} for source {source}")
        return False

    # 4. 📞 Contact Extraction (Moved from Scraper to Intelligence)
    contacts = extract_contact_info(raw_text)
    # Merge with any contact info already found by scraper
    signal_contacts = signal.get("contact", {})
    phone = signal_contacts.get("phone") or contacts.get("phone")
    whatsapp = signal_contacts.get("whatsapp") or contacts.get("whatsapp")
    email = signal_contacts.get("email") or contacts.get("email")

    try:
        # Deduplication by URL
        source_url = signal.get("url")
        if source_url:
            existing = db.query(models.Lead).filter(models.Lead.source_url == source_url).first()
            if existing:
                return False
        
        # 5. 🗺️ Mapping to 10-field schema (+ internal metadata)
        lead_id = str(uuid.uuid4())
        priority = classify_lead_priority(final_score)
        
        db_lead = models.Lead(
            id=lead_id,
            buyer_name=signal.get("author") or "Market Signal",
            contact_phone=phone,
            product_category=product_query,
            intent_score=raw_intent,
            location_raw=signal.get("location", "Kenya"),
            source_platform=source,
            request_timestamp=datetime.fromisoformat(signal["timestamp"]) if signal.get("timestamp") else datetime.utcnow(),
            whatsapp_link=whatsapp,
            source_url=source_url,
            buyer_request_snippet=raw_text[:500], # Keep snippet manageable
            urgency_level=priority,
            confidence_score=final_score,
            contact_status="verified" if phone or whatsapp else "needs_outreach",
            is_hot_lead=1 if final_score >= STRICT_PUBLIC else 0,
            tap_count=0
        )
        
        db.add(db_lead)
        
        # Log Activity
        log = models.ActivityLog(
            event_type="SIGNAL_INGESTED",
            lead_id=lead_id,
            extra_metadata={
                "source": source,
                "score": final_score,
                "priority": priority
            }
        )
        db.add(log)
        
        db.commit()
        logger.info(f"SIGNAL ACCEPTED: {priority} lead saved from {source} (Score: {final_score})")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"INGESTION ERROR: {str(e)}")
        return False

def ingest_lead(db: Session, lead_data: Dict[str, Any]):
    """Legacy wrapper for backward compatibility"""
    # Map old format to signal format if needed, or just redirect
    return ingest_signal(db, lead_data)
