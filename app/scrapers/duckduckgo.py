import logging
import re
from datetime import datetime, timezone
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

class DuckDuckGoScraper(BaseScraper):
    source = "duckduckgo"

    def scrape(self, query: str, time_window_hours: int):
        logger.info(f"OUTBOUND CALL: DuckDuckGo Scrape for {query} (Window: {time_window_hours}h)")
        results = []
        
        # Remove timelimit to get more results for testing/production
        # timelimit = 'd' if time_window_hours <= 24 else 'w'
        timelimit = None
        
        try:
            with DDGS() as ddgs:
                # region='ke-en' for Kenya
                # Using default backend (auto-selects best available: api/html/etc)
                logger.info("DDG: Scraping with default backend...")
                ddg_results = list(ddgs.text(query, max_results=25, region='ke-en'))
                
                logger.info(f"DuckDuckGo found {len(ddg_results)} raw results")
                
                for r in ddg_results:
                    body = r.get('body', '')
                    title = r.get('title', '')
                    link = r.get('href', '')
                    full_text = f"{title} {body}"
                    
                    logger.debug(f"DDG Result: {title} | {link}")

                    # 🎯 DUMB SCRAPER: Standardized Signal Output
                    signal = ScraperSignal(
                        source=self.source,
                        text=full_text,
                        author="DuckDuckGo User",
                        contact=self.extract_contact_info(f"{body} {link}"),
                        location="Kenya",
                        url=link,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    results.append(signal.model_dump())
        except Exception as e:
            logger.error(f"DuckDuckGo Scrape Error: {e}", exc_info=True)
        
        return results
