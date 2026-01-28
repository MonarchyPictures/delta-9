from scraper import LeadScraper
import json

def test_ddg():
    scraper = LeadScraper()
    query = "tires Kenya \"looking for\""
    print(f"Testing DuckDuckGo Search for: {query}")
    results = scraper.duckduckgo_search(query, location="Kenya", source="DuckDuckGo")
    print(f"Found {len(results)} results")
    for r in results[:5]:
        print(f" - {r['link']}: {r['text'][:100]}...")

if __name__ == "__main__":
    test_ddg()
