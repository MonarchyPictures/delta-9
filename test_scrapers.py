
from scraper import LeadScraper
import json

def test():
    scraper = LeadScraper()
    platforms = ["reddit", "twitter", "facebook", "tiktok", "google"]
    queries = [
        "looking for where can I buy",
        "price of budget",
        "iphone laptop shop",
        "sofa bed dining table",
        "chicken feed poultry water tank"
    ]
    
    for platform in platforms:
        for query in queries:
            print(f"\n--- Testing {platform} with query: '{query}' ---")
            results = scraper.scrape_platform(platform, query, "Kenya")
            print(f"Found {len(results)} results")
            if results:
                # Show the first result's link and snippet
                print(f"First result: {results[0]['link']}")
                print(f"Snippet: {results[0]['text'][:100]}...")
            else:
                print(f"NO RESULTS for {platform} with '{query}'")

if __name__ == "__main__":
    test()
