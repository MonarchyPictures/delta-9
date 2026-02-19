
import logging
import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.scrapers.registry import get_active_scrapers_sorted
from app.models.lead import Lead
from app.db.database import SessionLocal
from app.config import runtime as settings
from app.services.intent_engine import calculate_intent_score
from app.services.market_classifier import classify_market_side
from app.services.urgency_ranker import calculate_urgency_score
from app.services.persona_detector import detect_persona
from app.services.confidence_engine import calculate_confidence
from app.services.page_enricher import enrich_lead_data

logger = logging.getLogger(__name__)

SOURCE_WEIGHTS = {
    "serpapi_google": 1.0,
    "jiji": 0.95,
    "facebook": 0.90,
    "duckduckgo": 0.90,
    "google_maps": 0.85
}

def extract_phone(raw):
    """
    Extract phone numbers from raw lead data.
    Checks 'phone' field first, then tries to extract from 'title' or 'snippet'.
    """
    if raw.get("phone"):
        return raw.get("phone")
    
    text = f"{raw.get('title', '')} {raw.get('snippet', '')}"
    # Match +254... or 07... or 01...
    phone_pattern = r'(\+?254|0)?([17]\d{8})'
    match = re.search(phone_pattern, text)
    if match:
        return match.group(0)
    return ""

def is_foreign_content(text: str, url: str) -> bool:
    """
    Detect if the content is explicitly foreign (US/UK/etc) to filter out ads/irrelevant results.
    Target: Kenya Only.
    """
    text_lower = text.lower()
    url_lower = url.lower()
    
    # Strong foreign indicators
    foreign_keywords = [
        "california", "united states", "usa", "new york", "texas", "london", "uk", 
        "ontario", "canada", "dubai", "uae", "australia", "germany",
        "ships from usa", "located in usa", "store in usa"
    ]
    
    # Check all keywords
    for keyword in foreign_keywords:
        # Simple substring check
        if keyword in text_lower:
             # Exception: "imported from Dubai" is okay, but "Dubai" alone might be ambiguous.
             # If "in Dubai" or "at Dubai" -> Foreign.
             # If "from Dubai" -> Allow (likely import).
             if keyword in ["dubai", "uae", "usa", "uk", "germany", "china"]:
                 if f"from {keyword}" in text_lower:
                     continue # Allow "from USA", "from Dubai" (Imports)
                 if f"import {keyword}" in text_lower:
                     continue
             
             return True
    
    # Specific locations to ban if they appear as the primary location
    # Use regex for state codes to avoid false positives
    if re.search(r'\bCA\b', text) or re.search(r'\bNY\b', text) or re.search(r'\bTX\b', text):
        return True
        
    return False

def extract_email(raw):
    """
    Extract email from raw lead data.
    """
    if raw.get("email"):
        return raw.get("email")
        
    text = f"{raw.get('title', '')} {raw.get('snippet', '')}"
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    if match:
        return match.group(0)
    return ""

def extract_name(text):
    """
    Attempt to extract a name from the title or return a default.
    """
    if not text:
        return "Unknown Buyer"
    
    match = re.search(r"Post by\s+([A-Z][a-z]*\s+[A-Z][a-z]*)", text)
    if match:
        return match.group(1)
        
    return "Unknown Buyer"

def normalize_lead(raw, source):
    # Ensure source is passed correctly
    final_source = source if source != "unknown" else raw.get("source", "unknown")
    
    normalized = {
        "buyer_name": raw.get("buyer_name") or extract_name(raw.get("title")),
        "title": raw.get("title"),
        "price": raw.get("price") or "",
        "location": raw.get("location") or "Kenya",
        "phone": extract_phone(raw),
        "email": extract_email(raw),
        "source": final_source,
        "intent_score": raw.get("intent_score", 0.5), # Default to 0.5 if missing
        "url": raw.get("url"),
        "snippet": raw.get("snippet"),
        "market_side": raw.get("market_side", "unknown") # Preserve market_side
    }
    return normalized

import uuid

def save_leads_to_db(leads_data: List[Dict]):
    db = SessionLocal()
    try:
        saved_count = 0
        for data in leads_data:
            url = data.get("url")
            if not url: continue
            
            # Check existence by URL
            exists = db.query(Lead).filter(Lead.url == url).first()
            if exists: continue

            lead = Lead(
                id=uuid.uuid4(),
                buyer_name=data.get("buyer_name"),
                title=data.get("title"),
                price=str(data.get("price") or ""),
                location=data.get("location"),
                contact_phone=data.get("phone"),
                contact_email=data.get("email"),
                source=data.get("source"),
                url=url,
                intent_score=data.get("intent_score"),
                created_at=datetime.now(timezone.utc),
                is_verified_signal=1,
                verification_flag=data.get("badge", "verified"),
                status=data.get("status", "NEW"), # Map to CRMStatus string if needed, or let Enum handle
                buyer_request_snippet=data.get("snippet") or data.get("title"),
                urgency_score=data.get("urgency_score"),
                urgency_level=data.get("badge", "low"), # Map badge to urgency level for DB
                confidence_score=data.get("confidence", 0.0),
                intent_type=data.get("persona", "Unknown") # Map persona to intent_type
            )
            db.add(lead)
            saved_count += 1
        db.commit()
        logger.info(f"Saved {saved_count} new leads to DB.")
    except Exception as e:
        logger.error(f"Failed to save leads: {e}")
        db.rollback()
    finally:
        db.close()

