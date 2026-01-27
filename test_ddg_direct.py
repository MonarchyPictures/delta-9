
from duckduckgo_search import DDGS
import json

def test_ddg():
    with DDGS() as ddgs:
        print("Testing with timelimit='w'...")
        results = list(ddgs.text("iphone Kenya", timelimit='w', max_results=5))
        print(f"Results: {len(results)}")
        for r in results:
            print(f" - {r['href']}")

if __name__ == "__main__":
    test_ddg()
