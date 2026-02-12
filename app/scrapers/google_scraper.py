import logging
import re
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

class GoogleScraper(BaseScraper): 
    source = "google" 

    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"GOOGLE: Scraping for {query}")
        # Build a simpler query for better recall on Google
        # We'll use the core query terms but relax the mandatory quotes slightly
        clean_query = query.replace('"', '')
        search_query = f'{clean_query} (site:facebook.com OR site:jiji.co.ke OR site:pigiame.co.ke)'
        
        url = f"https://www.google.com/search?q={search_query}" 
        
        html = self.get_page_content(url, wait_selector="div#search")
        
        if not html:
            logger.warning("GOOGLE: No HTML content received")
            return []
 
        results = [] 
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Google search results are usually in 'div.g' or 'div.MjjYud'
        search_results = soup.select('div.g') or soup.select('div.MjjYud')
        logger.info(f"GOOGLE: Found {len(search_results)} result blocks")
        
        if len(search_results) == 0:
            # Try a broader fallback selector
            search_results = soup.select('div[data-hveid]')
            logger.info(f"GOOGLE: Fallback found {len(search_results)} potential result blocks")

        for res in search_results:
            link_tag = res.select_one('a')
            # Multiple possible snippet selectors
            snippet_tag = res.select_one('div.VwiC3b') or res.select_one('div.kb0u9b') or res.select_one('span.st') or res.select_one('.yD9P9') or res.select_one('.MUF3bd')
            
            if not link_tag or not snippet_tag:
                continue
                
            link = link_tag.get('href')
            snippet = snippet_tag.get_text()
            
            if not link or not snippet or not link.startswith('http'):
                continue

            if any(x in link for x in ["google.com", "gstatic.com", "youtube.com"]):
                continue

            logger.info(f"GOOGLE: Found potential lead at {link}")
            
            # 🎯 DUMB SCRAPER: Standardized Signal Output
            signal = ScraperSignal(
                source=self.source,
                text=snippet,
                author="Google Search Result",
                contact=self.extract_contact_info(f"{snippet}"),
                location="Kenya",
                url=link,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            results.append(signal.model_dump())
 
        return results[:10]
