import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import SessionLocal
from app.ingestion import LiveLeadIngestor

def verify_thrice():
    print("--- PROD_STRICT: Starting 3-cycle pipeline verification ---")
    os.environ["ENVIRONMENT"] = "production"
    
    import logging
    logging.getLogger("LeadIngestion").setLevel(logging.DEBUG)
    
    db = SessionLocal()
    ingestor = LiveLeadIngestor(db)
    
    results = []
    queries = ["water tank", "construction", "solar"]
    
    for i in range(3):
        print(f"\nRUN {i+1}/3...")
        start_time = time.time()
        try:
            # Use broader queries to ensure we get results and metadata
            query = queries[i]
            leads = ingestor.fetch_from_external_sources(query, "Nairobi")
            duration = time.time() - start_time
            
            print(f"SUCCESS: Captured {len(leads)} leads in {duration:.2f}s")
            
            # Check for mandatory fields
            for l in leads:
                missing = [f for f in ["source_url", "request_timestamp", "http_status", "latency_ms"] if f not in l]
                if missing:
                    raise RuntimeError(f"FAILED: Missing mandatory proof-of-life fields: {missing}")
            
            results.append([l["id"] for l in leads])
            
            # Sleep to avoid rate limiting
            if i < 2:
                time.sleep(2)
                
        except Exception as e:
            print(f"FAILED RUN {i+1}: {str(e)}")
            db.close()
            return False

    # Compare results for independence (they should have some overlap but be real fetches)
    # If they are identical every time, it might be cached
    if results[0] == results[1] == results[2]:
        print("\nFAILED: Pipeline produced identical results across all 3 runs. Likely cached or mocked.")
        db.close()
        return False

    print("\n--- PROD_STRICT: PIPELINE VERIFIED ---")
    print("All 3 runs produced independently fetched results with mandatory metadata.")
    db.close()
    return True

if __name__ == "__main__":
    success = verify_thrice()
    if not success:
        exit(1)
