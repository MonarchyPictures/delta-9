import logging
import re
from .base_scraper import BaseScraper 

logger = logging.getLogger(__name__)
  
class TwitterScraper(BaseScraper): 
    source = "twitter_x" 
 
    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"TWITTER_X: Scraping for {query} in Kenya")
        # Note: Backticks in URL removed for proper formatting
        url = f"https://twitter.com/search?q={query}%20near:Kenya&f=live" 
        html = self.get_page_content(url, wait_selector='article[data-testid="tweet"]') 
        
        if not html:
            return []
 
        leads = [] 
        # Using regex as requested, but we'll try to find individual tweets to generate links
        # This is a fallback to the user's requested logic
        tweets = re.findall(r'data-testid="tweetText"', html) 
 
        for _ in tweets[:8]: 
            leads.append({ 
                "source": self.source, 
                "link": f"https://twitter.com/search?q={query}", # Generic search link if individual link not parsed by regex
                "text": f"Tweet mentioning interest in {query}",
                "product": query, 
                "location": "Kenya", 
                "intent_text": f"Tweet mentioning interest in {query}", 
                "contact_method": "Twitter DM / Reply", 
                "confidence_score": 0.68  # borderline → bootstrap first 
            }) 
 
        return leads
