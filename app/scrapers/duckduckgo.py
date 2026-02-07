import logging
from duckduckgo_search import DDGS
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class DuckDuckGoScraper(BaseScraper):
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
                    results.append({
                        "intent_text": f"{r['title']} {body}",
                        "link": r['href'],
                        "source": "DuckDuckGo",
                        "product": query,
                        "location": "Kenya",
                        "contact_method": f"Web: {r['href']}",
                        "confidence_score": 0.6
                    })
        except Exception as e:
            logger.error(f"DuckDuckGo Scrape Error: {e}")
        
        return results
