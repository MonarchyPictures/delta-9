
from app.db.database import SessionLocal
from app.db import models

def check_leads():
    db = SessionLocal()
    count = db.query(models.Lead).count()
    print(f"Total leads in database: {count}")
    
    if count > 0:
        latest = db.query(models.Lead).order_by(models.Lead.created_at.desc()).first()
        print(f"Latest lead: {latest.buyer_request_snippet[:100]} from {latest.source_platform}")
        print(f"Link: {latest.post_link}")
        print(f"Created At: {latest.created_at}")
        
        print("\nAll platforms in DB:")
        platforms = db.query(models.Lead.source_platform).distinct().all()
        for p in platforms:
            p_count = db.query(models.Lead).filter(models.Lead.source_platform == p[0]).count()
            print(f" - {p[0]}: {p_count}")
    
    db.close()

if __name__ == "__main__":
    check_leads()
