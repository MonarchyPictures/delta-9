import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

BUYER_KEYWORDS = [
    "looking for",
    "wanted",
    "want to buy",
    "buying",
    "need",
    "seeking"
]

SELLER_KEYWORDS = [
    "for sale",
    "selling",
    "available",
    "brand new",
    "offer"
]

class ClassifiedsScraper(BaseScraper):
    source = "jiji"

    async def scrape(self, query: str, time_window_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Adapter method to satisfy the system interface while using the async search logic.
        Returns a list of raw dictionaries that runner.py will normalize.
        """
        # We can map 'query' directly. 'time_window_hours' is ignored by the user's logic currently.
        try:
            results = await self.search(query)
            
            signals = []
            for res in results:
                # Convert user's simple dict to a structure close to ScraperSignal
                # runner.py expects: author, text/snippet, source, url, phone, location, timestamp
                
                # Combine title and price into text/snippet
                price_str = f" Price: {res['price']}" if res.get('price') else ""
                full_text = f"{res['title']}{price_str}"
                
                # Try to extract contact info if possible (BaseScraper has helper)
                # But we don't have the full text here, just title.
                # If we want phone numbers, we might need to visit the ad page (expensive)
                # or extract from title if present.
                contact = self.extract_contact_info(full_text)
                
                signal = {
                    "source": self.source,
                    "author": "Jiji User", # No specific author in listing
                    "text": full_text,
                    "url": res['url'],
                    "location": "Kenya", # Default scope
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "phone": contact.get("phone"),
                    # Add raw fields if needed
                    "price": res.get("price")
                }
                signals.append(signal)
            
            return signals
        except Exception as e:
            logger.error(f"Error in Jiji scrape: {e}")
            return []

    async def search(self, query: str, location: str = "Kenya"):
        transformed_query = self.transform_query(query)
        # Fixed URL string from user input (removed backticks)
        url = f"https://jiji.co.ke/search?query={transformed_query}"
        
        logger.info(f"Searching Jiji: {url}")

        results = []

        async with async_playwright() as p:
            # Launch options adjusted for headless env
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            
            # Use context for stealth
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            page = await context.new_page()
            
            try:
                await page.goto(url, timeout=60000)
                await page.wait_for_timeout(3000)

                # Scroll to load more (optional, but good practice)
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await page.wait_for_timeout(1000)

                ads = await page.query_selector_all(".b-list-ad")
                logger.info(f"Jiji found {len(ads)} ads")

                for ad in ads:
                    title_element = await ad.query_selector(".b-ad-title-inner") # Correct selector
                    if not title_element:
                        # Fallback
                        title_element = await ad.query_selector("h3") or await ad.query_selector(".qa-ad-title")
                        
                    if not title_element:
                        continue

                    title = (await title_element.inner_text()).lower()

                    if not self.is_buyer(title):
                        logger.info(f"Jiji Filtered (Seller/Neutral): {title}")
                        continue
                    
                    logger.info(f"Jiji Found Buyer: {title}")

                    price_element = await ad.query_selector(".qa-advert-price")
                    link_element = await ad.query_selector("a")

                    price = await price_element.inner_text() if price_element else None
                    link = await link_element.get_attribute("href") if link_element else None
                    
                    # Ensure absolute URL
                    if link and not link.startswith("http"):
                        link = f"https://jiji.co.ke{link}"

                    snippet = f"{title} {price or ''}"

                    results.append({
                        "buyer_name": "Jiji User",
                        "title": title,
                        "price": price or "",
                        "location": location,
                        "phone": None,
                        "source": "jiji",
                        "intent_score": 0.85, # Pre-verified by is_buyer check
                        "url": link,
                        "snippet": snippet
                    })
            except Exception as e:
                logger.error(f"Jiji search failed: {e}")
            finally:
                await browser.close()

        return results

    def transform_query(self, query):
        if any(k in query.lower() for k in BUYER_KEYWORDS):
            return query
        return f"looking for {query}"

    def is_buyer(self, title):
        # Strict demand-only logic - RESTORED for user "why I am seeing sellers" request
        
        # If explicitly contains STRONG buyer keywords, always accept (even if "brand new" is present)
        # e.g. "Looking for brand new laptop" -> Accept
        if any(b in title for b in BUYER_KEYWORDS):
            return True

        # Jiji is primarily a SELLER platform. 
        # A neutral title like "iPhone 13" is 99% a seller.
        # We MUST require explicit buyer keywords to avoid flooding with seller ads.
        
        # Exception: If title starts with "wanted" or "looking", we catch it above.
        # If not caught above, and it's just "iPhone 13", we REJECT it.
        return False
