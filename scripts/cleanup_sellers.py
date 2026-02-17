import sqlite3
import os

def cleanup_db():
    db_path = "intent_radar.db"
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Delete leads marked as SELLER or UNCLEAR
    cursor.execute("DELETE FROM leads WHERE intent_type IN ('SELLER', 'UNCLEAR', 'UNKNOWN')")
    print(f"Deleted {cursor.rowcount} leads with non-buyer intent type.")

    # 2. Delete leads with seller keywords in snippet even if marked as BUYER (extra safety)
    seller_keywords = [
        "for sale", "selling", "available", "price", "discount", "offer", 
        "promo", "delivery", "in stock", "we sell", "shop", "dealer", 
        "supplier", "warehouse", "order now", "dm for price", 
        "call / whatsapp", "our store", "brand new", "limited stock",
        "flash sale", "retail price", "wholesale", "best price",
        "check out", "visit us", "located at", "we deliver", "buy from us",
        "contact for price", "special offer", "new arrival", "stockist",
        "dm to order", "shipping available", "price is", "kwa bei ya",
        "tunauza", "mzigo mpya", "punguzo", "call me for", "contact me for",
        "brand new", "imported", "affordable", "wholesale price", "retail",
        "visit our shop", "we are located", "delivery available", "countrywide",
        "pay on delivery", "lipa baada ya", "mzigo umefika", "bei nafuu",
        "tuko na", "pata yako", "agiza sasa"
    ]
    
    deleted_count = 0
    for kw in seller_keywords:
        cursor.execute("DELETE FROM leads WHERE buyer_request_snippet LIKE ?", (f"%{kw}%",))
        deleted_count += cursor.rowcount

    print(f"Deleted {deleted_count} additional leads containing seller keywords.")

    conn.commit()
    conn.close()
    print("Database cleanup complete.")

if __name__ == "__main__":
    cleanup_db()
