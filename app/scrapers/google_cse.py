import logging
import os
import re
import requests
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal
from app.utils.resilience import retry_sync

logger = logging.getLogger(__name__)

class GoogleCSEScraper(BaseScraper):
    source = "google_cse"

    def __init__(self, api_keys=None, cx=None):
        super().__init__()
        # Support rotation: Provide a comma-separated list of keys in env or a list
        env_keys = os.getenv("GOOGLE_CSE_API_KEYS", "")
        if env_keys:
            self.api_keys = [k.strip() for k in env_keys.split(",")]
        else:
            self.api_keys = [
                os.getenv("GOOGLE_CSE_API_KEY", "AIzaSyBGQ7FpAkvzWgd_v7FjLm_1fGlI8z5aZNI"),
                # Add additional keys here for rotation
                "AIzaSyCl-PlaceholderKey2", 
                "AIzaSyDm-PlaceholderKey3"
            ]
        
        self.current_key_index = 0
        self.cx = cx or os.getenv("GOOGLE_CSE_ID", "b19c2ccb43df84d2e")

    @retry_sync(retries=2, delay=2.0, backoff=2.0, exceptions=(requests.RequestException,))
    def _call_api(self, params):
        return requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=20)

    def scrape(self, query: str, time_window_hours: int):
        # --- Advanced Query Builder ---
        intent_terms = [
            '"looking for"',
            '"need"',
            '"who sells"',
            '"anyone selling"',
            '"natafuta"',
            '"nahitaji"'
        ]
        
        geo_terms = [
            '"Nairobi"',
            '"Kenya"'
        ]
        
        # Make phone pattern optional in the query to increase recall
        expanded_query = f'({" OR ".join(intent_terms)}) {query} ({" OR ".join(geo_terms)})'
        
        logger.info(f"OUTBOUND CALL: Google CSE Scrape for {expanded_query} (Window: {time_window_hours}h)")
        
        date_restrict = "d1"
        if time_window_hours <= 24:
            date_restrict = "d1"
        elif time_window_hours <= 168:
            date_restrict = "w1"
        else:
            date_restrict = "m1"
            
        results = []
        max_retries = len(self.api_keys)
        
        for attempt in range(max_retries):
            api_key = self.api_keys[self.current_key_index]
            params = {
                "q": expanded_query,
                "key": api_key,
                "cx": self.cx,
                "dateRestrict": date_restrict,
                "cr": "countryKE",
                "num": 10
            }
            
            try:
                response = self._call_api(params)
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("items", []):
                        snippet = item.get('snippet', '')
                        link = item.get('link', '')
                        title = item.get('title', '')
                        full_text = f"{title} {snippet}"
                        
                        # Extract contact info from snippet + link as requested
                        contact = self.extract_contact_info(f"{snippet} {link}")
                        
                        signal = ScraperSignal(
                            source=self.source,
                            text=full_text,
                            author="Google User",
                            contact=contact,
                            location="Kenya",
                            url=link,
                            timestamp=datetime.now(timezone.utc).isoformat()
                        )
                        results.append(signal.model_dump())
                    logger.info(f"Google CSE Scrape: Found {len(results)} results for {query} using key index {self.current_key_index}")
                    return results # Success!
                    
                elif response.status_code in [429, 403, 400]:
                    # 429: Quota, 403: Forbidden/Quota, 400: Invalid Key (rotate to try others)
                    reason = "Quota Exceeded" if response.status_code == 429 else "Invalid/Forbidden Key"
                    logger.warning(f"Google CSE {reason} for key index {self.current_key_index}. Rotating...")
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    continue # Try next key
                    
                else:
                    logger.error(f"Google CSE Error: Status {response.status_code} - {response.text}")
                    break # Other errors don't necessarily warrant rotation
                    
            except Exception as e:
                logger.error(f"Google CSE Scrape Exception: {e}")
                break
                
        return results
