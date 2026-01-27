
from scraper import LeadScraper
import json
import logging

# Disable warnings from duckduckgo_search
logging.getLogger("duckduckgo_search").setLevel(logging.ERROR)

def test():
    scraper = LeadScraper()
    # Focus on the problematic ones
    platforms = ["reddit", "twitter", "facebook"]
    queries = [
        "iphone",
        "sofa bed",
    ]
    
    for platform in platforms:
        for query in queries:
            print(f"\n--- Testing {platform} with query: '{query}' ---")
            results = scraper.scrape_platform(platform, query, "Kenya")
            print(f"Found {len(results)} results")
            for i, res in enumerate(results[:3]):
                print(f" Result {i+1}: {res['link']}")
                print(f" Snippet: {res['text'][:100]}...")

if __name__ == "__main__":
    test()
