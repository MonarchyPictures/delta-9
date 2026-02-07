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
        Process a single raw lead result from a scraper.
        Performs validation, scoring, and normalization.
        """
        text = raw_data.get('intent_text', '')
        link = raw_data.get('link', '')
        
        if not text or not link:
            return None

        # 1. Intent Validation
        if not self.scorer.validate_lead(text):
            logger.debug(f"Lead rejected by validation: {link}")
            return None

        # 2. Scoring & Readiness
        intent_score = raw_data.get('confidence_score') or self.scorer.calculate_intent_score(text)
        readiness_level, readiness_score = self.scorer.analyze_readiness(text)

        # 3. Extraction
        phone = self._extract_phone(text)
        buyer_name = self._extract_name(text, raw_data.get('source', 'Web'))
        urgency = self._parse_urgency(text)
        
        # 4. Normalization
        lead_id = str(uuid.uuid5(uuid.NAMESPACE_URL, link))
        
        # Check if exists
        existing = self.db.query(models.Lead).filter(models.Lead.source_url == link).first()
        if existing:
            return None

        lead = models.Lead(
            id=lead_id,
            buyer_name=buyer_name,
            contact_phone=phone,
            product_category=raw_data.get('product', 'General'),
            quantity_requirement="1",
            intent_score=intent_score,
            location_raw=raw_data.get('location', 'Kenya'),
            radius_km=random.randint(1, 50),
            source_platform=raw_data.get('source', 'Web'),
            request_timestamp=datetime.now(timezone.utc), # Simplification for now
            whatsapp_link=self._generate_whatsapp_link(phone, raw_data.get('product', 'Product')),
            contact_method=raw_data.get('contact_method'),
            source_url=link,
            http_status=200,
            created_at=datetime.now(timezone.utc),
            property_country="Kenya",
            buyer_request_snippet=text[:500],
            urgency_level=urgency,
            is_verified_signal=1
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
        clean_text = text.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '')
        phone_pattern = r'(\+254|254|0)(7|1)\d{8}'
        match = re.search(phone_pattern, clean_text)
        if match:
            found = match.group(0)
            if found.startswith('0'):
                return '254' + found[1:]
            if found.startswith('+'):
                return found.replace('+', '')
            if found.startswith('254'):
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
