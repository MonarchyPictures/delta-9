
from duckduckgo_search import DDGS

def test_ddgs():
    print("Testing DDGS directly...")
    try:
        with DDGS() as ddgs:
            # Try with 'wt-wt' and see if it's better
            results = ddgs.text("solar panels Nairobi", region='wt-wt', max_results=10)
            if not results:
                print("No results found.")
            for r in results:
                print(f"Title: {r['title']}")
                print(f"Link: {r['href']}")
                print("-" * 20)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ddgs()
