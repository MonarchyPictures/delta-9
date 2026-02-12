import logging
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from .base_scraper import BaseScraper, ScraperSignal
from ..core.pipeline_mode import PIPELINE_MODE, PIPELINE_CATEGORY

logger = logging.getLogger(__name__)

class BootstrapScraper(BaseScraper):
    source = "bootstrap_mock"

    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]:
        """
        Provides high-quality mock leads for testing in Bootstrap Mode.
        Only activates when PIPELINE_MODE is 'bootstrap'.
        """
        if PIPELINE_MODE != "bootstrap":
            logger.info("BootstrapScraper: Inactive (not in bootstrap mode)")
            return []

        logger.info(f"BootstrapScraper: Generating mock leads for '{query}'")
        
        # Extract the original object if possible from expanded query
        # Example expanded: "toyota (car OR vehicle...)" -> "toyota"
        display_query = query.split(' (')[0].replace('"', '') if ' (' in query else query
        if not display_query: display_query = "Toyota Axio"

        # Mock data for testing
        mock_raw_leads = [
            {
                "buyer_name": "Generic Buyer",
                "location_raw": "Global",
                "contact_phone": "+1234567890",
                "source": "Facebook",
                "url": f"https://facebook.com/groups/market-1/{display_query}",
                "posted_at": (datetime.now(timezone.utc) - timedelta(minutes=45)),
                "text": f"I need {display_query} urgently! Contact +1234567890"
            },
            {
                "buyer_name": "Market Researcher",
                "location_raw": "Global",
                "contact_phone": "+1987654321",
                "source": "Twitter",
                "url": f"https://twitter.com/search?q={display_query}-market",
                "posted_at": (datetime.now(timezone.utc) - timedelta(hours=2)),
                "text": f"Anyone selling {display_query}. +1987654321"
            },
            {
                "buyer_name": "Verified Market Signal",
                "location_raw": "Global",
                "contact_phone": "+1555000999",
                "source": "Classifieds",
                "url": f"https://classifieds.com/items/{display_query}-3",
                "posted_at": (datetime.now(timezone.utc) - timedelta(minutes=10)),
                "text": f"Serious buyer {display_query} +1555000999"
            }
        ]

        normalized_leads = []
        for raw in mock_raw_leads:
            signal = ScraperSignal(
                source=raw["source"],
                text=raw["text"],
                author=raw["buyer_name"],
                contact=self.extract_contact_info(f"{raw['text']} {raw['url']}"),
                location=raw["location_raw"],
                url=raw["url"],
                timestamp=raw["posted_at"].isoformat()
            )
            normalized_leads.append(signal.model_dump())

        return normalized_leads
