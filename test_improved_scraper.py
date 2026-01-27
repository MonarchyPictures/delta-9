
import os
import sys
from scraper import LeadScraper

def test_scraper():
    print("Testing improved LeadScraper...")
    scraper = LeadScraper()
    
    # Test Google Search with Dork
    query = "solar panels Nairobi"
    location = "Kenya"
    print(f"Searching for: {query} in {location}")
    
    results = scraper.scrape_platform("google", query, location)
    print(f"Found {len(results)} results.")
    
    # Test Social Search via DDG
    print("\nTesting Social Search (Facebook via DDG)...")
    social_results = scraper.scrape_platform("facebook", "furniture Nairobi", "Kenya")
    print(f"Found {len(social_results)} facebook results.")
    for i, res in enumerate(social_results[:5]):
        print(f"{i+1}. [{res['source']}] {res['text'][:100]}...")

if __name__ == "__main__":
    test_scraper()
