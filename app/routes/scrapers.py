from fastapi import APIRouter, Header, HTTPException, Query, Depends, Request
from datetime import datetime
from app.scrapers.registry import SCRAPER_REGISTRY, ACTIVE_SCRAPERS, update_scraper_state, update_scraper_mode, refresh_scraper_states
from app.scrapers.metrics import get_metrics, SCRAPER_METRICS
from app.middleware.auth import require_admin
from app.config.scrapers import is_scraper_allowed
from typing import Optional

router = APIRouter(tags=["Scrapers"]) 

# Removed legacy verify_admin

@router.get("/scrapers") 
def list_scrapers(): 
    """List all scrapers with their current configuration and metrics."""
    try:
        results = []
        for name, scraper_instance in SCRAPER_REGISTRY.items():
            metrics = SCRAPER_METRICS.get(name, {})
            runs = metrics.get("runs", 0)
            failures = metrics.get("failures", 0)
            
            # Calculate dynamic success rate
            success_rate_val = (runs - failures) / runs if runs > 0 else 0
            success_rate_str = f"{int(success_rate_val * 100)}%"
            
            is_active = name in ACTIVE_SCRAPERS
            
            data = {
                "enabled": is_active,
                "core": True,
                "mode": "production",
                "cost": "free",
                "noise": "low",
                "categories": ["general"],
                "metrics": {
                    "leads_found": metrics.get("leads", 0),
                    "success_rate": success_rate_str,
                    "avg_speed": f"{metrics.get('avg_latency', 0.0):.2f}s",
                    "priority_score": round(metrics.get("priority_score", 0.0), 4),
                    "avg_confidence": round(metrics.get("avg_confidence", 0.0), 4),
                    "auto_disabled": metrics.get("auto_disabled", False)
                }
            }
            results.append((name, data))
        
        # Sort by priority score for live ranking visibility
        results.sort(key=lambda x: x[1]["metrics"]["priority_score"], reverse=True)
        
        return dict(results)
    except Exception as e:
        return {"error": f"Failed to list scrapers: {str(e)}", "registry_size": len(SCRAPER_REGISTRY)}

@router.get("/scrapers/status")
def get_scraper_status(request: Request, role: str = Depends(require_admin)):
    """Detailed status for admin dashboard."""
    try:
        refresh_scraper_states()
        now = datetime.utcnow()
        
        # Mapping for category check
        mapping = {
            "FacebookMarketplaceScraper": "facebook",
            "TwitterScraper": "twitter",
            "RedditScraper": "reddit",
            "GoogleMapsScraper": "google"
        }
        
        return {
            name: {
                "enabled": name in ACTIVE_SCRAPERS, 
                "core": True,
                "mode": "production",
                "cost": "free",
                "category": "vehicles" if is_scraper_allowed(mapping.get(name, "unknown")) else "other",
                "enabled_until": None,
                "ttl_remaining": None,
                "metrics": get_metrics(name)
            } for name, _ in SCRAPER_REGISTRY.items()
        }
    except Exception as e:
        return {"error": f"Failed to get scraper status: {str(e)}"}

@router.post("/scrapers/{name}/promote")
def promote_scraper(request: Request, name: str, role: str = Depends(require_admin)):
    """Promote a scraper from sandbox to production."""
    success, message = update_scraper_mode(name, "production", caller=f"User({role})")
    if not success:
        return {"status": "error", "message": message}
    return {"status": "success", "scraper": name, "mode": "production"}

@router.post("/scrapers/{name}/enable") 
def enable_scraper(
    request: Request,
    name: str, 
    ttl: Optional[int] = Query(None, description="TTL in minutes"),
    role: str = Depends(require_admin)
): 
    success, message = update_scraper_state(name, True, ttl_minutes=ttl, caller=f"User({role})")
    if not success:
        return {"status": "error", "message": message}
        
    return {"status": "enabled", "scraper": name, "ttl": ttl} 

@router.post("/scrapers/{name}/disable") 
def disable_scraper(request: Request, name: str, role: str = Depends(require_admin)): 
    success, message = update_scraper_state(name, False, caller=f"User({role})")
    if not success:
        return {"status": "error", "message": message}
        
    return {"status": "disabled", "scraper": name}

@router.post("/scrapers/{name}/mode")
def set_scraper_mode(request: Request, name: str, mode: str, role: str = Depends(require_admin)):
    """Update scraper mode (production/sandbox)."""
    success, message = update_scraper_mode(name, mode, caller=f"User({role})")
    if not success:
        return {"status": "error", "message": message}
    return {"status": "success", "scraper": name, "mode": mode}

@router.post("/scrapers/toggle")
def toggle_scraper_generic(request: Request, name: str, enabled: bool, role: str = Depends(require_admin)):
    """
    🔐 Standardized toggle endpoint.
    Snippet requested: Use on /scrapers/toggle
    """
    success, message = update_scraper_state(name, enabled, caller=f"User({role})")
    if not success:
        return {"status": "error", "message": message}
    return {"status": "success", "scraper": name, "enabled": enabled}

@router.get("/scrapers/metrics")
def get_all_metrics(request: Request, role: str = Depends(require_admin)):
    return get_metrics()

@router.get("/health/scrapers") 
def scraper_health(): 
    return {"status": "ok", "message": "Scraper health check endpoint is active"}
