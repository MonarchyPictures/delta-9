from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from app.pipeline.dispatcher import run_pipeline 
from app.config.runtime import PIPELINE_MODE 

router = APIRouter() 

@router.post("/search") 
async def search(request: Request, payload: dict, background_tasks: BackgroundTasks): 
    import logging
    logger = logging.getLogger("SearchRoute")
    query = payload.get("query") 
    location = payload.get("location") 
    logger.info(f"SEARCH REQUEST: query='{query}', location='{location}'")

    if not query or not location: 
        raise HTTPException(400, "query and location required") 

    results = await run_pipeline( 
        query=query, 
        location=location, 
        headers=request.headers,
        background_tasks=background_tasks,
        tier=1 # ⚡ MANUAL SEARCH IS ALWAYS TIER 1 (FAST)
    ) 

    # 🎯 DISPLAY LAYER FILTERING (Save Everything, Rank Later)
    # We filter for UI display but everything is already saved in the DB
    filtered_results = [
        r for r in results 
        if r.get("intent_score", 0) >= 0.60 or r.get("intent_type") == "BUYER"
    ]
    
    logger.info(f"DISPLAY FILTER: Showing {len(filtered_results)} of {len(results)} total signals.")

    response = { 
        "results": filtered_results, 
        "count": len(filtered_results),
        "total_signals_captured": len(results)
    } 

    if PIPELINE_MODE != "strict": 
        response["warning"] = "Low-confidence signals shown" 

    return response
