
import sys
import os
sys.path.append(os.getcwd())

from app.intelligence_v2.query_expander import expand_query

def test_expansion():
    print("--- 🧪 QUERY EXPANDER VERIFICATION ---")
    
    input_data = {
        "product": "Toyota",
        "category": "vehicles",
        "location": "Nairobi"
    }
    
    results = expand_query(
        input_data["product"], 
        input_data["location"], 
        input_data["category"]
    )
    
    print(f"Input: {input_data}")
    print(f"Expanded Queries ({len(results)}):")
    for q in results:
        print(f"  - {q}")
    
    # Validation checks
    expected_sw = "natafuta toyota nairobi"
    expected_en = "looking for toyota nairobi"
    
    has_sw = any(expected_sw == q.lower() for q in results)
    has_en = any(expected_en == q.lower() for q in results)
    
    if has_sw and has_en:
        print("\n✅ SUCCESS: Expansion includes both English and Swahili intent layers!")
    else:
        print("\n❌ FAILURE: Missing critical intent layers.")

if __name__ == "__main__":
    test_expansion()
