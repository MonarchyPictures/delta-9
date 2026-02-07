from .base_scraper import BaseScraper 
import re 
import logging

logger = logging.getLogger(__name__)
 
class FacebookMarketplaceScraper(BaseScraper): 
    source = "facebook_marketplace" 
 
    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"FACEBOOK: Scraping for {query} in Kenya")
        url = f"https://www.facebook.com/marketplace/kenya/search?query={query}" 
        html = self.get_page_content(url, wait_selector="div[role='feed']") 
        
        if not html:
            return []
 
        leads = [] 
        items = re.findall(r'/marketplace/item/\d+', html) 
 
        for item in set(items)[:10]: 
            link = f"https://www.facebook.com{item}"
            leads.append({ 
                "source": self.source, 
                "link": link,
                "text": f"Marketplace buyer looking for {query}",
                "product": query, 
                "location": "Kenya", 
                "intent_text": f"Marketplace buyer looking for {query}", 
                "contact_method": "Facebook Messenger", 
                "confidence_score": 0.82  # marketplace intent is strong 
            }) 
 
        return leads
