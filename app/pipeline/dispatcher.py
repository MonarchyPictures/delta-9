import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.ingestion import LiveLeadIngestor
from app.intelligence.expand import expand_query
from app.config import PIPELINE_MODE

logger = logging.getLogger(__name__)

def run_background_discovery(query: str, location: str, tier: int = 2):
    """
    🛠️ Background Task: Continues discovery for the remaining queries 
    to populate cache and metrics after an early return.
    Default to Tier 2 (Full) to ensure deep data is captured eventually.
    """
    logger.info(f"BACKGROUND DISCOVERY: Starting full pass (Tier {tier}) for '{query}' in {location}")
    db = SessionLocal()
    try:
        ingestor = LiveLeadIngestor(db)
        # Run with early_return=False to ensure full coverage in background
        leads = ingestor.fetch_from_external_sources(query, location, early_return=False, tier=tier)
        if leads:
            logger.info(f"BACKGROUND DISCOVERY: Saving {len(leads)} leads for '{query}'")
            ingestor.save_leads_to_db(leads)
        logger.info(f"BACKGROUND DISCOVERY: Completed for '{query}'")
    except Exception as e:
        logger.error(f"BACKGROUND DISCOVERY ERROR: {str(e)}")
    finally:
        db.close()

async def run_pipeline(query: str, location: str, headers: Dict[str, Any] = None, background_tasks: BackgroundTasks = None, tier: int = 2) -> List[Dict[str, Any]]:
    """
    🎯 The Engine: Generic pipeline dispatcher.
    Expands query, fetches leads, scores them, and returns verified buyers.
    Includes Early Return logic for instant UX.
    
    tier=1: Fast (API-based) - 5 sec max return
    tier=2: Full (API + Playwright)
    """
    start_time = time.time()
    db = SessionLocal()
    try:
        # 1. Expand Query (Generic expansion)
        expanded_queries = expand_query(query)
        logger.info(f"PIPELINE: Expanding '{query}' -> {expanded_queries} (Tier {tier})")

        ingestor = LiveLeadIngestor(db)
        all_results = []

        # 2. Run enabled scrapers for the primary query first (Speed Optimized)
        # We use early_return=True to return as soon as we have >= 2 signals
        # CRITICAL: Run blocking ingestion in thread to avoid blocking async loop
        primary_leads = await asyncio.to_thread(
            ingestor.fetch_from_external_sources, 
            query, 
            location, 
            early_return=True, 
            tier=tier
        )
        all_results.extend(primary_leads)

        # 🚀 EARLY RETURN CHECK: If we found enough signals from the primary query, 
        # return immediately and move the expanded queries AND the full pass of the primary query to background.
        if len(primary_leads) >= 2:
            logger.info(f"PIPELINE SPEED: Early return triggered with {len(primary_leads)} signals.")
            if background_tasks:
                # 1. Complete the full pass for the primary query in background (Always Tier 2 for deep data)
                background_tasks.add_task(run_background_discovery, query, location, tier=2)
                # 2. Complete expanded queries in background
                for eq in expanded_queries:
                    if eq != query:
                        background_tasks.add_task(run_background_discovery, eq, location, tier=2)
        else:
            # 3. Fallback: Run expanded queries sequentially if primary query was dry
            for q in expanded_queries:
                if q == query: continue # Already did this
                normalized_query = q.strip()
                leads = await asyncio.to_thread(
                    ingestor.fetch_from_external_sources, 
                    normalized_query, 
                    location, 
                    early_return=True, 
                    tier=tier
                )
                all_results.extend(leads)
                if len(all_results) >= 2:
                    break

        # 3. Final De-duplication (by source_url or text hash if URL missing)
        unique_results = {}
        
        # 🛠️ DEBUG: Check all_results content type
        if all_results:
            logger.info(f"DEBUG: all_results type: {type(all_results)}")
            logger.info(f"DEBUG: First item type: {type(all_results[0])}")
            if isinstance(all_results[0], list):
                logger.error("CRITICAL: all_results contains lists! Flattening...")
                # Flatten if accidentally nested
                flat = []
                for sublist in all_results:
                    if isinstance(sublist, list):
                        flat.extend(sublist)
                    else:
                        flat.append(sublist)
                all_results = flat

        for lead in all_results:
            # Use URL as primary key, fall back to text hash for URL-less signals
            if isinstance(lead, list):
                logger.error(f"SKIPPING LIST ITEM IN LOOP: {lead}")
                continue
            
            if not isinstance(lead, dict):
                logger.error(f"SKIPPING NON-DICT ITEM ({type(lead)}): {lead}")
                continue
                
            url = lead.get('source_url')
            if not url:
                # Fallback key: Phone + Snippet hash
                phone = lead.get('contact_phone') or ""
                text = lead.get('buyer_request_snippet') or ""
                url = f"signal://{phone}:{hash(text)}"
            
            if url not in unique_results:
                unique_results[url] = lead
            else:
                # Keep the one with higher intent score if duplicates exist
                if lead.get('intent_score', 0) > unique_results[url].get('intent_score', 0):
                    unique_results[url] = lead

        final_leads = list(unique_results.values())
        
        from app.scrapers.metrics import SCRAPER_METRICS

        # 4. Sort by weighted intent score (intent_score * priority_boost)
        def get_weighted_score(lead):
            if not isinstance(lead, dict):
                return 0
            base_score = lead.get('intent_score', 0)
            scraper_name = lead.get('_scraper_name')
            boost = 1.0
            
            # if scraper_name and scraper_name in SCRAPER_METRICS:
            #     try:
            #         metric_data = SCRAPER_METRICS[scraper_name]
            #         if isinstance(metric_data, dict):
            #             boost = metric_data.get('priority_boost', 1.0)
            #         else:
            #             logger.warning(f"DEBUG: SCRAPER_METRICS[{scraper_name}] is not a dict: {type(metric_data)}")
            #     except Exception as e:
            #         logger.error(f"DEBUG: Error accessing SCRAPER_METRICS[{scraper_name}]: {e}")
            boost = 1.0
                    
            return base_score * boost

        final_leads.sort(key=get_weighted_score, reverse=True)

        duration = time.time() - start_time
        logger.info(f"PIPELINE COMPLETE: Found {len(final_leads)} leads for '{query}' in {duration:.2f}s")
        
        # 🛠️ DEBUG METRICS
        metrics = {
            "scraped": len(final_leads) + len(getattr(ingestor, 'rejected_leads', [])),
            "passed": len(final_leads),
            "rejected": len(getattr(ingestor, 'rejected_leads', []))
        }

        return final_leads, getattr(ingestor, 'rejected_leads', []), metrics

    except Exception as e:
        logger.exception(f"PIPELINE ERROR: {str(e)}")
        return [], [], {"error": str(e)}
    finally:
        db.close()
