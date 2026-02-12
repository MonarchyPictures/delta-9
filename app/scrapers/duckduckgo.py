import logging
import re
from datetime import datetime, timezone
from duckduckgo_search import DDGS
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

class DuckDuckGoScraper(BaseScraper):
    source = "duckduckgo"

    def scrape(self, query: str, time_window_hours: int):
        logger.info(f"OUTBOUND CALL: DuckDuckGo Scrape for {query} (Window: {time_window_hours}h)")
        results = []
        
        timelimit = 'd' if time_window_hours <= 24 else 'w'
        
        try:
            with DDGS() as ddgs:
                # region='ke-en' for Kenya specific results
                ddg_results = list(ddgs.text(query, region='ke-en', max_results=10, timelimit=timelimit))
                for r in ddg_results:
                    body = r.get('body', '')
                    full_text = f"{r['title']} {body}"
                    
                    # 🎯 DUMB SCRAPER: Standardized Signal Output
                    signal = ScraperSignal(
                        source=self.source,
                        text=full_text,
                        author="DuckDuckGo User",
                        contact=self.extract_contact_info(f"{body} {r['href']}"),
                        location="Kenya",
                        url=r['href'],
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    results.append(signal.model_dump())
        except Exception as e:
            logger.error(f"DuckDuckGo Scrape Error: {e}")
        
        return results
