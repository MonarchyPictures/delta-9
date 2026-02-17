import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

class MockScraper(BaseScraper):
    """
    A scraper that returns hardcoded results for testing pipeline logic.
    Guaranteed to return results, including duplicates to test deduplication.
    """
    source = "mock_scraper"
    priority_score = 100.0 # High priority to ensure it runs

    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]:
        logger.info(f"MOCK: Generating test leads for query='{query}'")
        
        results = []
        now = datetime.now(timezone.utc)
        
        # 1. Valid High-Quality Lead
        lead1 = ScraperSignal(
            source=self.source,
            text=f"I am looking to buy a {query} urgently. Budget is flexible. Contact me at 0712345678. Located in Nairobi.",
            author="Mock User 1",
            contact={"phone": "0712345678", "whatsapp": "0712345678", "email": None},
            location="Nairobi",
            url="http://mock.test/lead1",
            timestamp=now.isoformat()
        )
        results.append(lead1.model_dump())
        
        # 2. Duplicate of Lead 1 (Exact URL) - Should be deduplicated by URL
        lead2 = ScraperSignal(
            source=self.source,
            text=f"I am looking to buy a {query} urgently. Budget is flexible. Contact me at 0712345678. Located in Nairobi.",
            author="Mock User 1",
            contact={"phone": "0712345678", "whatsapp": "0712345678", "email": None},
            location="Nairobi",
            url="http://mock.test/lead1", # Same URL
            timestamp=now.isoformat()
        )
        results.append(lead2.model_dump())
        
        # 3. Semantic Duplicate (Different URL, similar text) - Should be deduplicated by NLP
        lead3 = ScraperSignal(
            source=self.source,
            text=f"Looking for {query}. Cash ready. 0712345678. Nairobi.",
            author="Mock User 1",
            contact={"phone": "0712345678", "whatsapp": "0712345678", "email": None},
            location="Nairobi",
            url="http://mock.test/lead3_semantic_dup",
            timestamp=now.isoformat()
        )
        results.append(lead3.model_dump())
        
        # 4. Old Lead (Outside window) - Should be rejected by timestamp check (if strict)
        old_time = now - timedelta(hours=48)
        lead4 = ScraperSignal(
            source=self.source,
            text=f"Old post about {query}.",
            author="Old User",
            contact={"phone": None, "whatsapp": None, "email": None},
            location="Nairobi",
            url="http://mock.test/lead4_old",
            timestamp=old_time.isoformat()
        )
        results.append(lead4.model_dump())
        
        # 5. Irrelevant Lead - Should be rejected by intent classifier (low score)
        lead5 = ScraperSignal(
            source=self.source,
            text=f"I am selling a {query}. Best price in town!",
            author="Seller User",
            contact={"phone": "0700000000", "whatsapp": None, "email": None},
            location="Nairobi",
            url="http://mock.test/lead5_seller",
            timestamp=now.isoformat()
        )
        results.append(lead5.model_dump())

        return results
