import logging
import os
import requests
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class GoogleCSEScraper(BaseScraper):
    def __init__(self, api_key=None, cx=None):
        super().__init__()
        self.api_key = api_key or os.getenv("GOOGLE_CSE_API_KEY", "AIzaSyBGQ7FpAkvzWgd_v7FjLm_1fGlI8z5aZNI")
        self.cx = cx or os.getenv("GOOGLE_CSE_ID", "b19c2ccb43df84d2e")

    def scrape(self, query: str, time_window_hours: int):
        logger.info(f"OUTBOUND CALL: Google CSE Scrape for {query} (Window: {time_window_hours}h)")
        
        date_restrict = "d1"
        if time_window_hours <= 24:
            date_restrict = "d1"
        elif time_window_hours <= 168:
            date_restrict = "w1"
        else:
            date_restrict = "m1"
            
        params = {
            "q": query,
            "key": self.api_key,
            "cx": self.cx,
            "dateRestrict": date_restrict,
            "cr": "countryKE",
            "num": 10
        }
        
        results = []
        try:
            response = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=20)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", []):
                    results.append({
                        "intent_text": f"{item.get('title', '')} {item.get('snippet', '')}",
                        "link": item.get("link", ""),
                        "source": "Google CSE",
                        "product": query,
                        "location": "Kenya",
                        "contact_method": f"Web: {item.get('link', '')}",
                        "confidence_score": 0.8
                    })
                logger.info(f"Google CSE Scrape: Found {len(results)} results for {query}")
            else:
                logger.error(f"Google CSE Error: Status {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Google CSE Scrape Exception: {e}")
            
        return results
