from collections import defaultdict, deque
from datetime import datetime 
from typing import Optional, Dict, Any
import logging
from app.db.database import SessionLocal
from app.db import models

logger = logging.getLogger(__name__)

# In-memory cache for performance, synced with DB
SCRAPER_METRICS = {}
CATEGORY_STATS = {}

def sync_metrics_from_db():
    """Load metrics from database into memory on startup."""
    db = SessionLocal()
    try:
        # Load Scraper Metrics
        scrapers = db.query(models.ScraperMetric).all()
        for s in scrapers:
            SCRAPER_METRICS[s.scraper_name] = {
                "runs": s.runs,
                "leads": s.leads_found,
                "verified": s.verified_leads,
                "failures": s.failures,
                "consecutive_failures": s.consecutive_failures,
                "last_success": s.last_success,
                "history": deque(s.history or [], maxlen=20)
            }
            
        # Load Category Stats
        categories = db.query(models.CategoryMetric).all()
        for c in categories:
            CATEGORY_STATS[c.category_name] = {
                "leads": c.total_leads,
                "verified": c.verified_leads,
                "verified_rate": c.verified_rate
            }
        logger.info(f"Metrics synced from DB: {len(SCRAPER_METRICS)} scrapers, {len(CATEGORY_STATS)} categories.")
    except Exception as e:
        logger.error(f"Failed to sync metrics from DB: {e}")
    finally:
        db.close()

def record_run(name: str, leads_count: int, error: bool = False):
    """Update metrics for a single scraper run and persist to DB."""
    if name not in SCRAPER_METRICS:
        SCRAPER_METRICS[name] = {
            "runs": 0, "leads": 0, "verified": 0, "failures": 0, 
            "consecutive_failures": 0, "last_success": None, "history": deque(maxlen=20)
        }
        
    metrics = SCRAPER_METRICS[name] 
    metrics["runs"] += 1 
    
    timestamp = datetime.utcnow().isoformat()
    
    if error:
        metrics["failures"] += 1
        metrics["consecutive_failures"] += 1
        metrics["history"].append({
            "timestamp": timestamp, "leads": 0, "verified": 0, "success": False
        })
    else:
        metrics["consecutive_failures"] = 0
        if leads_count > 0: 
            metrics["leads"] += leads_count 
            metrics["last_success"] = datetime.utcnow() 
        metrics["history"].append({
            "timestamp": timestamp, "leads": leads_count, "verified": 0, "success": True
        })

    # Persist to DB
    db = SessionLocal()
    try:
        db_metric = db.query(models.ScraperMetric).filter_by(scraper_name=name).first()
        if not db_metric:
            db_metric = models.ScraperMetric(scraper_name=name)
            db.add(db_metric)
        
        db_metric.runs = metrics["runs"]
        db_metric.leads_found = metrics["leads"]
        db_metric.verified_leads = metrics["verified"]
        db_metric.failures = metrics["failures"]
        db_metric.consecutive_failures = metrics["consecutive_failures"]
        db_metric.last_success = metrics["last_success"]
        db_metric.history = list(metrics["history"])
        db.commit()
    except Exception as e:
        logger.error(f"Failed to persist run metrics for {name}: {e}")
        db.rollback()
    finally:
        db.close()

def record_verified(name: str, verified_count: int = 1):
    """Update metrics for verified leads and persist to DB."""
    if name not in SCRAPER_METRICS: return
    
    metrics = SCRAPER_METRICS[name]
    metrics["verified"] += verified_count
    
    if metrics["history"] and metrics["history"][-1]["success"]:
        metrics["history"][-1]["verified"] += verified_count

    db = SessionLocal()
    try:
        db_metric = db.query(models.ScraperMetric).filter_by(scraper_name=name).first()
        if db_metric:
            db_metric.verified_leads = metrics["verified"]
            db_metric.history = list(metrics["history"])
            db.commit()
    except Exception as e:
        logger.error(f"Failed to persist verified metrics for {name}: {e}")
        db.rollback()
    finally:
        db.close()

def record_category_lead(category: str, is_verified: bool):
    """Track lead success rate per category and persist to DB."""
    if not category: return
    
    if category not in CATEGORY_STATS:
        CATEGORY_STATS[category] = {"leads": 0, "verified": 0, "verified_rate": 0.0}
        
    stats = CATEGORY_STATS[category]
    stats["leads"] += 1
    if is_verified:
        stats["verified"] += 1
    
    if stats["leads"] > 0:
        stats["verified_rate"] = stats["verified"] / stats["leads"]

    db = SessionLocal()
    try:
        db_cat = db.query(models.CategoryMetric).filter_by(category_name=category).first()
        if not db_cat:
            db_cat = models.CategoryMetric(category_name=category)
            db.add(db_cat)
        
        db_cat.total_leads = stats["leads"]
        db_cat.verified_leads = stats["verified"]
        db_cat.verified_rate = stats["verified_rate"]
        db.commit()
    except Exception as e:
        logger.error(f"Failed to persist category metrics for {category}: {e}")
        db.rollback()
    finally:
        db.close()

def get_metrics(name: Optional[str] = None):
    """Return metrics for one or all scrapers."""
    def format_metric(m):
        res = dict(m)
        res["history"] = list(m["history"])
        return res

    if name:
        return format_metric(SCRAPER_METRICS.get(name, {}))
    return {k: format_metric(v) for k, v in SCRAPER_METRICS.items()}

# Initial sync
sync_metrics_from_db()
