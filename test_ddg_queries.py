from duckduckgo_search import DDGS
import json

def test_search(query, source):
    print(f"Testing search for {source}: {query}")
    results = []
    with DDGS() as ddgs:
        try:
            ddg_results = list(ddgs.text(query, region='ke-en', max_results=10))
            print(f"Found {len(ddg_results)} results")
            for r in ddg_results:
                print(f"- {r['href']}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # Test Twitter
    test_search('site:twitter.com "buying" Kenya', "Twitter")
    test_search('site:x.com "buying" Kenya', "X")
    test_search('"buying" Kenya twitter.com', "Twitter keyword")
    # Test Reddit
    test_search('site:reddit.com "buying" Kenya', "Reddit")
    # Test Facebook
    test_search('site:facebook.com "buying" Kenya', "Facebook")
