from fastapi import APIRouter, Header, HTTPException, Query, Depends
from app.scrapers.registry import SCRAPER_REGISTRY, update_scraper_state, update_scraper_mode
from app.scrapers.metrics import get_metrics, SCRAPER_METRICS
from app.middleware.auth import require_admin
from typing import Optional

router = APIRouter(tags=["Scrapers"]) 

# Removed legacy verify_admin

@router.get("/scrapers") 
def list_scrapers(): 
    """List all scrapers with their current configuration and metrics."""
    return { 
        name: { 
            **meta, 
            "metrics": SCRAPER_METRICS.get(name, {}) 
        } 
        for name, meta in SCRAPER_REGISTRY.items() 
    } 

@router.get("/scrapers/status")
def get_scraper_status(request: Request, role: str = Depends(require_admin)):
    """Detailed status for admin dashboard."""
    refresh_scraper_states()
    now = datetime.utcnow()
    
    return {
        name: {
            "enabled": config["enabled"], 
            "core": config["core"],
            "mode": config.get("mode", "production"),
            "cost": config.get("cost", "free"),
            "enabled_until": config.get("enabled_until").isoformat() if config.get("enabled_until") else None,
            "ttl_remaining": max(0, int((config.get("enabled_until") - now).total_seconds())) if config.get("enabled_until") else None,
            "metrics": get_metrics(name)
        } for name, config in SCRAPER_REGISTRY.items()
    }

@router.post("/scrapers/{name}/promote")
def promote_scraper(request: Request, name: str, role: str = Depends(require_admin)):
    """Promote a scraper from sandbox to production."""
    success, message = update_scraper_mode(name, "production", caller=f"User({role})")
    if not success:
        raise HTTPException(400, message)
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
        raise HTTPException(400, message)
        
    return {"status": "enabled", "scraper": name, "ttl": ttl} 

@router.post("/scrapers/{name}/disable") 
def disable_scraper(request: Request, name: str, role: str = Depends(require_admin)): 
    success, message = update_scraper_state(name, False, caller=f"User({role})")
    if not success:
        raise HTTPException(400, message)
        
    return {"status": "disabled", "scraper": name}

@router.post("/scrapers/{name}/mode")
def set_scraper_mode(request: Request, name: str, mode: str, role: str = Depends(require_admin)):
    """Update scraper mode (production/sandbox)."""
    success, message = update_scraper_mode(name, mode, caller=f"User({role})")
    if not success:
        raise HTTPException(400, message)
    return {"status": "success", "scraper": name, "mode": mode}

@router.post("/scrapers/toggle")
def toggle_scraper_generic(request: Request, name: str, enabled: bool, role: str = Depends(require_admin)):
    """
    🔐 Standardized toggle endpoint.
    Snippet requested: Use on /scrapers/toggle
    """
    success, message = update_scraper_state(name, enabled, caller=f"User({role})")
    if not success:
        raise HTTPException(400, message)
    return {"status": "success", "scraper": name, "enabled": enabled}

@router.get("/scrapers/metrics")
def get_all_metrics(request: Request, role: str = Depends(require_admin)):
    return get_metrics()

@router.get("/health/scrapers") 
def scraper_health(): 
    return {"status": "ok", "message": "Scraper health check endpoint is active"}
