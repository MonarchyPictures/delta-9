import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import asyncio
from app.db.database import SessionLocal
from app.scrapers import run_scrapers
from app.ingestion import ingest_leads

from ..db import models
from ..utils.playwright_helpers import get_page_content
from ..utils.intent_scoring import IntentScorer
from ..intelligence.verification import verify_leads as cross_source_verify
from ..config import PIPELINE_MODE, PROD_STRICT, PIPELINE_CATEGORY
from app.config.runtime import REQUIRE_VERIFICATION
from app.scrapers.verifier import is_verified_signal

logger = logging.getLogger(__name__)

async def run_pipeline_for_query(query: str, location: str = "Kenya") -> List[models.Lead]:
    """
    Orchestrates the search pipeline:
    1. Executes search (async).
    2. Processes raw results into Lead objects.
    3. Returns list of new leads.
    """
    try:
        # 1️⃣ Run scrapers
        raw_results = await run_scrapers(query, location)

        # 2️⃣ Ingest & deduplicate (sync blocking call moved to thread)
        verified_leads = await asyncio.to_thread(ingest_leads, raw_results)

        # 3️⃣ Return for DB saving
        return verified_leads
        
    except Exception as e:
        logger.error(f"Pipeline execution failed for query '{query}': {e}")
        return []

class LeadPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.scorer = IntentScorer()

    def verify_leads(self, leads: List[Dict[str, Any]], strict_mode: bool = True): 
        """
        Verification Layer: Filter leads based on confidence score and cross-source verification.
        The brain in app.scrapers.verifier now handles adaptive thresholds.
        """
        # First apply cross-source and adaptive threshold verification
        verified_leads_with_reasons = cross_source_verify(leads)
        
        verified = [] 
        warnings = [] 
        for lead in verified_leads_with_reasons: 
            # The verifier brain now sets 'verified' based on trust, cross-match, OR adaptive thresholds
            is_verified = lead.get('verified', False)
            
            # ALWAYS append, just annotate if unverified
            verified.append(lead)
            
            if not is_verified:
                warnings.append(f"Unverified signal from {lead.get('source', 'Unknown')} ({lead.get('verification_reason', 'low_confidence')})") 
                
        return verified, warnings

    def _reject(self, lead_data: Dict[str, Any], reason: str):
        """
        Helper to log rejection reasons clearly.
        """
        url = lead_data.get('url', 'No URL')
        logger.info(f"[REJECTED] {url} | Reason: {reason}")
        return None

    def process_raw_lead(self, raw_data: Dict[str, Any]) -> Optional[models.Lead]:
        """
        Process a single standardized raw lead from a "dumb" scraper.
        The Engine ("smart") decides if this is a buyer and extracts details.
        """
        text = raw_data.get('text') or raw_data.get('snippet', '')
        url = raw_data.get('url', '')
        
        if not text or not url:
            return self._reject(raw_data, "Missing required fields (text or url)")

        # 1. Intent Validation (Smart Engine Decision)
        # We now FLAG instead of REJECT
        validation = self.scorer.validate_lead_debug(text)
        intent_status = "BUYER"
        
        if not validation["valid"]:
            score = validation["score"]
            if validation["classification"] == "SELLER":
                intent_status = "SELLER"
                # If Strict Mode is on, we might reject sellers
                if PROD_STRICT:
                     return self._reject(raw_data, f"Classified as SELLER (Score: {score})")
            else:
                intent_status = "low_confidence"
                
            logger.info(f"Lead flagged as {intent_status}: {url} | Score: {score} | Reason: {validation['reasons']}")
            # DO NOT REJECT - We keep everything now unless PROD_STRICT is explicitly True for sellers
        else:
            intent_status = "BUYER"

        # 2. Scoring & Readiness (Smart Engine Logic)
        intent_score = self.scorer.calculate_intent_score(text)
        readiness_level, readiness_score = self.scorer.analyze_readiness(text)

        # 3. Extraction (Smart Engine Logic)
        # Handle nested contact info from ScraperSignal
        contact_info = raw_data.get('contact', {})
        
        phone = raw_data.get('phone') or contact_info.get('phone') or self._extract_phone(text)
        email = raw_data.get('email') or contact_info.get('email')
        
        buyer_name = raw_data.get('name') or self._extract_name(text, raw_data.get('source', 'Web'))
        urgency = self._parse_urgency(text)
        
        # 4. Normalization
        lead_id = uuid.uuid5(uuid.NAMESPACE_URL, url)
        
        # Check if exists (Re-enabled with logging)
        existing = self.db.query(models.Lead).filter(models.Lead.source_url == url).first()
        if existing:
            return self._reject(raw_data, "Duplicate lead (already in DB)")

        # Determine product category dynamically from raw_data or query
        product_category = raw_data.get('product_category') or PIPELINE_CATEGORY or "General"

        # Verification Status (Soft Flagging)
        verified_status = is_verified_signal(text, url)
        verification_flag = "verified" if verified_status else "unverified"
        
        # Contact Flagging (Relaxed Requirement)
        contact_flag = "ok"
        if not phone and not email:
            contact_flag = "missing_contact"
            logger.info(f"Lead missing contact info: {url} (Flagged as {contact_flag})")
            # We do NOT return None. We proceed.

        # Enforce REQUIRE_VERIFICATION check (Soft Flag only, NO REJECTION)
        if REQUIRE_VERIFICATION and not verified_status:
            logger.info(f"Lead unverified under strict policy: {url} (Flagged as {verification_flag})")
            # We do NOT return None. We proceed.

        lead = models.Lead(
            id=lead_id,
            buyer_name=buyer_name,
            contact_phone=phone,
            contact_email=email,
            product_category=product_category.capitalize(),
            quantity_requirement="1",
            intent_score=intent_score,
            location_raw=raw_data.get('location', 'Global'),
            radius_km=0.0,
            source_platform=raw_data.get('source', 'Web'),
            request_timestamp=datetime.now(timezone.utc),
            whatsapp_link=self._generate_whatsapp_link(phone, product_category),
            contact_method="WhatsApp" if phone else "Needs Outreach",
            source_url=url,
            http_status=200,
            created_at=datetime.now(timezone.utc),
            property_country="Global",
            buyer_request_snippet=text[:500],
            urgency_level=urgency,
            is_verified_signal=1 if verified_status else 0,
            verification_flag=verification_flag,
            contact_flag=contact_flag,
            is_hot_lead=1 if intent_score >= 0.8 else 0,
            intent_type=intent_status
        )
        
        return lead

    def save_leads(self, leads: List[models.Lead]):
        """Bulk save leads to database."""
        if not leads:
            return
            
        try:
            for lead in leads:
                self.db.add(lead)
            self.db.commit()
            logger.info(f"Pipeline: Saved {len(leads)} new leads.")
        except Exception as e:
            logger.error(f"Pipeline: Error saving leads: {e}")
            self.db.rollback()

    def _extract_phone(self, text: str) -> Optional[str]:
        import re
        # Generalized phone extraction: looks for + followed by digits, or common formats
        # Supports international formats (+1, +44, +254, etc.)
        phone_patterns = [
            r'\+(\d{1,3})\s?(\d{3})\s?(\d{3})\s?(\d{3,4})', # +254 712 345 678
            r'\+(\d{1,15})',                                 # +254712345678
            r'(?<!\d)(07\d{8}|01\d{8})(?!\d)',               # Kenyan local 07... or 01...
            r'(?<!\d)(\d{10,15})(?!\d)'                      # Long digit strings
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                found = match.group(0).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                if found.startswith('0') and len(found) == 10:
                    return '254' + found[1:]
                if found.startswith('+'):
                    return found.replace('+', '')
                return found
        return None

    def _extract_name(self, text: str, source: str) -> str:
        import re
        name_patterns = [
            r"Post by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"Contact:\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"Name:\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return "Verified Market Signal"

    def _parse_urgency(self, text: str) -> str:
        text = text.lower()
        high = ["asap", "urgently", "urgent", "immediately", "now", "today"]
        if any(kw in text for kw in high):
            return "high"
        return "medium"

    def _generate_whatsapp_link(self, phone: str, product: str) -> Optional[str]:
        if not phone:
            return None
        import urllib.parse
        message = f"Hello, I saw your request for {product}. I can help you with that!"
        return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"