def process_and_score(results):
    processed = []
    rejected = []
    for result in results:
        # First normalize the result
        normalized = normalize_lead(result, result.get("source", "unknown"))
        
        # 0. Foreign Content Filter (Kenya Lock)
        full_text = f"{normalized['title']} {normalized.get('snippet', '')} {normalized.get('location', '')}"
        if is_foreign_content(full_text, normalized.get("url", "")):
             rejected.append({
                 "title": normalized["title"], 
                 "reason": "Foreign content detected (US/UK/etc)",
                 "source": normalized["source"]
             })
             continue

        # 1. Market Side Filter (Supply vs Demand)
        # Use existing if available, otherwise classify
        market_side = normalized.get("market_side")
        if not market_side or market_side == "unknown":
            market_side = classify_market_side(normalized["title"])
            normalized["market_side"] = market_side

        if market_side == "supply":
             rejected.append({
                 "title": normalized["title"], 
                 "reason": "Classified as Supply/Seller side",
                 "source": normalized["source"]
             })
             continue

        # 2. AI Pipeline Processing
        
        # Intent Score
        if not normalized.get("intent_score") or normalized["intent_score"] == 0.5:
            normalized["intent_score"] = calculate_intent_score(normalized["title"])
            
        # Apply source weighting
        source_weight = SOURCE_WEIGHTS.get(normalized["source"], 0.8)
        normalized["intent_score"] *= source_weight
        
        # Urgency Score
        normalized["urgency_score"] = calculate_urgency_score(f"{normalized['title']} {normalized.get('snippet', '')}")
        
        # Persona Detection
        normalized["persona"] = detect_persona(f"{normalized['title']} {normalized.get('snippet', '')}", normalized["source"])
        
        # Confidence Score
        normalized["confidence"] = calculate_confidence(
            normalized["intent_score"], 
            normalized["urgency_score"], 
            source_weight
        )
        
        # Page Enrichment (adds badge, ensures fields)
        normalized = enrich_lead_data(normalized)

        # 3. Filtering Logic
        
        # Use 0.4 as absolute minimum for "verified" status after weighting
        MIN_SCORE = 0.4
        if normalized["intent_score"] < MIN_SCORE:
            rejected.append({
                 "title": normalized["title"], 
                 "reason": f"Low intent score: {normalized['intent_score']:.2f} < {MIN_SCORE}",
                 "source": normalized["source"]
             })
            continue
        
        processed.append(normalized)
    return processed, rejected

async def search(query: str, location: str):
    metrics = {
        "scrapers_run": [],
        "total_found": 0,
        "total_verified": 0,
        "rejected": []
    }

    # Micro-query guard to save credits
    if len(query) < 3:
        msg = f"Query '{query}' is too short. Skipping."
        logger.warning(msg)
        return {
            "results": [], 
            "metrics": metrics, 
            "message": msg,
            "status": "skipped"
        }

    scrapers = get_active_scrapers_sorted()
    verified_leads = []
    
    for scraper in scrapers:
        scraper_name = scraper.__class__.__name__
        metrics["scrapers_run"].append(scraper_name)
        logger.info(f"Running scraper: {scraper_name}")
        
        try:
            results = await scraper.search(query, location)
            logger.info(f"Scraper {scraper_name} returned {len(results)} raw results")
            metrics["total_found"] += len(results)
            
            processed, rejected_items = process_and_score(results)
            logger.info(f"Scraper {scraper_name} yielded {len(processed)} verified leads (Rejected: {len(rejected_items)})")
            verified_leads.extend(processed)
            metrics["total_verified"] += len(processed)
            metrics["rejected"].extend(rejected_items)
            
            if processed and scraper_name == "SerpAPIScraper":
                logger.info("SerpAPIScraper returned results. Continuing to other scrapers for maximum recall.")
                # Disabled short-circuit to allow Jiji/others to run even if SerpAPI finds leads
                # break
                pass
                
        except Exception as e:
            logger.error(f"Scraper {scraper_name} failed: {e}")
            
    # Save to DB for persistence
    if verified_leads:
        save_leads_to_db(verified_leads)
            
    return {
        "results": verified_leads,
        "metrics": metrics,
        "count": len(verified_leads),
        "status": "success" if verified_leads else "zero_results"
    }
