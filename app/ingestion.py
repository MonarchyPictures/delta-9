import os
import uuid
import time
import random
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .scrapers.base_scraper import BaseScraper, GoogleScraper, FacebookMarketplaceScraper, DuckDuckGoScraper, SerpApiScraper
from .scrapers.classifieds import ClassifiedsScraper
from .scrapers.twitter import TwitterScraper
from .scrapers.google_maps import GoogleMapsScraper
from .scrapers.reddit import RedditScraper
from .scrapers.google_cse import GoogleCSEScraper
from .scrapers.whatsapp_public_groups import WhatsAppPublicGroupScraper
from .scrapers.instagram import InstagramScraper
from .config import PROD_STRICT
from .config.categories.vehicles_ke import VEHICLES_KE
from .intelligence.confidence import apply_confidence
from .cache.scraper_cache import get_cached, set_cached
from .scrapers.registry import SCRAPER_REGISTRY, update_scraper_state, get_active_scrapers
from .scrapers.selector import decide_scrapers
from .scrapers.metrics import record_run, SCRAPER_METRICS
from .scrapers.supervisor import check_scraper_health, reset_consecutive_failures
from .scrapers.verifier import is_verified_signal, verify_leads
from .core.category_config import CategoryConfig

# ALL possible scrapers available in the system
ALL_SCRAPERS = [ 
    GoogleMapsScraper(), 
    ClassifiedsScraper(), 
    FacebookMarketplaceScraper(), 
    TwitterScraper(), 
    RedditScraper(),
    GoogleCSEScraper(),
    WhatsAppPublicGroupScraper(),
    InstagramScraper()
]

# ABSOLUTE RULE: PROD STRICT ENFORCEMENT
# Configuration for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ingestion.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LeadIngestion")

