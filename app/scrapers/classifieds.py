import logging
import re
from .base_scraper import BaseScraper 

logger = logging.getLogger(__name__)
  
class ClassifiedsScraper(BaseScraper): 
    source = "jiji_kenya" 
 
    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"JIJI_KENYA: Scraping for {query}")
        # Note: Backticks in URL removed for proper formatting
        url = f"https://jiji.co.ke/search?query={query}" 
        html = self.get_page_content(url, wait_selector="div.b-list-advert-base") 
        
        if not html:
            return []
 
        leads = [] 
        ads = re.findall(r'/item/\w+', html) 
 
        for ad in set(ads)[:10]: 
            link = f"https://jiji.co.ke{ad}"
            leads.append({ 
                "source": self.source, 
                "link": link,
                "text": f"Buyer or seller active for {query} on Jiji",
                "product": query, 
                "location": "Kenya", 
                "intent_text": f"Buyer or seller active for {query} on Jiji", 
                "contact_method": "Phone / Jiji Chat", 
                "confidence_score": 0.9 
            }) 
 
        return leads
