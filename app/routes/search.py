from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from app.services.search_service import search as service_search
from app.config.runtime import PIPELINE_MODE, PROD_RELAXED, PROD_STRICT, INTENT_THRESHOLD, REQUIRE_VERIFICATION, ALLOW_MOCK

router = APIRouter() 

@router.get("/debug-mode") 
def debug_mode(): 
    return { 
        "PROD_STRICT": PROD_STRICT, 
        "REQUIRE_VERIFICATION": REQUIRE_VERIFICATION, 
        "INTENT_THRESHOLD": INTENT_THRESHOLD, 
        "PIPELINE_MODE": PIPELINE_MODE,
        "PROD_RELAXED": PROD_RELAXED,
        "ALLOW_MOCK": ALLOW_MOCK
    } 

@router.post("/search") 
async def search(request: Request, payload: dict, background_tasks: BackgroundTasks): 
    import logging
    logger = logging.getLogger("SearchRoute")
    query = payload.get("query") 
    location = payload.get("location") 
    logger.info(f"SEARCH REQUEST: query='{query}', location='{location}'")

    if not query or not location: 
        logger.warning("Search request missing query or location. Returning empty results.")
        return {
            "results": [],
            "count": 0,
            "total_signals_captured": 0,
            "error": "Query and location are required."
        }

    try:
        # Use new search service
        search_data = await service_search(query, location)
        
        results = search_data.get("results", [])
        metrics = search_data.get("metrics", {})
        rejected = metrics.get("rejected", [])
        
    except Exception as e:
        logger.error(f"CRITICAL PIPELINE ERROR: {e}")
        return {
            "results": [],
            "count": 0,
            "total_signals_captured": 0,
            "error": f"Internal search pipeline error: {str(e)}"
        } 

    # 🎯 DISPLAY LAYER FILTERING (Annotate, Don't Block)
    # We used to filter, now we just annotate for the UI
    min_score = INTENT_THRESHOLD
    
    filtered_results = []
    for r in results:
        # Annotate visibility status
        if r.get("intent_score", 0) >= min_score:
            r["ui_filter_status"] = "shown"
        else:
            r["ui_filter_status"] = "low_confidence"
            
        # We return EVERYTHING now, letting the UI decide how to render
        filtered_results.append(r)
    
    logger.info(f"DISPLAY: Returning {len(filtered_results)} signals (Annotated with min_score={min_score}).")

    response = { 
        "results": filtered_results, 
        "count": len(filtered_results),
        "total_signals_captured": metrics.get("total_found", 0),
        "metrics": metrics,
        "rejected": rejected,
        "status": search_data.get("status", "success")
    } 

    if PIPELINE_MODE != "strict": 
        response["warning"] = "Low-confidence signals shown" 

    return response
