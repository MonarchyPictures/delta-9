import logging
import re
from .base_scraper import BaseScraper 

logger = logging.getLogger(__name__)

class RedditScraper(BaseScraper): 
    source = "reddit" 

    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"REDDIT: Scraping for {query} in Kenya subreddits")
        # Search reddit for the query in Kenya-specific subreddits
        url = f"https://www.reddit.com/search/?q={query}%20kenya&t=day" 
        html = self.get_page_content(url, wait_selector='shreddit-post') 
        
        if not html:
            return []
 
        leads = [] 
        # Extract post titles and links
        posts = re.findall(r'href="(/r/[^/]+/comments/[^/]+/[^/]+/)"', html)
        
        for post_url in set(posts)[:5]: 
            full_url = f"https://www.reddit.com{post_url}"
            leads.append({ 
                "source": self.source, 
                "link": full_url,
                "text": f"Reddit discussion about {query} in Kenya",
                "product": query, 
                "location": "Kenya", 
                "intent_text": f"Reddit discussion about {query} in Kenya", 
                "contact_method": "Reddit DM / Comment", 
                "confidence_score": 0.7
            }) 
 
        return leads
