from fastapi import APIRouter 
from app.services.search_service import search 
from app.services.lead_service import get_leads, get_dashboard_stats 

router = APIRouter() 

@router.get("/success/stats")
async def get_stats():
    return get_dashboard_stats()

@router.post("/search") 
async def run_search(query: str, location: str = "Kenya"): 
    return await search(query, location) 

@router.get("/leads") 
def fetch_leads(limit: int = 20): 
    return get_leads(limit)
