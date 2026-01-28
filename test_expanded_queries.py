import sys
import os
from scraper import LeadScraper
from ddgs import DDGS

def test_expanded_queries():
    query = "tires"
    location = "Kenya"
    expanded_queries = [
        f'site:reddit.com ("looking for" OR "where can I buy" OR "anyone selling" OR "recommend" OR "need" OR "searching for" OR "who sells" OR "where can i get") "{query}" ("Kenya" OR "Nairobi" OR "Mombasa" OR "Kisumu")',
        f'"{query}" Kenya "natafuta"',
        f'"{query}" Kenya "nahitaji"',
    ]
    
    with DDGS() as ddgs:
        for q in expanded_queries:
            print(f"\nTesting Query: {q}")
            try:
                results = list(ddgs.text(q, region='ke-en', max_results=5))
                print(f"Found {len(results)} results")
                for r in results:
                    print(f" - {r['href']}: {r['title'][:50]}...")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    test_expanded_queries()
