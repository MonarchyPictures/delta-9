import logging
import re
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

class FacebookMarketplaceScraper(BaseScraper): 
    source = "facebook" 

    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"FACEBOOK: Scraping for {query}")
        
        # FORCE KENYA LOCATION
        # The user explicitly requested to lock to Kenya.
        # We use 'nairobi' as the base location for Facebook Marketplace as it is the primary hub.
        # 'kenya' path often redirects to global/IP-based if not specific.
        search_query = f"{query} Kenya"
        url = f"https://www.facebook.com/marketplace/nairobi/search?query={search_query}"
        location_name = "Kenya"
        
        html = self.get_page_content(url, wait_selector="div[role='feed']") 
        # html = None # Placeholder
        
        if not html:
            return []
 
        results = [] 
        # items = re.findall(r'/marketplace/item/\d+', html) 
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Facebook marketplace items are usually in a feed
        # Selectors change frequently, so we use a broad approach + regex for links
        links = soup.find_all('a', href=re.compile(r'/marketplace/item/\d+'))
        
        processed_links = set()

        for link_tag in links[:10]: 
            href = link_tag.get('href')
            if not href or href in processed_links:
                continue
            
            processed_links.add(href)
            link = f"https://www.facebook.com{href}"
            
            # Try to extract text from the link tag or parent
            text = link_tag.get_text(strip=True)
            
            # If text is empty, look for parent text (often the link wraps an image and text is sibling or parent)
            if not text:
                parent = link_tag.find_parent('div')
                if parent:
                    text = parent.get_text(strip=True)
            
            if not text:
                continue

            # 🎯 DUMB SCRAPER: Standardized Signal Output
            signal = ScraperSignal(
                source=self.source,
                text=text,
                author="Facebook User",
                contact=self.extract_contact_info(f"{text} {link}"),
                location=location_name,
                url=link,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            results.append(signal.model_dump())
 
        return results
