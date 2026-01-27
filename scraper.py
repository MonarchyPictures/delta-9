import json
import time
import asyncio
import random
import requests
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class LeadScraper:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Edge/121.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (iPad; CPU OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1"
        ]

    def _get_browser_context(self, playwright):
        # Use a random user agent for each session
        ua = random.choice(self.user_agents)
        # Use a more realistic browser setup
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certifcate-errors',
                '--ignore-certifcate-errors-spki-list',
                '--user-agent=' + ua
            ]
        )
        
        # Create context with more realistic features
        context = browser.new_context(
            user_agent=ua,
            viewport={'width': random.randint(1280, 1920), 'height': random.randint(720, 1080)},
            device_scale_factor=1,
            has_touch=random.choice([True, False]),
            locale=random.choice(['en-US', 'en-GB', 'en-KE']),
            timezone_id='Africa/Nairobi'
        )
        
        # Add extra stealth script to bypass detection
        context.add_init_script("""
            // Overwrite the 'webdriver' property to avoid detection
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Overwrite the 'languages' property
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });

            // Overwrite the 'plugins' property
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            // Mock chrome object
            window.chrome = {
                runtime: {}
            };

            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        return browser, context

    def bing_search(self, query, location="Kenya", source="Bing"):
        """Search Bing using Playwright for better bypass of bot detection."""
        print(f"Bing Playwright Search ({source}): {query}")
        
        results = []
        browser = None
        try:
            with sync_playwright() as p:
                browser, context = self._get_browser_context(p)
                page = context.new_page()
                
                # Navigate to Bing
                search_url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
                try:
                    # Use 'load' instead of 'networkidle' as it's faster and more reliable
                    page.goto(search_url, wait_until="load", timeout=60000)
                    time.sleep(random.uniform(3, 5))
                except Exception as e:
                    print(f"Bing goto error: {e}")
                    # Try one more time with a simpler wait
                    try:
                        time.sleep(5)
                        page.goto(search_url, wait_until="commit", timeout=30000)
                    except:
                        pass
                
                # Check for CAPTCHA or results
                try:
                    # Wait for either results or a known CAPTCHA indicator
                    page.wait_for_selector("li.b_algo, #b_results, .b_captcha, #captcha-container", timeout=15000)
                except:
                    pass

                # Check URL and content for CAPTCHA
                is_captcha = False
                current_url = page.url.lower()
                if "verify" in current_url or "captcha" in current_url:
                    is_captcha = True
                
                if not is_captcha:
                    try:
                        # Use a safer way to get content that doesn't fail during navigation
                        content = page.evaluate("() => document.body.innerText").lower()
                        if "verify you are a human" in content or "blocked" in content:
                            is_captcha = True
                    except:
                        pass
                
                if is_captcha:
                    print(f"Bing CAPTCHA or Block detected for {source}")
                    browser.close()
                    return []

                # Try multiple selectors for results
                selectors = ["li.b_algo", ".b_algo", "#b_results li", ".b_results li"]
                found_selector = None
                for selector in selectors:
                    try:
                        if page.query_selector(selector):
                            found_selector = selector
                            break
                    except:
                        continue
                
                if not found_selector:
                    print(f"No Bing results found for {source}")
                    # Take a screenshot for debugging if needed (optional)
                    # page.screenshot(path=f"bing_error_{source}.png")
                    browser.close()
                    return []
                
                # Extract results
                search_results = page.query_selector_all(found_selector)
                print(f"Bing found {len(search_results)} raw elements for {source}")
                
                for res in search_results:
                    try:
                        title_el = res.query_selector("h2 a")
                        snippet_el = res.query_selector(".b_caption p") or res.query_selector(".snippet") or res.query_selector(".b_lineclamp2") or res.query_selector(".b_caption")
                        
                        if title_el:
                            title = title_el.inner_text()
                            link = title_el.get_attribute("href")
                            snippet = snippet_el.inner_text() if snippet_el else ""
                            
                            if not link or not link.startswith("http"): continue
                            href_lower = link.lower()
                            
                            # Platform filtering logic - strictly enforce if not a general search
                            if source not in ["Google", "DuckDuckGo", "Bing"]:
                                platforms = {
                                    "Facebook": ["facebook.com", "fb.com", "fb.me"],
                                    "Reddit": ["reddit.com", "redd.it"],
                                    "TikTok": ["tiktok.com"],
                                    "Twitter": ["twitter.com", "x.com", "t.co"],
                                    "LinkedIn": ["linkedin.com"]
                                }
                                allowed_domains = platforms.get(source, [source.lower() + ".com"])
                                
                                # Extract domain from link for better matching
                                try:
                                    from urllib.parse import urlparse
                                    parsed_link = urlparse(link)
                                    domain = parsed_link.netloc.lower()
                                    path = parsed_link.path.lower()
                                    
                                    if not any(ad in domain for ad in allowed_domains):
                                        continue
                                        
                                    # EXCLUDE common non-post pages (RELAXED)
                                    noise = ["/login", "/signup", "robots.txt", "/terms", "/privacy", "/help/", "/support/", "index.php", "home=", "about.fb.com", "business.facebook.com", "/directory/", "/policies/"]
                                    if any(n in path for n in noise):
                                        continue
                                        
                                    # EXCLUDE top-level and utility pages
                                    if path in ["/", "", "/home", "/explore", "/facebook/", "/twitter/", "/reddit/"]:
                                        continue
                                    if domain in ["l.facebook.com", "m.me"]:
                                        continue
                                        
                                    # INCLUDE patterns for specific platforms - EXTREMELY RELAXED
                                    is_valid = False
                                    if source == "Facebook":
                                        # Include almost any Facebook link that isn't login/signup/noise
                                        if any(p in path for p in ["/groups/", "/posts/", "/permalink/", "/marketplace/", "/story.php", "/photo.php", "/p/", "/events/"]):
                                            is_valid = True
                                        elif len(path.strip('/')) > 3: # Relaxed: profiles can be short
                                            is_valid = True
                                    elif source == "Twitter":
                                        if any(p in path for p in ["/status/", "/hashtag/", "/events/", "/i/"]):
                                            is_valid = True
                                        elif len(path.strip('/')) > 3: # Likely a profile
                                            is_valid = True
                                    elif source == "Reddit":
                                        if any(p in path for p in ["/r/", "/user/", "/comments/"]):
                                            is_valid = True
                                        elif len(path.strip('/')) > 3:
                                            is_valid = True
                                    elif source == "TikTok":
                                        if any(p in path for p in ["/video/", "/@", "/discover/"]):
                                            is_valid = True
                                        elif len(path.strip('/')) > 3:
                                            is_valid = True
                                    else:
                                        is_valid = True
                                        
                                    if not is_valid:
                                        # If it's a social link but didn't match patterns, 
                                        # we'll still keep it if it has some depth
                                        if len(path.strip('/')) > 2:
                                            is_valid = True
                                        else:
                                            print(f"Skipping {source} link due to path: {path}")
                                            continue
                                        
                                except:
                                    if not any(ad in href_lower for ad in allowed_domains):
                                        continue
                            
                            results.append({
                                "source": source,
                                "link": link,
                                "text": f"{title} - {snippet}",
                                "category": "General",
                                "user": "Social Post" if source not in ["Google", "Bing"] else "Web Result",
                                "location": location
                            })
                    except Exception as res_err:
                        continue
                
                browser.close()
                return results
        except Exception as e:
            print(f"Bing Playwright search error: {e}")
            if browser:
                try:
                    browser.close()
                except:
                    pass
            return []

    def google_search(self, query, location="Kenya"):
        """Search Google via Bing fallback for better reliability."""
        print(f"Google Search: {query}")
        # Use Bing for Google queries as it's more reliable with Playwright
        return self.bing_search(query, location, source="Google")

    def duckduckgo_search(self, query, location="Kenya", source="DuckDuckGo"):
        """Search DuckDuckGo with improved query handling and retry logic."""
        try:
            # Try the new package name first
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
        except ImportError:
            print("Error: duckduckgo_search/ddgs package not found. Please install with 'pip install duckduckgo_search'")
            return []
        
        print(f"DuckDuckGo Search ({source}): {query}")
        
        results = []
        # Try multiple times with increasing delays and query simplification
        for attempt in range(4):
            try:
                # Add a small random delay to avoid rapid-fire requests
                time.sleep(random.uniform(2, 4))
                
                current_query = query
                # Simplification logic
                if attempt == 1:
                    # Remove quotes and years
                    current_query = query.replace('"', '').replace('2025', '').replace('2026', '')
                elif attempt == 2:
                    # Very simple query - just keywords and platform
                    parts = query.split()
                    keywords = " ".join([p for p in parts if not p.startswith("site:") and p.lower() != source.lower()])
                    current_query = f"{source} {keywords} {location}"
                elif attempt == 3:
                    # Pure keywords
                    current_query = query.split('"')[1] if '"' in query else query
                    parts = current_query.split()
                    current_query = " ".join([p for p in parts if not p.startswith("site:")])
                
                with DDGS() as ddgs:
                    # Use region-specific search if possible
                    region = 'ke-en' if 'kenya' in location.lower() else 'wt-wt'
                    
                    # Use 'm' (month) for social sources to get relatively fresh leads
                    # But if we get nothing, we'll try without time limit in later attempts
                    t_limit = 'm' if (source in ["Facebook", "Twitter", "Reddit", "TikTok"] and attempt < 2) else None
                    
                    try:
                        # Use text search
                        # The text() method returns a list of dicts with 'title', 'href', 'body'
                        ddg_results = list(ddgs.text(current_query, region=region, max_results=25, timelimit=t_limit))
                    except Exception as e:
                        err_str = str(e).lower()
                        if "202" in err_str or "ratelimit" in err_str or "429" in err_str:
                            print(f"DDG rate limited ({err_str}). Waiting longer...")
                            time.sleep(random.uniform(15, 25))
                            continue
                        
                        # Handle potential ddgs package issues
                        print(f"DDG Error on attempt {attempt+1}: {e}")
                        continue
                    
                    if ddg_results:
                        print(f"DDG found {len(ddg_results)} results for {source}")
                        for r in ddg_results:
                            href = r['href'].lower()
                            
                            # General filtering for all sources
                            blacklist = [
                                "baidu.com", "zhihu.com", "douban.com", "weibo.com", 
                                "qq.com", "163.com", "sina.com.cn", "sohu.com",
                                "amazon.com", "ebay.com", "alibaba.com", "aliexpress.com",
                                "jumia.co.ke", "kilimall.co.ke", "copia.co.ke",
                                "/login", "/signup", "robots.txt", "/terms", "/privacy"
                            ]
                            if any(d in href for d in blacklist):
                                continue

                            # Platform filtering logic - strictly enforce if not a general search
                            if source not in ["Google", "DuckDuckGo", "Bing"]:
                                platforms = {
                                    "Facebook": ["facebook.com", "fb.com", "fb.me"],
                                    "Reddit": ["reddit.com", "redd.it"],
                                    "TikTok": ["tiktok.com"],
                                    "Twitter": ["twitter.com", "x.com", "t.co"],
                                    "LinkedIn": ["linkedin.com"]
                                }
                                allowed_domains = platforms.get(source, [source.lower() + ".com"])
                                
                                # Extract domain for better matching
                                try:
                                    from urllib.parse import urlparse
                                    parsed_link = urlparse(r['href'])
                                    domain_netloc = parsed_link.netloc.lower()
                                    path = parsed_link.path.lower()
                                    
                                    is_allowed_domain = any(ad in domain_netloc for ad in allowed_domains)
                                    if not is_allowed_domain:
                                        is_allowed_domain = any(ad in href for ad in allowed_domains)
                                    
                                    if not is_allowed_domain:
                                        continue
                                        
                                    # EXCLUDE common noise pages
                                    noise = ["/help/", "/support/", "index.php", "home=", "about.fb.com", "business.facebook.com", "/directory/", "/policies/", "/legal/"]
                                    if any(n in path for n in noise):
                                        continue
                                        
                                    # EXCLUDE top-level and utility pages
                                    if path in ["/", "", "/home", "/explore", "/facebook/", "/twitter/", "/reddit/", "/login/", "/signup/"]:
                                        continue
                                        
                                except:
                                    if not any(ad in href for ad in allowed_domains):
                                        continue
                            
                            results.append({
                                "source": source,
                                "link": r['href'],
                                "text": f"{r['title']} - {r['body']}",
                                "category": "General",
                                "user": "Social Post" if source not in ["Google", "Bing"] else "Web Result",
                                "location": location
                            })
                        
                        if results:
                            return results
                    
                print(f"DDG Attempt {attempt+1} ({current_query}) no relevant results. Retrying...")
            except Exception as e:
                print(f"Error during DDG attempt {attempt+1}: {e}")
            
        # If all DDG attempts fail, try Bing as a last resort fallback
        if not results and source not in ["Bing"]:
            print(f"DDG failed for {source}. Trying Bing fallback...")
            return self.bing_search(query, location, source=source)
            
        return results

    def search_reddit(self, keywords, location="Kenya"):
        """Search Reddit for recent posts matching keywords in Kenya."""
        print(f"Reddit Search: {keywords}")
        # Use simpler queries for better recall
        queries = [
            f'site:reddit.com "{keywords}" {location}',
            f'Reddit {keywords} {location} "buying"',
            f'site:reddit.com/r/Kenya {keywords}'
        ]
        
        all_results = []
        for query in queries:
            results = self.duckduckgo_search(query, location, source="Reddit")
            if results:
                all_results.extend(results)
                if len(all_results) >= 15: break
            
        return all_results

    def search_tiktok(self, keywords, location="Kenya"):
        """Search TikTok for recent posts/comments in Kenya via DDG."""
        print(f"TikTok Search: {keywords}")
        # TikTok results often have "video" or "explore" in the URL
        query = f'TikTok {keywords} {location} "buy"'
        return self.duckduckgo_search(query, location, source="TikTok")

    def search_facebook(self, keywords, location="Kenya"):
        """Search Facebook public posts and marketplace in Kenya."""
        print(f"Facebook Search: {keywords}")
        # Use simpler queries for better recall
        queries = [
            f'site:facebook.com "{keywords}" {location}',
            f'Facebook marketplace {keywords} {location}',
            f'site:facebook.com/groups {keywords} Kenya'
        ]
        
        all_results = []
        for query in queries:
            results = self.duckduckgo_search(query, location, source="Facebook")
            if results:
                all_results.extend(results)
                if len(all_results) >= 20: break
                
        return all_results

    def search_twitter(self, keywords, location="Kenya"):
        """Search Twitter/X posts in Kenya."""
        print(f"Twitter Search: {keywords}")
        # Use simpler queries for better recall
        queries = [
            f'site:twitter.com "{keywords}" {location}',
            f'Twitter {keywords} {location} "buying"',
            f'site:twitter.com "{keywords}" Kenya'
        ]
        
        all_results = []
        for query in queries:
            results = self.duckduckgo_search(query, location, source="Twitter")
            if results:
                all_results.extend(results)
                if len(all_results) >= 15: break
                
        return all_results

    def scrape_platform(self, platform, keywords, location="Kenya"):
        """Entry point for scraping different platforms."""
        try:
            platform_lower = platform.lower()
            if platform_lower == "google":
                # Very simple query for Google to avoid detection
                query = f"{keywords} {location}"
                return self.google_search(query, location)
            elif platform_lower == "reddit":
                return self.search_reddit(keywords, location)
            elif platform_lower == "tiktok":
                return self.search_tiktok(keywords, location)
            elif platform_lower == "facebook":
                return self.search_facebook(keywords, location)
            elif platform_lower == "twitter":
                return self.search_twitter(keywords, location)
            elif platform_lower == "bing":
                query = f'"{keywords}" {location}'
                return self.bing_search(query, location, source="Bing")
            else:
                # Default to Bing search for unknown platforms
                query = f'site:{platform_lower}.com "{keywords}" {location}'
                return self.bing_search(query, location, source=platform.capitalize())
        except Exception as e:
            print(f"Error scraping {platform}: {e}")
            return []

if __name__ == "__main__":
    scraper = LeadScraper()
    print(scraper.search_reddit("tires"))
