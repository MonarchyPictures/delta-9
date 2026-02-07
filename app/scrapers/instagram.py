import logging
from .base_scraper import BaseScraper
from ..utils.playwright_helpers import get_page_content
from bs4 import BeautifulSoup
import urllib.parse

logger = logging.getLogger(__name__)

class InstagramScraper(BaseScraper):
    def scrape(self, query, time_window_hours=2):
        logger.info(f"INSTAGRAM: Scraping for {query} in Kenya")
        
        # Instagram search usually works best via hashtags or specific keywords
        encoded_query = urllib.parse.quote(f"{query} Kenya")
        url = f"https://www.instagram.com/explore/tags/{encoded_query.replace('%20', '')}/"
        
        content = get_page_content(url, wait_selector='article')
        if not content:
            # Fallback to keyword search
            url = f"https://www.instagram.com/reels/keywords/?q={encoded_query}"
            content = get_page_content(url, wait_selector='div._ac7v')
            
        if not content:
            return []
            
        soup = BeautifulSoup(content, 'html.parser')
        results = []
        
        # Instagram items
        items = soup.select('a[href*="/p/"], a[href*="/reels/"]')
        for item in items[:10]:
            try:
                link = "https://www.instagram.com" + item['href']
                # Instagram doesn't show much text in list view, might need individual post fetching
                # but we'll capture what's available (alt text often contains caption)
                img = item.find('img')
                text = img.get('alt', '') if img else f"Instagram post about {query}"
                
                results.append({
                    "intent_text": text,
                    "link": link,
                    "source": "Instagram",
                    "product": query,
                    "location": "Kenya",
                    "contact_method": f"Instagram DM: {link}",
                    "confidence_score": 0.7
                })
            except Exception as e:
                logger.error(f"Error parsing Instagram item: {e}")
                
        return results
