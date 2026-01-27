from duckduckgo_search import DDGS
import json

def test_search(query, source):
    print(f"\n--- Testing search for {source}: {query} ---")
    with DDGS() as ddgs:
        try:
            ddg_results = list(ddgs.text(query, region='wt-wt', max_results=5))
            print(f"Found {len(ddg_results)} results")
            for r in ddg_results:
                print(f"Title: {r['title']}")
                print(f"Link: {r['href']}")
                print(f"Snippet: {r['body'][:100]}...")
                print("-" * 20)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # Test natural queries
    test_search('buying selling Kenya reddit', "Reddit Natural")
    test_search('looking for "chicken feed" Kenya facebook', "Facebook Natural")
    test_search('where can I buy iphone Kenya twitter', "Twitter Natural")
