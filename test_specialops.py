from app.core.specialops import SpecialOpsAgent
import json

def test_mission():
    agent = SpecialOpsAgent()
    query = "tires"
    location = "Kenya"
    
    print(f"Testing SpecialOps mission for '{query}' in {location}...")
    leads = agent.execute_mission(query, location)
    
    print(f"\nFound {len(leads)} leads:")
    for i, lead in enumerate(leads):
        print(f"{i+1}. [{lead.get('confidence')}%] {lead.get('url')}")
        print(f"   Snippet: {lead.get('data', {}).get('raw_text', '')[:100]}...")
        print(f"   Intent: {lead.get('intent_type', 'UNKNOWN')}")

if __name__ == "__main__":
    test_mission()
