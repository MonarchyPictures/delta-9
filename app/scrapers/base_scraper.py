from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import abc
import logging
import os
import requests
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

class BaseScraper(abc.ABC):
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

    @abc.abstractmethod
    def scrape(self, query, time_window_hours=2):
        pass

    def get_page_content(self, url, wait_selector=None):
        logger.info(f"PLAYWRIGHT: Fetching {url}")
        try:
            with sync_playwright() as p:
                # Use a shorter launch timeout and specify chromium
                browser = p.chromium.launch(headless=True, timeout=30000)
                context = browser.new_context(
                    user_agent=self.user_agent,
                    viewport={'width': 1280, 'height': 800}
                )
                page = context.new_page()
                
                # Set default timeout for all actions
                page.set_default_timeout(30000)
                
                try:
                    # Use "domcontentloaded" instead of "networkidle" for speed
                    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    
                    if response and response.status == 429:
                        logger.warning(f"PLAYWRIGHT: Rate limited (429) at {url}")
                        return None

                    if "google.com" in url:
                        try:
                            # Faster check for consent
                            consent_btn = page.query_selector('button:has-text("Accept all"), button:has-text("I agree"), button:has-text("Accept everything")')
                            if consent_btn:
                                consent_btn.click()
                                # Don't wait too long after click
                                page.wait_for_load_state("domcontentloaded", timeout=5000)
                        except:
                            pass
                    
                    if wait_selector:
                        try:
                            page.wait_for_selector(wait_selector, timeout=10000)
                        except:
                            logger.warning(f"PLAYWRIGHT: Timeout waiting for selector {wait_selector}")
                    
                    return page.content()
                except Exception as e:
                    logger.error(f"PLAYWRIGHT: Page operation error at {url}: {str(e)}")
                    return None
                finally:
                    browser.close()
        except Exception as e:
            logger.error(f"PLAYWRIGHT: Browser launch/context error: {str(e)}")
            return None

class SerpApiScraper(BaseScraper):
    def __init__(self, api_key=None):
        super().__init__()
        # Priority 1: Passed key, Priority 2: Env Var, Priority 3: Hardcoded fallback
        self.api_key = api_key or os.getenv("SERPAPI_KEY", "79053e35aaae93199161e4eb92af7b834963548f94f454977647c5d5c8ec4d74")

    def scrape(self, query, time_window_hours=2):
        logger.info(f"OUTBOUND CALL: SerpApi Scrape for {query} (Window: {time_window_hours}h)")
        
        # Map hours to SerpApi tbs format
        tbs = "qdr:h" # Default to last hour
        if time_window_hours > 1 and time_window_hours <= 24:
            tbs = f"qdr:h{time_window_hours}"
            if time_window_hours == 24: tbs = "qdr:d"
        elif time_window_hours > 24:
            days = time_window_hours // 24
            tbs = f"qdr:d{days}" if days > 1 else "qdr:d"
            if days >= 7: tbs = "qdr:w"
            
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "location": "Kenya",
            "google_domain": "google.co.ke",
            "gl": "ke",
            "hl": "en",
            "tbs": tbs,
            "num": 20 # Get more results to increase chance of finding verified signals
        }
        
        results = []
        try:
            response = requests.get("https://serpapi.com/search", params=params, timeout=20)
            if response.status_code == 200:
                data = response.json()
                
                # 1. Process Organic Results
                for r in data.get("organic_results", []):
                    if not isinstance(r, dict): continue
                    # Combine title, snippet and rich snippet info for better verification
                    text_parts = [r.get('title', '')]
                    if r.get('snippet'): text_parts.append(r.get('snippet'))
                    
                    # SerpApi often has 'date' or 'published_date'
                    date_str = r.get('date') or r.get('published_date', '')
                    if date_str:
                        text_parts.append(f" [{date_str}]")
                        
                    results.append({
                        "link": r.get("link"),
                        "text": " ".join(text_parts),
                        "source": "SerpApi (Google)",
                        "date": date_str
                    })
                
                # 2. Process Twitter Results
                for r in data.get("twitter_results", []):
                    if not isinstance(r, dict): continue
                    results.append({
                        "link": r.get("link"),
                        "text": f"{r.get('snippet', '')} [{r.get('published_date', '')}]",
                        "source": "SerpApi (Twitter)",
                        "date": r.get('published_date')
                    })
                
                # 3. Process Local Results (can be good for Kenya market)
                for r in data.get("local_results", []):
                    if not isinstance(r, dict): continue
                    results.append({
                        "link": r.get("link") or f"https://www.google.com/search?q={query}",
                        "text": f"{r.get('title', 'No Title')} - {r.get('description', '')} {r.get('address', '')}",
                        "source": "SerpApi (Local)"
                    })
                    
                logger.info(f"SerpApi Scrape: Found {len(results)} results for {query}")
            else:
                logger.error(f"SerpApi Error: Status {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"SerpApi Scrape Exception: {e}")
            
        return results

class DuckDuckGoScraper(BaseScraper):
    def scrape(self, query, time_window_hours=2):
        logger.info(f"OUTBOUND CALL: DuckDuckGo Scrape for {query} (Window: {time_window_hours}h)")
        results = []
        
        # DDG time filters: 'd' (day), 'w' (week), 'm' (month)
        timelimit = 'd' if time_window_hours <= 24 else 'w'
        
        try:
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=10, timelimit=timelimit))
                for r in ddg_results:
                    # Capture snippet text if available in DDGS
                    body = r.get('body', '')
                    results.append({
                        "link": r['href'],
                        "text": f"{r['title']} {body}",
                        "source": "DuckDuckGo"
                    })
        except Exception as e:
            logger.error(f"DuckDuckGo Scrape Error: {e}")
        
        return results

