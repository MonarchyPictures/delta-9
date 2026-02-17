import os
import uuid
import time
import random
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .utils.logging import get_logger
from sqlalchemy.orm import Session
from .scrapers.base_scraper import BaseScraper
from .scrapers.google_scraper import GoogleScraper
from .scrapers.facebook_marketplace import FacebookMarketplaceScraper
from .scrapers.duckduckgo import DuckDuckGoScraper
from .scrapers.serpapi_scraper import SerpApiScraper
from .scrapers.classifieds import ClassifiedsScraper
from .scrapers.twitter import TwitterScraper
from .scrapers.google_maps import GoogleMapsScraper
from .scrapers.reddit import RedditScraper
from .scrapers.google_cse import GoogleCSEScraper
from .scrapers.whatsapp_public_groups import WhatsAppPublicGroupScraper
from .scrapers.instagram import InstagramScraper
from .config import PROD_STRICT
from .intelligence.confidence import apply_confidence
from .cache.scraper_cache import get_cached, set_cached
from .scrapers.registry import SCRAPER_REGISTRY, update_scraper_state, get_active_scrapers
from .scrapers.selector import decide_scrapers
from .scrapers.metrics import record_run, SCRAPER_METRICS, get_scraper_performance_score
from .scrapers.supervisor import check_scraper_health, reset_consecutive_failures
from .scrapers.verifier import is_verified_signal, verify_leads
from .intelligence.intent import buyer_intent_score
from .intelligence.buyer_classifier import classify_post
from .utils.deduplication import get_deduplicator
from .utils.geo_bias import apply_geo_bias
from .intelligence.query_expander import get_expanded_queries
from .nlp.dedupe import dedupe_leads

# 🚀 GLOBAL THREAD POOL: Reuse threads to prevent resource exhaustion (Playwright is heavy!)
# Limit to 5 concurrent scrapers to keep the server stable.
SCRAPER_EXECUTOR = ThreadPoolExecutor(max_workers=5)

def ingest_leads(raw_results: List[Dict[str, Any]]) -> List[Any]:
    """
    Takes raw scraper results, processes them (NLP dedupe, strict filtering, metadata),
    and returns a list of verified Lead objects.
    """
    if not raw_results:
        return []

    logger.info(f"INGEST: Processing {len(raw_results)} raw signals...")

    # 1. NLP Deduplication
    # Group similar leads to avoid duplicates
    unique_results, rejected = dedupe_leads(raw_results)
    logger.info(f"INGEST: Deduplicated to {len(unique_results)} unique signals")

    # 2. Strict Filtering & Metadata (using Pipeline logic if possible, or reimplementing)
    # We need to convert these dicts to Lead objects.
    # We can use LeadPipeline for this conversion and validation.
    
    # Since we need a DB session for LeadPipeline, we might need to handle it here 
    # or assume the caller handles saving.
    # The user signature is `ingest_leads(raw_results) -> verified_leads`
    # It doesn't take a session.
    # But to create Lead objects and check existence, we might need DB.
    # However, the user says "Returns a list of Lead objects ready to save".
    # This implies they are not saved yet.
    
    from app.db.database import SessionLocal
    from app.services.pipeline import LeadPipeline
    
    verified_leads = []
    db = SessionLocal()
    try:
        pipeline = LeadPipeline(db)
        for res in unique_results:
            # Pipeline's process_raw_lead handles:
            # - Intent Validation
            # - Scoring & Readiness
            # - Extraction (Phone, Name)
            # - Normalization
            # - Existence Check (against DB)
            lead = pipeline.process_raw_lead(res)
            if lead:
                verified_leads.append(lead)
    finally:
        db.close()

    logger.info(f"INGEST: Produced {len(verified_leads)} verified leads ready for storage")
    return verified_leads


from .scrapers.mock_scraper import MockScraper

