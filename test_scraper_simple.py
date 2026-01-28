import sys
import os
from scraper import LeadScraper

def test_scraper():
    scraper = LeadScraper()
    results = scraper.duckduckgo_search("tires", location="Kenya", source="DuckDuckGo")
    print(f"Found {len(results)} results from DDG")
    for r in results[:2]:
        print(f" - {r['link']}")

if __name__ == "__main__":
    test_scraper()
