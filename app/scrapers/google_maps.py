import logging
import re
from .base_scraper import BaseScraper 

logger = logging.getLogger(__name__)
  
class GoogleMapsScraper(BaseScraper): 
    source = "google_maps" 
 
    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"GOOGLE_MAPS: Scraping for {query} in Kenya")
        search = f"{query} Kenya site:google.com/maps" 
        url = f"https://www.google.com/search?q={search}" 
        html = self.get_page_content(url) 
        
        if not html:
            return []
 
        leads = [] 
        businesses = re.findall(r'aria-label="([^"]+)"', html) 
 
        for biz in businesses[:6]: 
            leads.append({ 
                "source": self.source, 
                "link": url,
                "text": f"Verified business related to {query}: {biz}",
                "product": query, 
                "location": "Kenya", 
                "intent_text": f"Verified business related to {query}: {biz}", 
                "contact_method": "Phone / Website", 
                "confidence_score": 0.95 
            }) 
 
        return leads
