from scraper import LeadScraper
import json

def test_bing():
    scraper = LeadScraper()
    query = "tires Kenya \"looking for\""
    print(f"Testing Bing Search for: {query}")
    results = scraper.bing_search(query, location="Kenya", source="Bing")
    print(f"Found {len(results)} results")
    for r in results[:5]:
        print(f" - {r['link']}: {r['text'][:100]}...")

if __name__ == "__main__":
    test_bing()
