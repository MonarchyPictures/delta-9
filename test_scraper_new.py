from scraper import LeadScraper
import json

def test_scraper():
    scraper = LeadScraper()
    keywords = "buying used iphone"
    location = "Kenya"
    
    print(f"Testing scraper with keywords: '{keywords}' in {location}")
    
    # Test individual platforms
    platforms = ["reddit", "facebook", "twitter"]
    all_results = []
    
    for p in platforms:
        print(f"\n--- Testing {p.upper()} ---")
        results = scraper.scrape_platform(p, keywords, location)
        print(f"Found {len(results)} results for {p}")
        for r in results[:3]:
            print(f"  - {r['link']} | {r['text'][:100]}...")
        all_results.extend(results)

    print(f"\nTotal results found: {len(all_results)}")
    
    if all_results:
        # Save to a file for inspection
        with open("test_results.json", "w") as f:
            json.dump(all_results, f, indent=2)
        print("Results saved to test_results.json")
    else:
        print("No results found on any platform.")

if __name__ == "__main__":
    test_scraper()
