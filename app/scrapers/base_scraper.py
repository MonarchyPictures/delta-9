import logging
import random
import time
from abc import ABC, abstractmethod 
from playwright.sync_api import sync_playwright 

logger = logging.getLogger(__name__)

USER_AGENTS = [ 
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", 
    "Mozilla/5.0 (X11; Linux x86_64)", 
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" 
] 

class BaseScraper(ABC): 
    def __init__(self, user_agent=None): 
        self.user_agent = user_agent or random.choice(USER_AGENTS)

    @abstractmethod 
    def scrape(self, query: str, time_window_hours: int): 
        """Must return list of leads with dicts: 
        { 
            'source': str, 
            'product': str, 
            'location': str, 
            'intent_text': str, 
            'contact_method': str, 
            'confidence_score': float 
        } 
        """ 
        pass 

    def get_page_content(self, url, wait_selector=None): 
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
                page.goto(url, timeout=60000) 
        
                for text in ["Accept", "Accept all", "I agree"]: 
                    try: 
                        page.click(f"text={text}", timeout=3000) 
                        break 
                    except: 
                        pass 
        
                if wait_selector: 
                    try:
                        page.wait_for_selector(wait_selector, timeout=15000) 
                    except Exception as e:
                        logger.warning(f"PLAYWRIGHT: Wait selector {wait_selector} failed: {e}")
        
                time.sleep(random.uniform(1.5, 3.0)) 
        
                html = page.content() 
                browser.close() 
                return html
        except Exception as e:
            logger.error(f"PLAYWRIGHT death at {url}: {str(e)}")
            return ""
