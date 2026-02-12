import logging
import os
import re
import requests
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal
from app.utils.resilience import retry_sync

logger = logging.getLogger(__name__)

class SerpApiScraper(BaseScraper):
    source = "serpapi"

    def __init__(self, api_key=None):
        super().__init__()
        self.api_key = api_key or os.getenv("SERPAPI_KEY", "79053e35aaae93199161e4eb92af7b834963548f94f454977647c5d5c8ec4d74")

    @retry_sync(retries=2, delay=2.0, backoff=2.0, exceptions=(requests.RequestException,))
    def _call_api(self, params):
        return requests.get("https://serpapi.com/search", params=params, timeout=20)

    def scrape(self, query: str, time_window_hours: int):
        logger.info(f"OUTBOUND CALL: SerpApi Scrape for {query} (Window: {time_window_hours}h)")
        
        tbs = "qdr:h"
        if time_window_hours > 1 and time_window_hours <= 24:
            tbs = f"qdr:h{time_window_hours}"
            if time_window_hours == 24: tbs = "qdr:d"
        elif time_window_hours > 24:
            days = time_window_hours // 24
            tbs = f"qdr:d{days}" if days > 1 else "qdr:d"
            if days >= 7: tbs = "qdr:w"
            
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "location": "Kenya",
            "google_domain": "google.co.ke",
            "gl": "ke",
            "hl": "en",
            "tbs": tbs,
            "num": 20
        }
        
        results = []
        try:
            response = self._call_api(params)
            if response.status_code == 200:
                data = response.json()
                
                # 1. Organic Results
                for r in data.get("organic_results", []):
                    if not isinstance(r, dict): continue
                    text_parts = [r.get('title', '')]
                    if r.get('snippet'): text_parts.append(r.get('snippet'))
                    date_str = r.get('date') or r.get('published_date', '')
                    if date_str: text_parts.append(f" [{date_str}]")
                    
                    full_text = " ".join(text_parts)
                        
                    snippet = r.get('snippet', '')
                    link = r.get('link', '')
                    
                    # 🎯 DUMB SCRAPER: Standardized Signal Output
                    signal = ScraperSignal(
                        source="serpapi_google",
                        text=full_text,
                        author="Google User",
                        contact=self.extract_contact_info(f"{snippet} {link}"),
                        location="Kenya",
                        url=link,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    results.append(signal.model_dump())
                
                # 2. Twitter Results
                for r in data.get("twitter_results", []):
                    if not isinstance(r, dict): continue
                    snippet = r.get('snippet', '')
                    link = r.get('link', '')
                    full_text = f"{snippet} [{r.get('published_date', '')}]"
                    
                    signal = ScraperSignal(
                        source="serpapi_twitter",
                        text=full_text,
                        author="Twitter User",
                        contact=self.extract_contact_info(f"{snippet} {link}"),
                        location="Kenya",
                        url=link,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    results.append(signal.model_dump())
                
                # 3. Local Results
                for r in data.get("local_results", []):
                    if not isinstance(r, dict): continue
                    link = r.get("link") or f"https://www.google.com/search?q={query}"
                    description = r.get('description', '')
                    address = r.get('address', '')
                    full_text = f"{r.get('title', 'No Title')} - {description} {address}"
                    
                    signal = ScraperSignal(
                        source="serpapi_local",
                        text=full_text,
                        author="Local Business",
                        contact=self.extract_contact_info(f"{full_text} {link}"),
                        location="Kenya",
                        url=link,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    results.append(signal.model_dump())
        except Exception as e:
            logger.error(f"SerpApi Scrape Error: {e}")
        
        return results
