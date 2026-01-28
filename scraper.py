import json
import time
import asyncio
import random
import requests
import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from duckduckgo_search import DDGS

class LeadScraper:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ]
        # Intent-driven search templates for higher signal-to-noise
        # REWRITTEN: Focus exclusively on buyer phrases, remove seller-bait (price, available)
        self.intent_templates = [
            '"{query}" "looking for" {location}',
            '"{query}" "where can i buy" {location}',
            '"{query}" "anyone selling" {location}',
            '"{query}" "recommendations" {location}',
            '"{query}" "need" {location}',
            '"{query}" "urgent" {location}',
            '"{query}" "natafuta" {location}',
            '"{query}" "nahitaji" {location}'
        ]

    def duckduckgo_search(self, query, location="Kenya", source="DuckDuckGo", max_results=25):
        """Search DuckDuckGo with improved query handling, retries, and intent expansion."""
        print(f"DuckDuckGo Search ({source}): {query} in {location}")
        
        # 1. Expand query with intent templates for better signal
        search_queries = [f"{query} {location}"]
        # Only expand if it's not already a specific site search
        if "site:" not in query:
             # Add more intent-heavy variations to get more leads
             templates = random.sample(self.intent_templates, 3)
             for t in templates:
                 search_queries.append(t.format(query=query, location=location))
        else:
            # If it is a site search, try to vary it slightly if it fails
            search_queries.append(query)

        all_results = []
        
        try:
            with DDGS() as ddgs:
                for sq in search_queries:
                    print(f"Executing expanded query: {sq}")
                    
                    # Try multiple times for each expanded query
                    for attempt in range(3):
                        try:
                            # Shorter sleep for DDG if we are being careful
                            time.sleep(random.uniform(2, 5))
                            region = 'ke-en' if 'kenya' in location.lower() else 'wt-wt'
                            
                            # Use 'm' (month) for general, but 'w' (week) for social to get fresh leads
                            # 'd' (day) might be too restrictive if no posts happened today
                            t_limit = 'w' if source in ["Facebook", "Twitter", "Reddit", "TikTok"] else 'm'
                            
                            # Use a longer timeout for the request
                            ddg_results = list(ddgs.text(sq, region=region, max_results=max_results, timelimit=t_limit))
                            
                            if ddg_results:
                                for r in ddg_results:
                                    href = r['href'].lower()
                                    
                                    # Filtering
                                    blacklist = ["amazon.com", "ebay.com", "alibaba.com", "jumia.co.ke", "/login", "/signup", "pigiame.co.ke", "jiji.co.ke"]
                                    if any(d in href for d in blacklist): continue

                                    # Platform filtering
                                    if source not in ["Google", "DuckDuckGo", "Bing"]:
                                        platforms = {
                                            "Facebook": ["facebook.com", "fb.com"],
                                            "Reddit": ["reddit.com"],
                                            "TikTok": ["tiktok.com"],
                                            "Twitter": ["twitter.com", "x.com"]
                                        }
                                        allowed = platforms.get(source, [])
                                        if allowed and not any(ad in href for ad in allowed): continue

                                    all_results.append({
                                        "source": source,
                                        "link": r['href'],
                                        "text": f"{r['title']} - {r['body']}",
                                        "category": "General",
                                        "user": "Social Post" if source not in ["Google", "Bing", "DuckDuckGo"] else "Web Result",
                                        "location": location
                                    })
                                if len(all_results) >= max_results:
                                    break # Got enough for this query
                        except Exception as e:
                            print(f"DDG Error on attempt {attempt+1} for {sq}: {e}")
                            time.sleep(5)
                    
                    if len(all_results) >= 50:
                        break
            
            # 2. Fallback to Bing if DDG failed completely
            if not all_results and source != "Bing":
                print(f"DDG failed for {source}. Trying Bing fallback...")
                return self.bing_search(query, location, source=source)
                
            return all_results
        except Exception as e:
            print(f"DuckDuckGo engine error: {e}")
            return []

    def serpapi_search(self, query, location="Kenya", source="Google"):
        """
        Premium search using SerpApi (highly recommended for production).
        To use: 
        1. Get an API key from https://serpapi.com/
        2. Set it in your .env as SERPAPI_KEY
        """
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            print("SerpApi key not found. Falling back to DuckDuckGo.")
            return self.duckduckgo_search(query, location, source)
            
        print(f"SerpApi Search ({source}): {query}")
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "location": location,
            "hl": "en",
            "gl": "ke",
            "google_domain": "google.com",
            "api_key": api_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            results = []
            
            for r in data.get("organic_results", []):
                results.append({
                    "source": source,
                    "link": r.get("link"),
                    "text": f"{r.get('title')} - {r.get('snippet')}",
                    "category": "General",
                    "user": "Web Result",
                    "location": location
                })
            return results
        except Exception as e:
            print(f"SerpApi error: {e}")
            return self.duckduckgo_search(query, location, source)

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
                selectors = [
                    "li.b_algo", 
                    ".b_algo", 
                    "#b_results li", 
                    "article",
                    ".b_caption",
                    "div.b_title"
                ]
                
                # Wait for any of the selectors to appear
                try:
                    page.wait_for_selector("li.b_algo, .b_algo, #b_results, article", timeout=5000)
                except:
                    pass

                found_selector = None
                for selector in selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        if elements and len(elements) > 0:
                            found_selector = selector
                            break
                    except:
                        continue
                
                if not found_selector:
                    print(f"No Bing results found for {source} after trying all selectors")
                    # Fallback: Just get all links from the page
                    search_results = page.query_selector_all("a")
                    print(f"Fallback: Found {len(search_results)} links on Bing page")
                else:
                    search_results = page.query_selector_all(found_selector)
                    print(f"Bing found {len(search_results)} raw elements for {source}")
                
                for res in search_results:
                    try:
                        # Try to find link and text within or as the element itself
                        link = None
                        text = ""
                        
                        if found_selector == "a":
                            link = res.get_attribute("href")
                            title = res.inner_text()
                            snippet = ""
                            text = title
                        else:
                            title_el = res.query_selector("h2 a") or res.query_selector("a")
                            snippet_el = res.query_selector(".b_caption p") or res.query_selector(".snippet") or res.query_selector(".b_lineclamp2") or res.query_selector(".b_caption")
                            
                            if title_el:
                                link = title_el.get_attribute("href")
                                title = title_el.inner_text()
                                snippet = snippet_el.inner_text() if snippet_el else ""
                                text = f"{title} - {snippet}"
                            else:
                                continue
                        
                        if not link or not link.startswith("http"): continue
                        if "bing.com" in link or "microsoft.com" in link: continue
                        
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
                    
                    # Use 'd' (day) for social sources on first attempt for fresh leads,
                    # then 'm' (month) for better volume, then None
                    if source in ["Facebook", "Twitter", "Reddit", "TikTok", "LinkedIn", "Instagram"]:
                        if attempt == 0:
                            t_limit = 'd'
                        elif attempt == 1:
                            t_limit = 'w'
                        elif attempt == 2:
                            t_limit = 'm'
                        else:
                            t_limit = None
                    else:
                        t_limit = None
                    
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

    def google_search_direct(self, query, location="Kenya", source="Google", max_results=20):
        """
        Direct Google search using googlesearch-python.
        """
        from googlesearch import search
        print(f"Direct Google Search: {query} in {location}")
        results = []
        try:
            # Search query construction - use explicit buyer intent
            # We combine multiple variations to increase volume
            intent_variations = [
                f"{query} {location} \"looking for\"",
                f"{query} {location} \"need\"",
                f"{query} {location} \"where to buy\"",
                f"{query} {location} \"natafuta\""
            ]
            
            for q in intent_variations:
                print(f"Direct Google variation: {q}")
                try:
                    for url in search(q, num_results=max_results // 2, lang="en"):
                        if url not in [r['link'] for r in results]:
                            results.append({
                                "source": "Google",
                                "link": url,
                                "text": f"Google Result for {query}",
                                "category": "General",
                                "user": "Web Result",
                                "location": location
                            })
                except Exception as ve:
                    print(f"Variation error: {ve}")
                    continue
                    
            return results
        except Exception as e:
            print(f"Google direct search error: {e}")
            return []

    def scrape_platform(self, platform, query, location="Kenya", radius=50):
        """
        Main entry point for scraping.
        """
        print(f"Scraping {platform} for '{query}' in {location}...")
        
        # 1. Try SerpApi if key exists
        if os.getenv("SERPAPI_KEY"):
            return self.serpapi_search(query, location, source=platform.capitalize())
            
        # 2. Multi-source selection
        if platform.lower() == "google":
            # Combine DDG Google results and Direct Google
            ddg_g = self.duckduckgo_search(query, location, source="Google")
            direct_g = self.google_search_direct(query, location, source="Google")
            return ddg_g + direct_g
            
        # 3. Default to DDG for social platforms
        return self.duckduckgo_search(query, location, source=platform.capitalize())

if __name__ == "__main__":
    scraper = LeadScraper()
    print(scraper.search_reddit("tires"))