# ALL possible scrapers available in the system
ALL_SCRAPERS = [ 
    MockScraper(),
    GoogleMapsScraper(), 
    ClassifiedsScraper(), 
    FacebookMarketplaceScraper(), 
    TwitterScraper(), 
    RedditScraper(),
    GoogleCSEScraper(),
    DuckDuckGoScraper(),
    GoogleScraper(),
    WhatsAppPublicGroupScraper(),
    InstagramScraper()
]

# ABSOLUTE RULE: PROD STRICT ENFORCEMENT
logger = get_logger("Ingestion")

# ⚡ TIER 1: FAST (API / Lightweight) - 5 sec max return
TIER_1_SCRAPERS = [
    "MockScraper",
    "GoogleCSEScraper", 
    "DuckDuckGoScraper", 
    "RedditScraper" # Usually fast via DDG site search
]

# 🐢 TIER 2: HEAVY (Playwright) - Full deep scrape
TIER_2_SCRAPERS = [
    "InstagramScraper",
    "GoogleMapsScraper",
    "FacebookMarketplaceScraper",
    "ClassifiedsScraper",
    "WhatsAppPublicGroupScraper",
    "TwitterScraper"
]

class LiveLeadIngestor:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.rejected_leads = [] # 🛠️ DEBUG: Capture rejected leads
        
        # Enforce production check immediately if initialized for live fetching
        if not PROD_STRICT:
            logger.warning("--- WARNING: Delta9 running in DEVELOPMENT mode. Auto-downgrading to bootstrap. ---")

    async def check_network_health(self) -> bool:
        """Verify network connectivity and proxy health before ingestion."""
        import asyncio
        logger.info("NETWORK CHECK: Verifying outbound connectivity...")
        try:
            # Check multiple reliable endpoints with significantly longer timeout for high-latency environments
            endpoints = [
                "https://www.google.com", 
                "https://8.8.8.8", 
                "https://duckduckgo.com",
                "https://www.facebook.com"
            ]
            
            # Run checks in PARALLEL to avoid blocking async loop for too long
            # Using asyncio.gather to check all at once
            async def check_url(url):
                try:
                    # Increase timeout to 20s to handle Kenyan mobile network latency
                    response = await asyncio.to_thread(requests.get, url, timeout=20)
                    if response.status_code == 200 or response.status_code == 301 or response.status_code == 302:
                        logger.info(f"NETWORK CHECK: Connectivity verified via {url} (HTTP {response.status_code})")
                        return True
                except Exception as e:
                    logger.warning(f"NETWORK CHECK: {url} unreachable: {str(e)}")
                    return False
                return False

            results = await asyncio.gather(*(check_url(url) for url in endpoints))
            
            if any(results):
                return True
            
            logger.error("NETWORK CHECK FAILED: All endpoints timed out or failed.")
            return False
        except Exception as e:
            logger.error(f"NETWORK CHECK FAILED: {str(e)}")
            return False

    def _generate_whatsapp_link(self, phone: str, product: str) -> str:
        """Generate a pre-filled WhatsApp link for the lead."""
        if not phone:
            return None
        # Ensure phone is in format 2547XXXXXXXX
        clean_phone = phone.replace('+', '')
        message = f"Hello, I saw your request for {product}. I can help you with that!"
        import urllib.parse
        encoded_message = urllib.parse.quote(message)
        return f"https://wa.me/{clean_phone}?text={encoded_message}"

    def _extract_phone(self, text: str) -> str:
        """Extract phone numbers using global regex."""
        if not text:
            return None
        import re
        # Generic global phone regex
        phone_pattern = r'(\+?\d{1,4}[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})'
        match = re.search(phone_pattern, text)
        if match:
            return match.group(0)
        return None

    def _extract_name(self, text: str, source_platform: str) -> str:
        """Attempt to extract name from public content."""
        if not text:
            return "Verified Market Signal"
        
        # Simple extraction for known patterns
        import re
        name_patterns = [
            r"Post by\s+([A-Z][a-z]*\s+[A-Z][a-z]*)",
            r"Contact:\s+([A-Z][a-z]*\s+[A-Z][a-z]*)",
            r"Name:\s+([A-Z][a-z]*\s+[A-Z][a-z]*)",
            r"^([A-Z][a-z]*\s+[A-Z][a-z]*)\s+is looking for",
            r"([A-Z][a-z]*\s+[A-Z][a-z]*)\s+on\s+(Facebook|Twitter|LinkedIn|Jiji|Pigiame)",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return "Verified Market Signal"

    def _parse_urgency(self, text: str) -> str:
        """Determine urgency level based on keywords."""
        text = text.lower()
        high_urgency = ["asap", "urgently", "urgent", "immediately", "now", "today", "ready to pay", "fast", "needed urgently", "emergency"]
        medium_urgency = ["soon", "this week", "budget", "looking for", "price of", "how much"]
        
        if any(kw in text for kw in high_urgency):
            return "high"
        if any(kw in text for kw in medium_urgency):
            return "medium"
        return "low"

    def _verify_timestamp_strict(self, text: str) -> (bool, int):
        """
        CRITICAL: Include ONLY posts/messages created in the last 120 minutes for strict mode.
        Returns (is_verified, minutes_ago).
        """
        text = text.lower()
        
        # Check for our injected SerpApi date format [Date]
        import re
        date_match = re.search(r'\[(.*?)\]', text)
        if date_match:
            date_str = date_match.group(1).lower()
            # If date_str is something like "2 hours ago", "1 min ago", etc.
            # handled by the markers below
            text = date_str # Use this for marker matching
        
        # Mapping markers to approximate minutes
        markers = {
            "just now": 1,
            "1 min ago": 1,
            "1 minute ago": 1,
            "2 mins ago": 2,
            "2 minutes ago": 2,
            "3 mins ago": 3,
            "5 mins ago": 5,
            "10 mins ago": 10,
            "15 mins ago": 15,
            "20 mins ago": 20,
            "30 mins ago": 30,
            "40 mins ago": 40,
            "45 mins ago": 45,
            "50 mins ago": 50,
            "1h ago": 60,
            "1 hour ago": 60,
            "2h ago": 120,
            "2 hours ago": 120,
            "3h ago": 180,
            "4h ago": 240,
            "6h ago": 360,
            "12h ago": 720,
            "24h ago": 1440,
            "1d ago": 1440,
            "yesterday": 1440,
        }
        
        # Regex for generic "X mins ago", "X hours ago", "X days ago"
        # Minutes
        min_match = re.search(r'(\d+)\s*(min|minute)s?\s*ago', text)
        if min_match:
            return True, int(min_match.group(1))
            
        # Hours
        hr_match = re.search(r'(\d+)\s*(hr|hour)s?\s*ago', text)
        if hr_match:
            return True, int(hr_match.group(1)) * 60
            
        # Days
        day_match = re.search(r'(\d+)\s*(day|d)s?\s*ago', text)
        if day_match:
            return True, int(day_match.group(1)) * 1440
        
        for marker, mins in markers.items():
            if marker in text:
                return True, mins
        
        # Fallback for specific date formats if possible, or return False
        return False, 0

    def fetch_from_external_sources(self, query: str, location: str, time_window_hours: int = 2, category: Optional[str] = "general", last_result_count: int = 0, early_return: bool = True, tier: int = 2) -> List[Dict[str, Any]]:
        """
        Fetch live leads using MULTI-PASS DISCOVERY (3 PASSES).
        Includes AUTO TIME WINDOW ESCALATION (2h -> 6h -> 24h).
        
        tier=1: Fast (API-based) - 5 sec max return
        tier=2: Full (API + Playwright)
        """
        # ⏱️ ESCALATION STRATEGY: 2h -> 6h -> 24h
        # If strict mode returns 0 leads, we automatically expand the search window.
        windows = [2, 6, 24]
        
        all_found_leads = []
        for current_window in windows:
            logger.info(f"FETCH: Trying window {current_window}h for '{query}' in {location} (Tier {tier})")
            leads = self._execute_discovery(query, location, current_window, category, last_result_count, early_return=early_return, tier=tier)
            
            if leads:
                # Tag leads with the window they were found in
                for l in leads:
                    l["discovery_window"] = f"{current_window}h"
                
                all_found_leads.extend(leads)
                
                # 🎯 ESCALATION RULE: If we found signals, we stop expanding.
                # This prevents "No Signals Detected" by escalating only when empty.
                logger.info(f"ESCALATION SUCCESS: Found {len(leads)} signals in {current_window}h window.")
                break
            
            logger.warning(f"ESCALATION: No signals in {current_window}h. Expanding search...")

        # Final de-duplication across all passes (though we broke early, we still dedupe)
        if not all_found_leads:
            logger.error(f"ESCALATION FAILED: Zero signals found even after 24h search for '{query}'")
            return []

        # Use deduplicator to clean up any overlap
        deduper = get_deduplicator()
        return deduper.deduplicate(all_found_leads)

    def _execute_discovery(self, query: str, location: str, time_window_hours: int, category: Optional[str] = "general", last_result_count: int = 0, early_return: bool = True, tier: int = 2) -> List[Dict[str, Any]]:
        """Internal discovery execution with PARALLEL scraping and early return."""
        # ABSOLUTE RULE: Mandatory health check
        if not self.check_network_health():
            if PROD_STRICT:
                logger.error("NETWORK CHECK FAILED: Ingestion proceeding cautiously despite network issues (Soft Fail).")
                # raise RuntimeError("ERROR: Network health check failed. Ingestion blocked to prevent stale data.")
            else:
                logger.warning("NETWORK CHECK FAILED: Continuing anyway because PROD_STRICT=False")

        # 🧠 AI QUERY EXPANSION: Expand product query into related terms
        expanded_queries = get_expanded_queries(query)
        logger.info(f"AI EXPANSION: Discovery broadened to {expanded_queries}")

        # --- Adaptive Scraper Control ---
        enabled_sources = decide_scrapers(
            query=query, 
            location=location, 
            category=category,
            time_window_hours=time_window_hours, 
            is_prod=PROD_STRICT,
            last_result_count=last_result_count
        )
        logger.info(f"DEBUG: decide_scrapers returned: {enabled_sources}")
        
        # 📈 PERFORMANCE RANKING: Sort scrapers by priority_score (Higher = First)
        logger.info(f"DEBUG: ALL_SCRAPERS keys: {[s.__class__.__name__ for s in ALL_SCRAPERS]}")
        enabled_scrapers = [ 
            s for s in ALL_SCRAPERS 
            if s.__class__.__name__ in enabled_sources and not s.auto_disabled
        ]
        logger.info(f"DEBUG: enabled_scrapers after filtering: {[s.__class__.__name__ for s in enabled_scrapers]}")
        
        # ⚡ TIER FILTERING
        if tier == 1:
            logger.info("TIER 1 MODE: Filtering for fast API scrapers only.")
            enabled_scrapers = [s for s in enabled_scrapers if s.__class__.__name__ in TIER_1_SCRAPERS]
        
        logger.info(f"DEBUG: enabled_scrapers after tier filtering: {[s.__class__.__name__ for s in enabled_scrapers]}")

        active_scrapers = sorted( 
            enabled_scrapers, 
            key=lambda s: s.priority_score or 0, 
            reverse=True 
        )
        
        logger.info(f"AI Decision (Ranked): {[(s.__class__.__name__, round(s.priority_score, 2)) for s in active_scrapers]}")

        # Check specifically for MockScraper
        mock_in_active = any(isinstance(s, MockScraper) for s in active_scrapers)
        if mock_in_active:
            logger.info("CONFIRMED: MockScraper is in active_scrapers list.")
        else:
            logger.warning("WARNING: MockScraper is NOT in active_scrapers list.")

        discovery_templates = [
            # Pass 1: Direct buyer intent
            [
                '"{query}" (looking to buy OR "want to buy" OR "need supplier") "{location}"',
                '"{query}" (buying OR need OR "urgent need") "{location}"',
            ],
            # Pass 2: Conversational discovery
            [
                '"{query}" ("where can i buy" OR "anyone selling" OR "who has") "{location}"',
                '"{query}" ("price of" OR "cost of" OR "how much is") "{location}"',
            ],
            # Pass 3: Sourcing & Vendors
            [
                '"{query}" ("where to find" OR "supply of" OR "quote for") "{location}"',
                '"{query}" ("can i get" OR "searching for") "{location}"',
            ]
        ]
        
        all_leads = []
        collected_high_confidence = 0
        
        for pass_idx, templates in enumerate(discovery_templates):
            logger.info(f"PASS {pass_idx + 1}/{len(discovery_templates)}: Starting ranked discovery...")
            
            # 🧠 AI BROADENING: Generate queries for each expanded product term
            pass_queries = []
            for expanded_q in expanded_queries:
                for template in templates:
                    pass_queries.append(template.format(query=expanded_q, location=location))
            
            # 🎯 ELITE DISPATCH: Run scrapers sequentially by rank and check for early termination
            for scraper in active_scrapers:
                scraper_name = scraper.__class__.__name__
                logger.info(f"DISPATCH: Running {scraper_name} (Ranked) for Pass {pass_idx+1}...")
                
                # Run this scraper for the current pass queries
                scraper_leads = self._run_parallel_scrapers([scraper], pass_queries, time_window_hours, query, location, early_return=early_return, tier=tier)
                
                logger.info(f"DEBUG: {scraper_name} returned {len(scraper_leads)} raw leads")
                
                # 🇰🇪 GEO BOOST: Prioritize Kenyan hubs before quality checks
                scraper_leads = apply_geo_bias(scraper_leads)
                
                all_leads.extend(scraper_leads)
                
                # 🚀 EARLY TERMINATION: Check for high-confidence leads (>= 0.85)
                high_quality = [ 
                    l for l in scraper_leads 
                    if l.get("intent_score", 0) >= 0.85 
                ]
                collected_high_confidence += len(high_quality)
                
                if collected_high_confidence >= 5:
                    logger.info(f"🎯 ELITE EXIT: Found {collected_high_confidence} high-confidence leads. Terminating all further discovery.")
                    break
            
            # Break the pass loop as well if we hit the limit
            if collected_high_confidence >= 5:
                break
    
        # 🎯 SMART DEDUPLICATION (NLP Semantic + Phone + URL)
        # Phase 1: NLP Semantic Deduplication (New Layer)
        all_leads, rejected_nlp = dedupe_leads(all_leads)
        if hasattr(self, 'rejected_leads'):
            self.rejected_leads.extend(rejected_nlp)
        
        # Phase 2: Basic Deduplication (Legacy/Fallback)
        deduper = get_deduplicator()
        unique_leads = deduper.deduplicate(all_leads)
        
        # 🎯 RANK EVERYTHING FIRST
        sorted_leads = sorted(unique_leads, key=lambda x: x["intent_score"], reverse=True)
        
        # ℹ️ Metadata-only filtering in storage layer (Replaces hard skip)
        # We return everything to fulfill "Save Everything, Rank Later"
        # The display layer (frontend or search route) will handle strict visibility.
        logger.info(f"STORAGE: Returning {len(sorted_leads)} leads for processing (Save Everything mode).")
        return sorted_leads

    def _run_parallel_scrapers(self, scrapers: List[BaseScraper], queries: List[str], time_window_hours: int, original_query: str, location: str, early_return: bool = False, tier: int = 2) -> List[Dict[str, Any]]:
        """Helper to run a set of scrapers in parallel with hard timeout and early return."""
        import time
        import uuid
        import random
        from datetime import datetime, timedelta, timezone
        from concurrent.futures import as_completed
        
        results_leads = []
        verified_count = 0
        
        # ⏱️ TIMEOUT CONTROL:
        # Tier 1 (Manual Search): Strict 5s timeout per scraper to ensure speed.
        # Tier 2 (Agent/Background): Relaxed 25s timeout for heavy scraping (Playwright).
        HARD_TIMEOUT = 5 if tier == 1 else 25
        
        EARLY_RETURN_THRESHOLD = 2 # 🚀 Speed Guard: Return if >= 2 high-confidence signals found
        
        # 🚀 Use GLOBAL EXECUTOR to prevent resource exhaustion
        global SCRAPER_EXECUTOR
        
        future_to_query = {}
        
        def scrape_with_cache(s, q, w):
            scraper_name = s.__class__.__name__
            cache_key = f"{scraper_name}:{q}:{w}"
            cached = get_cached(cache_key)
            if cached is not None:
                logger.info(f"CACHE: Hit for {cache_key}")
                return cached
            
            start_time = time.time()
            try:
                # Apply 10s timeout to the scraper.scrape call
                res = s.scrape(q, time_window_hours=w)

                # 🛠️ RAW CAPTURE LOGGING (Phase 3)
                if res:
                    try:
                        os.makedirs("logs", exist_ok=True)
                        with open("logs/raw_capture.log", "a", encoding="utf-8") as f:
                            for item in res:
                                url_log = item.get('url', 'no-url')
                                title_log = (item.get('text') or item.get('snippet') or '')[:100].replace('\n', ' ')
                                f.write(f"{url_log} | {title_log}\n")
                    except Exception as e:
                        logger.error(f"Raw capture logging failed: {e}")

                latency = time.time() - start_time
                
                if latency > HARD_TIMEOUT:
                    logger.warning(f"TIMEOUT GUARD: {scraper_name} took {latency:.2f}s (Threshold: {HARD_TIMEOUT}s)")
                
                # Calculate avg confidence, freshness, and geo_score if results found
                avg_conf = 0.0
                avg_fresh = 0.0
                avg_geo = 0.0
                if res:
                    # Use intent scorer to estimate confidence for metric tracking
                    scores = [buyer_intent_score(r.get('text', '')) for r in res]
                    avg_conf = sum(scores) / len(scores) if scores else 0.0
                    
                    # Calculate average freshness (minutes ago)
                    freshness_values = []
                    for r in res:
                        is_v, mins = self._verify_timestamp_strict(r.get('text', ''))
                        if is_v:
                            freshness_values.append(mins)
                    avg_fresh = sum(freshness_values) / len(freshness_values) if freshness_values else 0.0

                    # Calculate average geo_score
                    geo_scores = [r.get('geo_score', 0.0) for r in res]
                    avg_geo = sum(geo_scores) / len(geo_scores) if geo_scores else 0.0
                
                # Record run metrics with performance data
                record_run(scraper_name, leads_count=len(res) if res else 0, latency=latency, 
                           avg_confidence=avg_conf, avg_freshness=avg_fresh, avg_geo_score=avg_geo)
                
                if res:
                    # Tag leads with scraper name for later verification tracking
                    for r in res:
                        r["_scraper_name"] = scraper_name
                    set_cached(cache_key, res)
                    
                    # Success: reset consecutive failures
                    reset_consecutive_failures(scraper_name)
                return res
            except Exception as e:
                latency = time.time() - start_time
                logger.error(f"Scraper {scraper_name} failed: {str(e)}")
                record_run(scraper_name, leads_count=0, latency=latency, error=True)
                check_scraper_health(scraper_name)
                return []

        for sq in queries:
            for scraper in scrapers:
                future = SCRAPER_EXECUTOR.submit(scrape_with_cache, scraper, sq, time_window_hours)
                future_to_query[future] = (sq, scraper.__class__.__name__)
        
        raw_results = []
        # Wait for results with HARD_TIMEOUT
        try:
            for future in as_completed(future_to_query, timeout=HARD_TIMEOUT):
                sq, scraper_name = future_to_query[future]
                try:
                    results = future.result()
                    if not results: continue
                    
                    for r in results:
                        r["_scraper_name"] = scraper_name
                        # Count high-confidence signals for early return
                        if r.get('intent_score', 0) >= 0.8:
                            verified_count += 1
                            
                    raw_results.extend(results)
                    
                    # 🚀 EARLY RETURN: If we have enough verified signals, stop waiting
                    # The other futures will continue in the background pool.
                    if early_return and verified_count >= EARLY_RETURN_THRESHOLD:
                        logger.info(f"EARLY RETURN: Found {verified_count} verified signals. Returning immediately.")
                        break
                        
                except Exception as e:
                    logger.error(f"Error getting future result: {str(e)}")
        except TimeoutError:
            logger.warning(f"PARALLEL TIMEOUT: Some scrapers did not finish within {HARD_TIMEOUT}s")

        # 🧠 NLP Deduplication BEFORE strict filtering
        raw_results, rejected_nlp = dedupe_leads(raw_results)
        
        # Capture rejected leads from NLP deduplication
        if hasattr(self, 'rejected_leads'):
            self.rejected_leads.extend(rejected_nlp)

        for r in raw_results:
            scraper_name = r.get("_scraper_name")
            snippet = r.get('text', '')
            
            # 🧠 Generic Buyer Classification
            classification = classify_post(snippet)
            if classification != "buyer":
                # SOFT FLAG: Mark as seller/unclear but do not drop
                logger.debug(f"Intent Flag: {classification} for {snippet[:30]}...")
                r["intent_type"] = classification
            else:
                r["intent_type"] = "buyer"
            
            # 🧠 Generic Intent Scoring
            score = buyer_intent_score(snippet, query=original_query)
            
            # 🇰🇪 GEO SCORE: Calculate early for window escalation
            from app.intelligence_v2.geo_score import compute_geo_score
            geo_data = compute_geo_score(snippet, query=original_query, location=location)
            geo_score = geo_data.get("geo_score", 0.0)

            # 🔒 DYNAMIC FLOOR: Score everything, filter only absolute junk (<0.1)
            # Thresholding for strict mode is now handled AFTER ranking in _execute_discovery
            quality_flag = "ok"
            if score < 0.1:
                logger.debug(f"JUNK FLAGGED: Signal with score {score} (likely noise)")
                quality_flag = "noise"
            elif score < 0.4:
                quality_flag = "low_quality"
            
            # ⏱️ TIME WINDOW (🇰🇪 Escalation: Allow 4h for high geo relevance)
            effective_window = time_window_hours
            if geo_score >= 0.8:
                effective_window = max(effective_window, 4)
                logger.info(f"GEO ESCALATION: Extending discovery window to 4h for high-relevance lead (Geo: {geo_score})")

            is_verified_time, minutes_ago = self._verify_timestamp_strict(snippet)
            if is_verified_time and minutes_ago > (effective_window * 60):
                self.rejected_leads.append({**r, "rejection_reason": f"Timestamp too old ({minutes_ago}m > {effective_window*60}m)"})
                continue

            phone = r.get('phone') or r.get('contact', {}).get('phone') or self._extract_phone(snippet)
            email = r.get('email') or r.get('contact', {}).get('email')
            
            buyer_name = r.get('name') or self._extract_name(snippet, r.get('source', 'Web'))
            urgency = self._parse_urgency(snippet)
            
            url = r.get('url')
            if not url: 
                self.rejected_leads.append({**r, "rejection_reason": "Missing URL"})
                continue
                
            lead_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
            
            # Contact Flagging (Relaxed Requirement)
            contact_flag = "ok"
            if not phone and not email:
                contact_flag = "missing_contact"
            
            lead_data = {
                "id": lead_id,
                "role": "buyer",
                "buyer_name": buyer_name, 
                "contact_phone": phone,
                "contact_email": email,
                "contact_flag": contact_flag,
                "product_category": original_query,
                "quantity_requirement": "1",
                "intent_score": score,
                "intent_strength": score,
                "location_raw": r.get('location') or location,
                "radius_km": random.randint(1, 50),
                "source_platform": r.get('source', 'Web'),
                "source": r.get('source', 'unknown'),
                "_scraper_name": scraper_name,
                "is_sandbox": SCRAPER_REGISTRY.get(scraper_name, {}).get("mode") == "sandbox",
                "request_timestamp": datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
                "whatsapp_link": self._generate_whatsapp_link(phone, original_query),
                "source_url": url,
                "http_status": 200, 
                "created_at": datetime.now(timezone.utc),
                "property_country": "Kenya" if geo_score >= 0.5 else "Global",
                "geo_score": geo_score,
                "geo_strength": geo_data.get("geo_strength", "low"),
                "geo_region": geo_data.get("geo_region", "Global"),
                "buyer_request_snippet": snippet[:500],
                "urgency_level": urgency,
                "is_verified_signal": 1
            }
            
            # 🎯 Confidence Layer
            lead_data = apply_confidence(lead_data)
            
            # 🎯 Industry-Aware Priority
            from app.intelligence_v2.semantic_score import classify_lead_priority
            lead_data["priority_label"] = classify_lead_priority(
                lead_data.get("confidence_score", 0.0), 
                query=original_query
            )
            
            results_leads.append(lead_data)
        
        return results_leads

    def save_leads_to_db(self, leads: List[Dict[str, Any]]):
        """Save verified leads to the database."""
        from .db import models
        for l_data in leads:
            try:
                # Check if lead already exists
                existing = self.db.query(models.Lead).filter(models.Lead.id == l_data["id"]).first()
                if existing:
                    continue
                
                # Contact Flagging (Relaxed Requirement)
                contact_flag = "ok"
                if not l_data.get("contact_phone") and not l_data.get("contact_email"):
                    contact_flag = "missing_contact"
                    logger.info(f"Lead missing contact info: {l_data.get('id')} (Flagged as {contact_flag})")
                    # We do NOT return None. We proceed.
                
                new_lead = models.Lead(
                    id=l_data["id"],
                    buyer_name=l_data["buyer_name"],
                    contact_phone=l_data.get("contact_phone"),
                    contact_email=l_data.get("contact_email"),
                    contact_flag=contact_flag,
                    product_category=l_data["product_category"],
                    quantity_requirement=l_data["quantity_requirement"],
                    intent_score=l_data["intent_score"],
                    location_raw=l_data["location_raw"],
                    radius_km=l_data["radius_km"],
                    source_platform=l_data["source_platform"],
                    request_timestamp=l_data["request_timestamp"],
                    whatsapp_link=l_data["whatsapp_link"],
                    source_url=l_data["source_url"],
                    http_status=l_data["http_status"],
                    buyer_request_snippet=l_data["buyer_request_snippet"],
                    urgency_level=l_data["urgency_level"],
                    is_verified_signal=l_data["is_verified_signal"],
                    property_country=l_data["property_country"],
                    geo_score=l_data.get("geo_score", 0.0),
                    geo_strength=l_data.get("geo_strength", "low"),
                    geo_region=l_data.get("geo_region", "Global")
                )
                self.db.add(new_lead)
                self.db.commit()
            except Exception as e:
                logger.error(f"Error saving lead {l_data.get('id')}: {str(e)}")
                self.db.rollback()

    def run_full_cycle(self):
        """Run a full discovery cycle for all active search patterns."""
        # This is now handled by agents or background jobs in main.py
        pass
