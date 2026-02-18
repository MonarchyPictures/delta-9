from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from app.pipeline.dispatcher import run_pipeline 
from app.config.runtime import PIPELINE_MODE, PROD_RELAXED, PROD_STRICT, INTENT_THRESHOLD, REQUIRE_VERIFICATION, ALLOW_MOCK
from app.intelligence_v2.thresholds import STRICT_PUBLIC

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
        results, rejected, metrics = await run_pipeline( 
            query=query, 
            location=location, 
            headers=request.headers,
            background_tasks=background_tasks,
            tier=1 # ⚡ MANUAL SEARCH IS ALWAYS TIER 1 (FAST)
        ) 
    except Exception as e:
        logger.error(f"CRITICAL PIPELINE ERROR: {e}")
        return {
            "results": [],
            "count": 0,
            "total_signals_captured": 0,
            "error": "Internal search pipeline error. Please check backend logs."
        } 

    # 🎯 DISPLAY LAYER FILTERING (Annotate, Don't Block)
    # We used to filter, now we just annotate for the UI
    min_score = INTENT_THRESHOLD
    
    filtered_results = []
    for r in results:
        # Annotate visibility status
        if r.get("intent_score", 0) >= min_score or r.get("intent_type") == "BUYER":
            r["ui_filter_status"] = "shown"
        else:
            r["ui_filter_status"] = "low_confidence"
            
        # We return EVERYTHING now, letting the UI decide how to render
        filtered_results.append(r)
    
    logger.info(f"DISPLAY: Returning {len(filtered_results)} signals (Annotated with min_score={min_score}).")

    response = { 
        "results": filtered_results, 
        "count": len(filtered_results),
        "total_signals_captured": metrics.get("scraped", len(results)),
        "metrics": metrics
    } 

    if payload.get("debug"):
        response["rejected"] = rejected

    if PIPELINE_MODE != "strict": 
        response["warning"] = "Low-confidence signals shown" 

    return response