class LiveLeadIngestor:
    def __init__(self, db_session: Session, category: str = "vehicles"):
        self.db = db_session
        self.category_name = category
        self.config = CategoryConfig.get_config(category)
        if not self.config:
            raise ValueError(f"Invalid category: {category}")
        
        self.categories = self.config["search_terms"]
        self.locations = self.config["locations"]
        self.price_bands = self.config.get("price_bands", {})
        
        # Enforce production check immediately if initialized for live fetching
        if not PROD_STRICT:
            logger.warning("--- WARNING: Delta9 running in DEVELOPMENT mode. Auto-downgrading to bootstrap. ---")

    def check_network_health(self) -> bool:
        """Verify network connectivity and proxy health before ingestion."""
        logger.info("NETWORK CHECK: Verifying outbound connectivity...")
        try:
            # Check multiple reliable endpoints with significantly longer timeout for high-latency environments
            endpoints = [
                "https://www.google.com", 
                "https://8.8.8.8", 
                "https://duckduckgo.com",
                "https://www.facebook.com"
            ]
            for url in endpoints:
                try:
                    # Increase timeout to 20s to handle Kenyan mobile network latency
                    response = requests.get(url, timeout=20)
                    if response.status_code == 200 or response.status_code == 301 or response.status_code == 302:
                        logger.info(f"NETWORK CHECK: Connectivity verified via {url} (HTTP {response.status_code})")
                        return True
                except Exception as e:
                    logger.warning(f"NETWORK CHECK: {url} unreachable: {str(e)}")
                    continue
            
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
        """Extract real Kenyan phone numbers using regex. No guessing allowed."""
        if not text:
            return None
        import re
        # Handle common obfuscations like "07 22...", "07-22...", "07.22..."
        # And look for "whatsapp: 07...", "call 07..."
        clean_text = text.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '')
        # Pattern to match 2547XXXXXXXX, 2541XXXXXXXX, 07XXXXXXXX, 01XXXXXXXX, +254...
        phone_pattern = r'(\+254|254|0)(7|1)\d{8}'
        match = re.search(phone_pattern, clean_text)
        if match:
            found = match.group(0)
            if found.startswith('0'):
                return '254' + found[1:]
            if found.startswith('+'):
                return found.replace('+', '')
            if found.startswith('254'):
                return found
        return None

    def _extract_name(self, text: str, source_platform: str) -> str:
        """Attempt to extract name from public content."""
        if not text:
            return "Verified Market Signal"
        
        # Simple extraction for known patterns
        import re
        name_patterns = [
            r"Post by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"Contact:\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"Name:\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"^([A-Z][a-z]+\s+[A-Z][a-z]+)\s+is looking for",
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+on\s+(Facebook|Twitter|LinkedIn|Jiji|Pigiame)",
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

    def fetch_from_external_sources(self, query: str, location: str, time_window_hours: int = 2, category: Optional[str] = None, last_result_count: int = 0) -> List[Dict[str, Any]]:
        """
        Fetch live leads using MULTI-PASS DISCOVERY (3 PASSES).
        Includes AUTO-EXPANDING TIME WINDOW if zero results found.
        """
        # Strategy: Try requested window, then expand if needed
        windows_to_try = [time_window_hours]
        if time_window_hours <= 2:
            # For 2h window, if nothing found, try expanding to 24h then 7d
            windows_to_try = [2, 24, 168]
        
        for current_window in windows_to_try:
            logger.info(f"FETCH: Trying window {current_window}h for '{query}' in {location}")
            leads = self._execute_discovery(query, location, current_window, category, last_result_count)
            if leads:
                # Add current window info to leads
                for l in leads:
                    l["discovery_window"] = f"{current_window}h"
                return leads
        
        return []

    def _execute_discovery(self, query: str, location: str, time_window_hours: int, category: Optional[str] = None, last_result_count: int = 0) -> List[Dict[str, Any]]:
        """Internal discovery execution with PARALLEL scraping."""
        # ABSOLUTE RULE: Mandatory health check
        if not self.check_network_health():
            if PROD_STRICT:
                raise RuntimeError("ERROR: Network health check failed. Ingestion blocked to prevent stale data.")
            else:
                logger.warning("NETWORK CHECK FAILED: Continuing anyway because PROD_STRICT=False")

        # --- Adaptive Scraper Control (Trae AI Driven) ---
        enabled_sources = decide_scrapers(
            query=query, 
            location=location, 
            category=category,
            time_window_hours=time_window_hours, 
            is_prod=PROD_STRICT,
            last_result_count=last_result_count
        )
        
        # 🔒 STEP 3 — CATEGORY-SPECIFIC SCRAPER FILTERING
        # Mandatory lock for vehicles_ke category
        if category == "vehicles" or category == "vehicles_ke":
            authorized_scrapers = get_active_scrapers("vehicles_ke")
            # Only allow scrapers that are both enabled by AI and authorized for this category
            enabled_sources = [s for s in enabled_sources if s in authorized_scrapers]
            logger.info(f"🔒 CATEGORY LOCK: Filtering scrapers for vehicles_ke. Authorized: {authorized_scrapers}")

        # CRITICAL: Filter scrapers at runtime using ClassName registry check
        active_scrapers = [ 
            s for s in ALL_SCRAPERS 
            if s.__class__.__name__ in enabled_sources and SCRAPER_REGISTRY.get(s.__class__.__name__, {}).get("enabled")
        ]
        
        logger.info(f"AI Decision: Active scrapers for this query: {[s.__class__.__name__ for s in active_scrapers]}")

        # MULTI-PASS DISCOVERY STRATEGY
        discovery_passes = [
            # Pass 1: Direct buyer phrases
            [
                f'"{query}" (looking to buy OR natafuta OR buying OR need) site:facebook.com/groups "Kenya"',
                f'"{query}" (looking to buy OR natafuta OR buying OR need) site:twitter.com "Kenya"',
            ],
            # Pass 2: Conversational buyer language
            [
                f'"{query}" (price of OR where to find OR how much is OR recommend) "Kenya"',
                f'"{query}" (anyone selling OR where can i get) "Kenya"',
            ]
        ]
        
        all_leads = []
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
<<<<<<< HEAD
=======
        # Prioritize SerpApi, then others
        from ..scraper import LeadScraper
        ls = LeadScraper(category_keywords=self.config.get("keywords"))
        
        # Note: We still use specialized scrapers but they should eventually be unified
        scrapers = [SerpApiScraper(), DuckDuckGoScraper(), GoogleScraper(), FacebookMarketplaceScraper()]
        
>>>>>>> 29fc54e (feat: vehicle-only mode, success metrics, and buyer-match scoring engine.)
        for pass_idx, pass_queries in enumerate(discovery_passes):
            logger.info(f"PASS {pass_idx + 1}/{len(discovery_passes)}: Starting parallel discovery...")
            pass_leads = []
            
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_to_query = {}
                
                def scrape_with_cache(s, q, w):
                    scraper_name = s.__class__.__name__
                    cache_key = f"{scraper_name}:{q}:{w}"
                    cached = get_cached(cache_key)
                    if cached is not None:
                        logger.info(f"CACHE: Hit for {cache_key}")
                        return cached
                    
                    try:
                        res = s.scrape(q, time_window_hours=w)
                        # Record run metrics
                        record_run(scraper_name, leads_count=len(res) if res else 0)
                        
                        if res:
                            # Tag leads with scraper name for later verification tracking
                            for r in res:
                                r["_scraper_name"] = scraper_name
                            set_cached(cache_key, res)
                            
                            # Success: reset consecutive failures
                            reset_consecutive_failures(scraper_name)
                        return res
                    except Exception as e:
                        logger.error(f"Scraper {scraper_name} failed: {str(e)}")
                        record_run(scraper_name, leads_count=0, error=True)
                        
                        # Supervisor health check (Auto-disable if unstable)
                        check_scraper_health(scraper_name)
                            
                        return []

                for sq in pass_queries:
                    for scraper in active_scrapers:
                        # Submit each scraper task
                        future = executor.submit(scrape_with_cache, scraper, sq, time_window_hours)
                        future_to_query[future] = (sq, scraper.__class__.__name__)
                
                for future in as_completed(future_to_query, timeout=90): # Overall timeout for all scrapers
                    sq, scraper_name = future_to_query[future]
                    try:
                        results = future.result()
                        if not results: continue

                        for r in results:
                            snippet = r.get('intent_text', '').lower()
                            url_lower = r.get('link', '').lower()
                            
                            # 🧪 SANDBOX CHECK: Does this scraper run in sandbox mode?
                            scraper_config = SCRAPER_REGISTRY.get(scraper_name, {})
                            is_sandbox = scraper_config.get("mode") == "sandbox"
                            
                            # 🧠 VERIFIER: Check for genuine buyer signal
                            if not is_verified_signal(snippet, url_lower):
                                # Non-blocking for sandbox scrapers: still allow them to pass for observation
                                if not is_sandbox:
                                    continue
                                else:
                                    logger.info(f"SANDBOX: Allowing unverified signal from {scraper_name} (NON-BLOCKING)")
                            
                            # 🔒 LOCKED CATEGORY DRIFT PREVENTION
                            snippet_lower = snippet.lower()
                            has_vehicle_object = any(obj in snippet_lower for obj in VEHICLES_KE["objects"])
                            if not has_vehicle_object:
                                logger.info(f"DRIFT: Discarding lead from {scraper_name} - No vehicle object detected in snippet.")
                                continue

                            # ⏱️ TIME WINDOW
                            is_verified_time, minutes_ago = self._verify_timestamp_strict(r.get('text', ''))
                            
                            # For 2h window, be very strict
                            if time_window_hours <= 2 and not is_verified_time:
                                continue
                            
                            # If it's verified but older than our current window -> DISCARD
                            if is_verified_time and minutes_ago > (time_window_hours * 60):
                                continue

                            # Qualification
                            phone = self._extract_phone(r.get('text', ''))
                            buyer_name = self._extract_name(r.get('text', ''), r.get('source', 'Web'))
                            urgency = self._parse_urgency(snippet)
                            
                            # Use new intent-aware scoring for high confidence
                            from .nlp.intent_service import BuyingIntentNLP
                            nlp = BuyingIntentNLP()
                            
                            # Extract entities including price
                            entities = nlp.extract_entities(snippet)
                            extracted_price = entities.get("price")
                            
                            # Calculate confidence with price bands
                            confidence = nlp.calculate_confidence(
                                snippet, 
                                has_phone=bool(phone),
                                extracted_price=extracted_price,
                                price_bands=self.price_bands
                            )
                            
                            lead_id = str(uuid.uuid5(uuid.NAMESPACE_URL, r['link']))
                            lead_data = {
                                "id": lead_id,
                                "buyer_name": buyer_name, 
                                "contact_phone": phone,
                                "product_category": query,
                                "quantity_requirement": "1",
<<<<<<< HEAD
                                "intent_score": 0.95 if phone else 0.85,
                                "intent_strength": 0.95 if phone else 0.85, # Support for apply_confidence
=======
                                "intent_score": confidence,
>>>>>>> 29fc54e (feat: vehicle-only mode, success metrics, and buyer-match scoring engine.)
                                "location_raw": location,
                                "radius_km": random.randint(1, 50),
                                "source_platform": r.get('source', 'Web'),
                                "source": r.get('source', 'unknown'), # Standard source field for confidence
                                "_scraper_name": r.get("_scraper_name"), # Preserve for metrics
                                "is_sandbox": is_sandbox, # 🧪 Sandbox tagging
                                "request_timestamp": datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
                                "whatsapp_link": self._generate_whatsapp_link(phone, query),
                                "source_url": r['link'],
                                "http_status": 200, 
                                "created_at": datetime.now(timezone.utc),
                                "property_country": "Kenya",
                                "buyer_request_snippet": r.get('text', '')[:500],
                                "urgency_level": urgency,
                                "is_verified_signal": 1,
                                "is_recent": is_verified_time and minutes_ago <= 120,
                                "minutes_ago": minutes_ago
                            }
                            # Apply source-weighted confidence score
                            lead_data = apply_confidence(lead_data)
                            
                            pass_leads.append(lead_data)
                    except Exception as e:
                        logger.error(f"Parallel Scrape Error for {scraper_name}: {str(e)}")
            
            all_leads.extend(pass_leads)
            # If we found enough leads in this pass, stop
            if len(all_leads) >= 5:
                break
            
        # Deduplicate
        unique_leads = []
        seen_ids = set()
        for lead in all_leads:
            if lead['id'] not in seen_ids:
                unique_leads.append(lead)
                seen_ids.add(lead['id'])

        # 🧠 VERIFIER: Cross-source verification
        verified_leads = verify_leads(unique_leads)

        logger.info(f"FETCH COMPLETE: Found {len(verified_leads)} verified signals.")
        return verified_leads

    def save_leads_to_db(self, leads: List[Dict[str, Any]]):
        """Save unique leads to database with logging."""
        from .db import models
        
        new_count = 0
        duplicate_count = 0
        
        for lead_data in leads:
            # 🧪 SAFETY: Never save sandbox leads to production DB
            if lead_data.get("is_sandbox"):
                logger.info(f"SANDBOX: Skipping DB save for lead from {lead_data.get('_scraper_name')}")
                continue

            try:
                # Check for duplicates by source_url (replaces post_link)
                existing = self.db.query(models.Lead).filter(models.Lead.source_url == lead_data["source_url"]).first()
                if existing:
                    duplicate_count += 1
                    continue
                
                # Prepare data for Lead model (only keep valid columns)
                valid_lead_data = {k: v for k, v in lead_data.items() if k not in ["is_recent", "minutes_ago", "_scraper_name"]}
                
                new_lead = models.Lead(**valid_lead_data)
                self.db.add(new_lead)
                
                # Track discovery event for Success Definition
                new_log = models.ActivityLog(
                    event_type="LEAD_DISCOVERED",
                    lead_id=lead_data["id"],
                    metadata={
                        "product": lead_data.get("product_category"),
                        "location": lead_data.get("location_raw"),
                        "source": lead_data.get("source_platform")
                    }
                )
                self.db.add(new_log)
                
                new_count += 1
                logger.info(f"INSERT: New lead saved from {lead_data['source_platform']} - {lead_data['source_url']}")
            except Exception as e:
                logger.error(f"Error saving lead {lead_data.get('source_url')}: {e}")
                self.db.rollback()
        
        try:
            self.db.commit()
            logger.info(f"COMMIT: Saved {new_count} new leads, skipped {duplicate_count} duplicates.")
        except Exception as e:
            logger.error(f"Failed to commit transaction: {e}")
            self.db.rollback()

    def run_full_cycle(self):
        """Execute one full end-to-end ingestion cycle."""
        logger.info("--- STARTING LIVE LEAD INGESTION CYCLE (2h Window) ---")
        
        # Pick a random category and location to simulate real-time discovery
        target_query = random.choice(self.categories)
        target_loc = random.choice(self.locations)
        
        leads = self.fetch_from_external_sources(target_query, target_loc, time_window_hours=2)
        if leads:
            self.save_leads_to_db(leads)
        else:
            logger.warning("No live leads found in this cycle.")
            
        logger.info("--- END OF CYCLE ---")

if __name__ == "__main__":
    # For local testing
    from app.db.database import SessionLocal
    db = SessionLocal()
    ingestor = LiveLeadIngestor(db)
    
    print("Running 3 verification cycles...")
    for i in range(3):
        print(f"\nCycle {i+1}/3:")
        ingestor.run_full_cycle()
        time.sleep(2) # Wait between cycles
    
    db.close()
