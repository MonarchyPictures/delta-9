
import sys
import os
from sqlalchemy import inspect
from app.db.database import engine

def check_schema():
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('leads')]
    print(f"Columns in leads table: {columns}")
    
    expected = ['id', 'buyer_name', 'title', 'price', 'location', 'source', 'url', 'intent_score', 'created_at']
    missing = [c for c in expected if c not in columns]
    
    if missing:
        print(f"MISSING COLUMNS: {missing}")
        sys.exit(1)
    else:
        print("All core columns present.")

if __name__ == "__main__":
    check_schema()
