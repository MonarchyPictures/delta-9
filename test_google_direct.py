from googlesearch import search
import json

def test_google(query):
    print(f"\n--- Testing Google Search: {query} ---")
    try:
        results = []
        for url in search(query, num_results=10):
            print(f"- {url}")
            results.append(url)
        print(f"Found {len(results)} results")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_google('site:reddit.com "buying" Kenya')
    test_google('site:facebook.com "buying" Kenya')
    test_google('site:twitter.com "buying" Kenya')
