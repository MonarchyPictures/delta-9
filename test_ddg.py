from duckduckgo_search import DDGS
import logging

logging.basicConfig(level=logging.DEBUG)

def test_ddg():
    print("Testing DuckDuckGo Search...")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text("buy iphone kenya", max_results=5, backend="html"))
            print(f"Found {len(results)} results")
            for r in results:
                print(r)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ddg()
