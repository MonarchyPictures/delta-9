import sqlite3
import os

def cleanup():
    db_path = 'intent_radar.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Checking subdirectories...")
        # Try to find it in the current or subdirectories
        for root, dirs, files in os.walk('.'):
            if 'intent_radar.db' in files:
                db_path = os.path.join(root, 'intent_radar.db')
                print(f"Found database at {db_path}")
                break
        else:
            print("Database 'intent_radar.db' really not found.")
            return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Add intent_type column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE leads ADD COLUMN intent_type TEXT DEFAULT 'UNKNOWN'")
        print("Added intent_type column to leads table.")
    except sqlite3.OperationalError:
        print("intent_type column already exists in leads table.")

    # 2. Add agent columns if they don't exist
    agent_columns = [
        ("radius", "INTEGER DEFAULT 50"),
        ("min_intent_score", "FLOAT DEFAULT 0.7"),
        ("enable_alerts", "INTEGER DEFAULT 1")
    ]
    for col_name, col_type in agent_columns:
        try:
            cursor.execute(f"ALTER TABLE agents ADD COLUMN {col_name} {col_type}")
            print(f"Added {col_name} column to agents table.")
        except sqlite3.OperationalError:
            print(f"{col_name} column already exists in agents table.")

    # 3. Seller keywords to purge existing bad leads
    seller_keywords = [
        "for sale", "selling", "available", "price", "discount", "offer", 
        "promo", "delivery", "in stock", "we sell", "shop", "dealer", 
        "supplier", "warehouse", "order now", "dm for price", 
        "call / whatsapp", "our store", "brand new", "limited stock",
        "flash sale", "retail price", "wholesale", "best price",
        "check out", "visit us", "located at", "we deliver", "buy from us",
        "contact for price", "special offer", "new arrival", "stockist",
        "dm to order", "shipping available", "price is", "kwa bei ya",
        "tunauza", "mzigo mpya", "punguzo"
    ]

    # 3. Purge leads containing seller keywords
    for keyword in seller_keywords:
        cursor.execute("DELETE FROM leads WHERE lower(buyer_request_snippet) LIKE ?", (f'%{keyword}%',))
        if cursor.rowcount > 0:
            print(f"Deleted {cursor.rowcount} leads containing '{keyword}'")

    # 4. Purge leads that are not BUYER (if intent_type is set)
    cursor.execute("DELETE FROM leads WHERE intent_type != 'BUYER' AND intent_type != 'UNKNOWN'")
    if cursor.rowcount > 0:
        print(f"Deleted {cursor.rowcount} non-buyer leads based on intent_type.")

    conn.commit()
    conn.close()
    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()
