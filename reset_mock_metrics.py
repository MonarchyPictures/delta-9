
from app.db.database import SessionLocal
from app.db import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResetMetrics")

def reset_mock_scraper_metrics():
    db = SessionLocal()
    try:
        scraper = db.query(models.ScraperMetric).filter(models.ScraperMetric.scraper_name == "MockScraper").first()
        if scraper:
            logger.info(f"Found MockScraper metrics. auto_disabled={scraper.auto_disabled}")
            scraper.auto_disabled = False
            scraper.consecutive_failures = 0
            scraper.failures = 0
            db.commit()
            logger.info("MockScraper metrics reset successfully.")
            
            # Verify persistence
            db.refresh(scraper)
            logger.info(f"VERIFY: auto_disabled after commit: {scraper.auto_disabled}")
        else:
            logger.info("MockScraper metrics not found in DB.")
            
            # Create if not exists to be safe
            new_scraper = models.ScraperMetric(
                scraper_name="MockScraper",
                auto_disabled=False,
                consecutive_failures=0,
                failures=0,
                runs=0,
                leads_found=0
            )
            db.add(new_scraper)
            db.commit()
            logger.info("Created fresh MockScraper metrics.")
            
    except Exception as e:
        logger.error(f"Error resetting metrics: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_mock_scraper_metrics()