class GoogleScraper(BaseScraper):
    def scrape(self, query, time_window_hours=2):
        # Map hours to Google tbs format
        # qdr:h (last hour), qdr:hN (last N hours), qdr:d (last 24h), qdr:w (last week)
        tbs = "qdr:h"
        if time_window_hours > 1 and time_window_hours <= 24:
            tbs = f"qdr:h{time_window_hours}"
            if time_window_hours == 24: tbs = "qdr:d"
        elif time_window_hours > 24:
            days = time_window_hours // 24
            if days >= 7:
                tbs = "qdr:w"
            else:
                tbs = f"qdr:d{days}"
            
        # Add Kenya specific parameters to the URL
        url = f"https://www.google.com/search?q={query}&tbs={tbs}&gl=ke&hl=en&gws_rd=cr"
        logger.info(f"OUTBOUND CALL: Google Scrape for {query} (Window: {time_window_hours}h, TBS: {tbs})")
        
        content = self.get_page_content(url)
        if not content: 
            logger.warning(f"Google Scrape: No content returned for {query}")
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        results = []
        # Google's layout changes frequently; try multiple selectors
        # .g is the standard organic result container
        search_results = soup.select('div.g') or soup.select('div[data-ved]') or soup.select('div.MjjYud') or soup.select('div.tF2Cxc')
        logger.info(f"Google Scrape: Found {len(search_results)} raw results for {query}")
        
        for g in search_results:
            try:
                link_tag = g.select_one('a')
                if not link_tag: continue
                
                title_tag = g.select_one('h3') or g.select_one('div[role="heading"]') or g.select_one('div.vv77sc')
                snippet_tag = g.select_one('div.VwiC3b') or g.select_one('div.kb0u9b') or g.select_one('div.st') or g.select_one('span.aCOp7e')
                
                link = link_tag['href'] if link_tag.has_attr('href') else ""
                title = title_tag.text if title_tag else ""
                snippet = snippet_tag.text if snippet_tag else ""
                
                if not title and link_tag:
                    title = link_tag.get_text()
                
                # Clean Google redirect links
                if link.startswith('/url?q='):
                    link = link.split('/url?q=')[1].split('&')[0]
                elif link.startswith('/'):
                    continue # Skip internal google links
                    
                if link and title and not any(x in link for x in ['accounts.google.com', 'google.com/search', 'maps.google.com']):
                    results.append({"link": link, "text": f"{title} {snippet}", "source": "Google"})
            except Exception as e:
                logger.error(f"Error parsing Google result: {e}")
                continue
        
        return results

class FacebookMarketplaceScraper(BaseScraper):
    def scrape(self, query, time_window_hours=2):
        logger.info(f"OUTBOUND CALL: Facebook Marketplace Scrape for {query} (Window: {time_window_hours}h)")
        url = f"https://www.facebook.com/marketplace/search/?query={query}"
        # FB doesn't have a direct time filter in the URL, but we track the window for logging
        content = self.get_page_content(url)
        if not content:
            # Fallback to Google search for FB groups/posts if marketplace is blocked
            logger.warning(f"Facebook Marketplace directly unreachable or empty, falling back to targeted search...")
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        results = []
        
        # FB uses highly obfuscated classes. In a real scenario, we'd use more robust selectors or Graph API.
        # This implementation attempts to find any links that look like marketplace items.
        for a in soup.select('a[href*="/marketplace/item/"]'):
            link = "https://www.facebook.com" + a['href'] if a['href'].startswith('/') else a['href']
            text = a.get_text() or f"Marketplace Item for {query}"
            results.append({"link": link, "text": text, "source": "Facebook"})
            
        return results

