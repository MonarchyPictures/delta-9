from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import abc

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
                page.goto(url, timeout=60000)
                if wait_selector:
                    page.wait_for_selector(wait_selector, timeout=10000)
                return page.content()
            except Exception as e:
                print(f"Scrape Error at {url}: {e}")
                return None
            finally:
                browser.close()

class GoogleScraper(BaseScraper):
    def scrape(self, query):
        url = f"https://www.google.com/search?q={query}"
        # Use a more lenient wait or no wait if we just want the HTML
        content = self.get_page_content(url)
        if not content: return []
        
        soup = BeautifulSoup(content, 'html.parser')
        results = []
        # Google's layout changes frequently; try multiple selectors
        search_results = soup.select('div.g') or soup.select('div[data-ved]')
        
        for g in search_results:
            link_tag = g.select_one('a')
            title_tag = g.select_one('h3')
            
            link = link_tag['href'] if link_tag and link_tag.has_attr('href') else ""
            title = title_tag.text if title_tag else ""
            
            if link.startswith('/url?q='):
                link = link.split('/url?q=')[1].split('&')[0]
                
            if link and title and not link.startswith('https://accounts.google.com'):
                results.append({"link": link, "text": title, "source": "Google"})
        
        return results

class FacebookMarketplaceScraper(BaseScraper):
    def scrape(self, query):
        print(f"Relentless FB Marketplace Scrape: {query}")
        # FB Marketplace usually requires geographic codes or city names in URL
        url = f"https://www.facebook.com/marketplace/search/?query={query}"
        content = self.get_page_content(url)
        if not content: return []
        
        soup = BeautifulSoup(content, 'html.parser')
        results = []
        # FB uses highly obfuscated classes, usually better to use Playwright selectors
        # For this example, we'll use a placeholder for the complex extraction logic
        return [{"link": url, "text": f"FB Marketplace Result for {query}", "source": "Facebook"}]

