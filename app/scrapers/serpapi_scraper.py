import logging
import os
import requests
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class SerpApiScraper(BaseScraper):
    def __init__(self, api_key=None):
        super().__init__()
        self.api_key = api_key or os.getenv("SERPAPI_KEY", "79053e35aaae93199161e4eb92af7b834963548f94f454977647c5d5c8ec4d74")

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
            response = requests.get("https://serpapi.com/search", params=params, timeout=20)
            if response.status_code == 200:
                data = response.json()
                
                # 1. Organic Results
                for r in data.get("organic_results", []):
                    if not isinstance(r, dict): continue
                    text_parts = [r.get('title', '')]
                    if r.get('snippet'): text_parts.append(r.get('snippet'))
                    date_str = r.get('date') or r.get('published_date', '')
                    if date_str: text_parts.append(f" [{date_str}]")
                        
                    results.append({
                        "intent_text": " ".join(text_parts),
                        "link": r.get("link", ""),
                        "source": "SerpApi (Google)",
                        "product": query,
                        "location": "Kenya",
                        "contact_method": f"Web: {r.get('link', '')}",
                        "confidence_score": 0.85
                    })
                
                # 2. Twitter Results
                for r in data.get("twitter_results", []):
                    if not isinstance(r, dict): continue
                    results.append({
                        "intent_text": f"{r.get('snippet', '')} [{r.get('published_date', '')}]",
                        "link": r.get("link", ""),
                        "source": "SerpApi (Twitter)",
                        "product": query,
                        "location": "Kenya",
                        "contact_method": f"Twitter: {r.get('link', '')}",
                        "confidence_score": 0.8
                    })
                
                # 3. Local Results
                for r in data.get("local_results", []):
                    if not isinstance(r, dict): continue
                    link = r.get("link") or f"https://www.google.com/search?q={query}"
                    results.append({
                        "intent_text": f"{r.get('title', 'No Title')} - {r.get('description', '')} {r.get('address', '')}",
                        "link": link,
                        "source": "SerpApi (Local)",
                        "product": query,
                        "location": r.get('address', 'Kenya'),
                        "contact_method": f"Local: {link}",
                        "confidence_score": 0.6
                    })
                    
                logger.info(f"SerpApi Scrape: Found {len(results)} results for {query}")
            else:
                logger.error(f"SerpApi Error: Status {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"SerpApi Scrape Exception: {e}")
            
        return results
