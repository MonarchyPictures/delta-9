import logging
import random
from abc import ABC, abstractmethod 
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from playwright.sync_api import sync_playwright 

logger = logging.getLogger(__name__)

USER_AGENTS = [ 
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", 
    "Mozilla/5.0 (X11; Linux x86_64)", 
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" 
] 

class ScraperSignal(BaseModel):
    """
    Standard Signal Object returned by all scrapers.
    Scrapers are 'dumb' and only emit raw data.
    """
    source: str
    text: str
    author: Optional[str] = None
    contact: Dict[str, Optional[str]] = Field(default_factory=lambda: {
        "phone": None,
        "whatsapp": None,
        "email": None
    })
    location: str
    url: str
    timestamp: str  # ISO Format

class BaseScraper(ABC): 
    def __init__(self, user_agent=None): 
        self.user_agent = user_agent or random.choice(USER_AGENTS)
        from .metrics import SCRAPER_METRICS
        self.stats = SCRAPER_METRICS.get(self.__class__.__name__, {})

    @property
    def priority_score(self) -> float:
        """Dynamic priority score for sorting."""
        from .metrics import get_scraper_performance_score
        return get_scraper_performance_score(self.__class__.__name__)

    @property
    def auto_disabled(self) -> bool:
        """Check if scraper has been auto-disabled by the performance engine."""
        from .metrics import SCRAPER_METRICS
        return SCRAPER_METRICS.get(self.__class__.__name__, {}).get("auto_disabled", False)

    @abstractmethod 
    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]: 
        """
        Must return a list of raw signals matching the ScraperSignal model:
        { 
            "source": str, 
            "text": str, 
            "author": str | None, 
            "contact": {"phone": str|None, "whatsapp": str|None, "email": str|None},
            "location": str, 
            "url": str,
            "timestamp": "ISO"
        }
        """ 
        pass 

    async def search(self, query: str, location: str) -> List[Dict[str, Any]]:
        """
        New Standard Interface for Search Service.
        Wraps the legacy 'scrape' method and ensures async execution.
        """
        import asyncio
        from datetime import datetime, timezone

        # Check if scrape is async
        if asyncio.iscoroutinefunction(self.scrape):
            # For async scrapers, we can pass query/location directly if they support it 
            # (like Jiji which overrides search)
            # But BaseScraper implementation is a fallback for legacy scrapers
            # Legacy scrapers use 'scrape(query, time_window)'
            full_query = f"{query} {location}"
            signals = await self.scrape(full_query, time_window_hours=24)
        else:
            full_query = f"{query} {location}"
            signals = await asyncio.to_thread(self.scrape, full_query, time_window_hours=24)
            
        results = []
        for s in signals:
            results.append({
                "title": s.get("title") or s.get("text") or s.get("snippet") or "Unknown Result",
                "url": s.get("url"),
                "source": s.get("source"),
                "snippet": s.get("text") or s.get("snippet"),
                "location": s.get("location", location),
                "timestamp": s.get("timestamp", datetime.now(timezone.utc).isoformat())
            })
        return results 

    def get_page_content(self, url, wait_selector=None): 
        print("Navigating to:", url)
        logger.info(f"PLAYWRIGHT: Fetching {url} with hardened stealth")
        try:
            with sync_playwright() as p: 
                browser = p.chromium.launch( 
                    headless=True, 
                    args=[ 
                        "--disable-blink-features=AutomationControlled", 
                        "--no-sandbox", 
                        "--disable-dev-shm-usage" 
                    ] 
                ) 
        
                context = browser.new_context( 
                    user_agent=random.choice(USER_AGENTS), 
                    locale="en-KE", 
                    timezone_id="Africa/Nairobi" 
                ) 
        
                page = context.new_page() 
                
                # Retry mechanism for navigation
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        page.goto(url, timeout=45000)
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            logger.error(f"Failed to navigate to {url} after {max_retries} attempts: {e}")
                            raise e
                        logger.warning(f"Navigation to {url} failed (attempt {attempt+1}/{max_retries}), retrying in 2s...")
                        import time
                        time.sleep(2 * (attempt + 1)) # Exponential backoff
        
                for text in ["Accept", "Accept all", "I agree"]: 
                    try: 
                        page.click(f"text={text}", timeout=2000) 
                        break 
                    except: 
                        pass 
        
                # 📜 Scroll to Load More Content (Handles lazy-loading)
                print(f"Scrolling to load content for {url}...")
                for i in range(2):
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    page.wait_for_timeout(2000) # wait for content to load
        
                if wait_selector: 
                    try:
                        # Primary selector 
                        page.wait_for_selector(wait_selector, timeout=5000) 
                    except Exception as e:
                        print(f"Primary selector '{wait_selector}' failed, trying fallback...")
                        try:
                            # Fallback for dynamic layout
                            page.wait_for_selector("[role='main'], [role='presentation'], .main-content, #main", timeout=5000)
                        except Exception as fe:
                            # If all selectors fail, just log and continue with whatever we have
                            html_len = len(page.content())
                            print(f"PLAYWRIGHT: All selectors failed, but got {html_len} chars of HTML")
                            logger.warning(f"PLAYWRIGHT: Both primary and fallback selectors failed at {url}, HTML len: {html_len}")
        
                # Use Playwright's native wait instead of blocking time.sleep
                page.wait_for_timeout(random.uniform(1500, 3000))
        
                html = page.content() 
                browser.close() 
                return html
        except Exception as e:
            print("PLAYWRIGHT ERROR:", str(e))
            logger.error(f"PLAYWRIGHT death at {url}: {str(e)}")
            return ""

    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extracts phone numbers and emails from text.
        """
        import re
        contact = {"phone": None, "whatsapp": None, "email": None}
        
        # Phone regex as requested: +254... or 07...
        phone_regex = r'(\+254\d{9}|07\d{8})'
        phones = re.findall(phone_regex, text)
        
        if phones:
            contact["phone"] = phones[0]
            # Default whatsapp to phone if found
            contact["whatsapp"] = f"https://wa.me/{phones[0].replace('+', '').replace(' ', '')}"
        
        # Fallback to email if no phone or just extra extraction
        email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_regex, text)
        if emails:
            contact["email"] = emails[0]
            
        return contact
