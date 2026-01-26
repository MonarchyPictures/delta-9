import json
import time
import asyncio
import random
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class LeadScraper:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
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
                '--disable-setuid-sandbox'
            ]
        )
        context = browser.new_context(
            user_agent=ua,
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
        )
        # Add extra stealth script
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        return browser, context

    def google_search_dork(self, query, location="Kenya"):
        """Perform a Google search using dorks and return results via Playwright."""
        # Random delay to mimic human behavior (2-5 seconds)
        time.sleep(random.uniform(2, 5))
        
        # Use the query as provided if it contains advanced operators, else format it
        if "site:" in query or '"' in query:
            geo_query = query
        else:
            # Better buyer intent dorks
            geo_query = f'"{query}" {location} ("looking for" OR "where to buy" OR "price of")'
            
        print(f"Savage Google Search: {geo_query}")
        results = []
        with sync_playwright() as p:
            browser, context = self._get_browser_context(p)
            page = context.new_page()
            try:
                # Add location parameter to Google search URL (cr=countryKE for Kenya)
                # Use a more natural search URL
                search_url = f"https://www.google.com/search?q={geo_query.replace(' ', '+')}&cr=countryKE"
                page.goto(search_url, wait_until="networkidle", timeout=30000)
                
                # Check for bot detection / CAPTCHA
                page_content = page.content().lower()
                if "detected unusual traffic" in page_content or "captcha" in page_content:
                    print(f"WARNING: Google blocked the scraper for query: {geo_query}. Trying DuckDuckGo fallback...")
                    return self.duckduckgo_search(geo_query, location)

                # Wait for results or "No results found"
                try:
                    page.wait_for_selector("div.g", timeout=5000)
                except:
                    # If no results on Google, try DDG
                    return self.duckduckgo_search(geo_query, location)
                
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                for g in soup.select('div.g'):
                    link_tag = g.select_one('a')
                    link = link_tag['href'] if link_tag and 'href' in link_tag.attrs else ""
                    title_tag = g.select_one('h3')
                    title = title_tag.text if title_tag else ""
                    snippet_tag = g.select_one('div.VwiC3b')
                    snippet = snippet_tag.text if snippet_tag else ""
                    
                    if link and title:
                        results.append({
                            "source": "Google",
                            "link": link,
                            "text": f"{title} - {snippet}",
                            "category": "General",
                            "user": "Web Result",
                            "location": location
                        })
            except Exception as e:
                print(f"Error during Google search: {e}. Trying DuckDuckGo fallback...")
                return self.duckduckgo_search(geo_query, location)
            finally:
                browser.close()
        
        # If no results from Google, try DDG anyway
        if not results:
            return self.duckduckgo_search(geo_query, location)
            
        return results

    def duckduckgo_search(self, query, location="Kenya"):
        """Fallback search using DuckDuckGo (more scraper friendly, using requests)."""
        import requests
        from urllib.parse import urlparse, parse_qs, unquote
        time.sleep(random.uniform(1, 2))
        
        # Use the query as provided
        geo_query = query
        print(f"DuckDuckGo Fallback Search: {geo_query}")
        
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }
        
        results = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={geo_query.replace(' ', '+')}"
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                print(f"DDG Error: {response.status_code}")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            found_results = soup.select('.result__body')
            print(f"DDG found {len(found_results)} raw result bodies")
            
            for result in found_results:
                link_tag = result.select_one('.result__a')
                if not link_tag: continue
                
                raw_link = link_tag['href']
                # Clean DDG redirect links
                if "/l/?uddg=" in raw_link:
                    parsed_url = urlparse(raw_link)
                    qs = parse_qs(parsed_url.query)
                    if 'uddg' in qs:
                        link = unquote(qs['uddg'][0])
                    else:
                        link = raw_link
                else:
                    link = raw_link
                
                if link.startswith("//"):
                    link = "https:" + link
                
                title = link_tag.text.strip()
                snippet_tag = result.select_one('.result__snippet')
                snippet = snippet_tag.text.strip() if snippet_tag else ""
                
                if link and title:
                    results.append({
                        "source": "DuckDuckGo",
                        "link": link,
                        "text": f"{title} - {snippet}",
                        "category": "General",
                        "user": "Web Result",
                        "location": location
                    })
        except Exception as e:
            print(f"Error during DuckDuckGo search: {e}")
            
        return results

    def search_reddit(self, keywords, location="Kenya"):
        """Search Reddit for recent posts matching keywords in Kenya."""
        print(f"Aggressive Reddit Scrape: {keywords} in {location}")
        # Dynamic date for freshness (last 7 days)
        date_limit = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        query = f'site:reddit.com "{keywords}" "{location}" ("looking for" OR "need" OR "buying" OR "recommend") after:{date_limit}'
        return self.google_search_dork(query, location)

    def search_tiktok(self, keywords, location="Kenya"):
        """Search TikTok for recent posts/comments in Kenya via Google Dorks."""
        print(f"Scouring TikTok: {keywords} in {location}")
        # TikTok dorking is often more effective than direct search for intent
        query = f'site:tiktok.com "{keywords}" "{location}" ("buy" OR "where to get" OR "looking for")'
        return self.google_search_dork(query, location)

    def search_facebook(self, keywords, location="Kenya"):
        """Search Facebook public posts in Kenya."""
        print(f"Facebook Public Scrape: {keywords} in {location}")
        # FB dorking with Kenya constraint and common buying intent phrases
        query = f'site:facebook.com "{keywords}" "{location}" ("need" OR "buying" OR "looking for" OR "price of")'
        return self.google_search_dork(query, location)

    def search_twitter(self, keywords, location="Kenya"):
        """Search Twitter/X posts in Kenya."""
        print(f"Twitter/X Extraction: {keywords} in {location}")
        query = f'site:twitter.com "{keywords}" "{location}" "looking for" -filter:links'
        return self.google_search_dork(query, location)

    def scrape_platform(self, platform, query, location="Kenya"):
        """Generic platform scraper dispatcher."""
        if platform == "reddit":
            return self.search_reddit(query, location)
        elif platform == "tiktok":
            return self.search_tiktok(query, location)
        elif platform == "facebook":
            return self.search_facebook(query, location)
        elif platform == "twitter":
            return self.search_twitter(query, location)
        elif platform == "google":
            return self.google_search_dork(query, location)
        return []

if __name__ == "__main__":
    scraper = LeadScraper()
    print(scraper.search_reddit("tires"))
