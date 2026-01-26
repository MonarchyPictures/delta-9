import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from app.scrapers.base_scraper import GoogleScraper
from app.utils.normalization import LeadValidator
from bs4 import BeautifulSoup

def test_google_scraper():
    print("Testing Google Scraper Agent...")
    scraper = GoogleScraper()
    # Use a common buying intent query
    query = "buying tires New York"
    url = f"https://www.google.com/search?q={query}"
    content = scraper.get_page_content(url)
    
    if content:
        print(f"Page content length: {len(content)}")
        if "detected unusual traffic" in content.lower() or "captcha" in content.lower():
            print("⚠️ Google detected bot traffic (CAPTCHA/Blocked).")
        
        soup = BeautifulSoup(content, 'html.parser')
        print(f"Page Title: {soup.title.text if soup.title else 'No Title'}")
    
    results = scraper.scrape(query)
    print(f"Found {len(results)} raw results.")
    
    validator = LeadValidator()
    normalized_leads = []
    for res in results[:3]: # Test first 3
        normalized = validator.normalize_lead(res)
        normalized_leads.append(normalized)
        print(f"Normalized Lead: {normalized['product_category']} from {normalized['source_platform']}")
        
    if len(normalized_leads) > 0:
        print("✅ Google Scraper Agent functional.")
    else:
        print("❌ Google Scraper Agent failed to produce leads.")

if __name__ == "__main__":
    try:
        test_google_scraper()
    except Exception as e:
        print(f"Agent Test Failed with error: {e}")
