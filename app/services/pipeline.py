import logging
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from ..db import models
from ..utils.playwright_helpers import get_page_content
from ..utils.intent_scoring import IntentScorer
from ..intelligence.verification import verify_leads as cross_source_verify
from ..config import PIPELINE_MODE, PROD_STRICT, PIPELINE_CATEGORY

logger = logging.getLogger(__name__)

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
            
            if is_verified: 
                verified.append(lead) 
            else: 
                if not strict_mode: 
                    verified.append(lead) 
                    warnings.append(f"Unverified signal from {lead.get('source', 'Unknown')} ({lead.get('verification_reason', 'low_confidence')})") 
        return verified, warnings

    def process_raw_lead(self, raw_data: Dict[str, Any]) -> Optional[models.Lead]:
        """
        Process a single standardized raw lead from a "dumb" scraper.
        The Engine ("smart") decides if this is a buyer and extracts details.
        """
        text = raw_data.get('text', '')
        url = raw_data.get('url', '')
        
        if not text or not url:
            return None

        # 1. Intent Validation (Smart Engine Decision)
        if not self.scorer.validate_lead(text):
            logger.debug(f"Lead rejected by engine validation: {url}")
            return None

        # 2. Scoring & Readiness (Smart Engine Logic)
        intent_score = self.scorer.calculate_intent_score(text)
        readiness_level, readiness_score = self.scorer.analyze_readiness(text)

        # 3. Extraction (Smart Engine Logic)
        phone = raw_data.get('phone') or self._extract_phone(text)
        buyer_name = raw_data.get('name') or self._extract_name(text, raw_data.get('source', 'Web'))
        urgency = self._parse_urgency(text)
        
        # 4. Normalization
        lead_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
        
        # Check if exists
        existing = self.db.query(models.Lead).filter(models.Lead.source_url == url).first()
        if existing:
            return None

        # Determine product category dynamically from raw_data or query
        product_category = raw_data.get('product_category') or PIPELINE_CATEGORY or "General"

        lead = models.Lead(
            id=lead_id,
            buyer_name=buyer_name,
            contact_phone=phone,
            product_category=product_category.capitalize(),
            quantity_requirement="1",
            intent_score=intent_score,
            location_raw=raw_data.get('location', 'Global'),
            radius_km=random.randint(1, 50),
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
            is_verified_signal=1,
            is_hot_lead=1 if intent_score >= 0.8 else 0
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
