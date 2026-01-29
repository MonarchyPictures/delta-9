from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import abc
import logging

logger = logging.getLogger(__name__)

class BaseScraper(abc.ABC):
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

    @abc.abstractmethod
    def scrape(self, query):
        pass

    def get_page_content(self, url, wait_selector=None):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.user_agent)
            page = context.new_page()
            try:
                # Handle Google Consent if it appears
                page.goto(url, timeout=60000)
                if "google.com" in url:
                    try:
                        # Try to find and click "Accept all" or similar if it's a consent page
                        consent_btn = page.query_selector('button:has-text("Accept all"), button:has-text("I agree")')
                        if consent_btn:
                            consent_btn.click()
                            page.wait_for_load_state("networkidle")
                    except:
                        pass
                
                if wait_selector:
                    page.wait_for_selector(wait_selector, timeout=10000)
                return page.content()
            except Exception as e:
                print(f"Scrape Error at {url}: {e}")
                return None
            finally:
                browser.close()

class DuckDuckGoScraper(BaseScraper):
    def scrape(self, query):
        from ddgs import DDGS
        logger.info(f"OUTBOUND CALL: DuckDuckGo Scrape for {query}")
        results = []
        try:
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=10))
                for r in ddg_results:
                    results.append({
                        "link": r['href'],
                        "text": f"{r['title']} {r['body']}",
                        "source": "DuckDuckGo"
                    })
        except Exception as e:
            logger.error(f"DuckDuckGo Scrape Error: {e}")
        
        return results

class GoogleScraper(BaseScraper):
    def scrape(self, query):
        url = f"https://www.google.com/search?q={query}"
        # Use a more lenient wait or no wait if we just want the HTML
        content = self.get_page_content(url)
        if not content: return []
        
        soup = BeautifulSoup(content, 'html.parser')
        results = []
        # Google's layout changes frequently; try multiple selectors
        search_results = soup.select('div.g') or soup.select('div[data-ved]') or soup.select('div.MjjYud') or soup.select('div.tF2Cxc')
        logger.info(f"Google Scrape: Found {len(search_results)} raw results for {query}")
        
        for g in search_results:
            link_tag = g.select_one('a')
            title_tag = g.select_one('h3') or g.select_one('div[role="heading"]') or g.select_one('div.vv77sc')
            
            link = link_tag['href'] if link_tag and link_tag.has_attr('href') else ""
            title = title_tag.text if title_tag else ""
            
            if not title and link_tag:
                title = link_tag.get_text()
            
            if link.startswith('/url?q='):
                link = link.split('/url?q=')[1].split('&')[0]
                
            if link and title and not link.startswith('https://accounts.google.com') and not link.startswith('/search'):
                results.append({"link": link, "text": title, "source": "Google"})
        
        return results

class FacebookMarketplaceScraper(BaseScraper):
    def scrape(self, query):
        logger.info(f"OUTBOUND CALL: Facebook Marketplace Scrape for {query}")
        url = f"https://www.facebook.com/marketplace/search/?query={query}"
        content = self.get_page_content(url)
        if not content:
            raise RuntimeError(f"ERROR: No live data returned from Facebook Marketplace for {query}")
        
        soup = BeautifulSoup(content, 'html.parser')
        results = []
        # FB uses highly obfuscated classes. In a real scenario, we'd use more robust selectors or Graph API.
        # However, for PROD_STRICT, we must return real data or fail.
        # This implementation attempts to find any links that look like marketplace items.
        for a in soup.select('a[href*="/marketplace/item/"]'):
            link = "https://www.facebook.com" + a['href'] if a['href'].startswith('/') else a['href']
            text = a.get_text() or f"Marketplace Item for {query}"
            results.append({"link": link, "text": text, "source": "Facebook"})
        
        if not results:
            raise RuntimeError(f"ERROR: No live sources returned data from Facebook Marketplace.")
            
        return results

