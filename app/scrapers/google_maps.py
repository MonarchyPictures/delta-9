import logging
import re
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

class GoogleMapsScraper(BaseScraper): 
    source = "google_maps" 

    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"GOOGLE_MAPS: Scraping for {query}")
        
        # FORCE KENYA LOCATION
        if "kenya" not in query.lower() and "nairobi" not in query.lower():
             search_query = f"{query} Kenya"
        else:
             search_query = query
             
        loc_name = "Kenya"

        search = f"{search_query} site:google.com/maps" 
        url = f"https://www.google.com/search?q={search}" 
        html = self.get_page_content(url)  
        
        if not html:
            return []
 
        signals = [] 
        businesses = re.findall(r'aria-label="([^"]+)"', html) 
 
        for biz in businesses[:6]: 
            snippet = f"Verified business: {biz}"
            
            # 🎯 DUMB SCRAPER: Standardized Signal Output
            signal = ScraperSignal(
                source=self.source,
                text=snippet,
                author=biz,
                contact=self.extract_contact_info(f"{snippet} {url}"),
                location=loc_name,
                url=url,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            signals.append(signal.model_dump())
 
        return signals
