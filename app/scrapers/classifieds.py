import logging
import re
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

class ClassifiedsScraper(BaseScraper): 
    source = "classifieds" 

    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"CLASSIFIEDS: Scraping for {query}")
        # Jiji specific search
        url = f"https://jiji.co.ke/search?query={query}"
        
        html = self.get_page_content(url, wait_selector=".b-list-advert-base") 
        
        if not html:
            logger.warning("CLASSIFIEDS: No HTML content received")
            return []
 
        results = [] 
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Jiji ads usually have this class
        ads = soup.select('.b-list-advert-base')
        logger.info(f"CLASSIFIEDS: Found {len(ads)} ads")
        
        for ad in ads:
            # Check if the ad element itself is the link
            if ad.name == 'a':
                link_tag = ad
            else:
                # Try specific selector first, then fallback to any link
                link_tag = ad.select_one('a.b-list-advert-base__item-text-title') or ad.select_one('a')
            
            snippet_tag = ad.select_one('.b-list-advert-base__description-text') or ad.select_one('.qa-advert-description')
            price_tag = ad.select_one('.qa-advert-price')
            
            if not link_tag:
                continue
            
            href = link_tag.get('href')
            if not href:
                continue

            # NEW: Clean URL to remove tracking params (Fixes idempotency)
            if "?" in href:
                href = href.split("?")[0]

            link = href if href.startswith('http') else f"https://jiji.co.ke{href}"
            title = link_tag.get_text(strip=True)
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            price = price_tag.get_text(strip=True) if price_tag else ""
            
            # Jiji often puts price in title or nearby.
            # We want to make sure the text feels like a "post"
            full_text = f"{title}. {snippet}. Price: {price}"
            
            # Helper to clean Jiji text
            if "KSh" in title and "KSh" in price:
                # Deduplicate price if it's in title
                full_text = f"{title}. {snippet}"
            
            # Ensure we capture "Job" or "Hiring" context if present in URL or category
            if "job" in link or "work" in link:
                 full_text += " [Job/Service Listing]"
            
            # Check if it looks like a buyer (Jiji has "Wanted" category or users post in titles)
            # For now, we emit all and let the intent scorer decide
            
            # 🎯 DUMB SCRAPER: Standardized Signal Output
            signal = ScraperSignal(
                source=self.source,
                text=full_text,
                author="Jiji User",
                contact=self.extract_contact_info(full_text),
                location="Kenya",
                url=link,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            results.append(signal.model_dump())
 
        return results[:10]
