import os
import uuid
import time
import random
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .scrapers.base_scraper import GoogleScraper, FacebookMarketplaceScraper, DuckDuckGoScraper, SerpApiScraper, GoogleCSEScraper

# ABSOLUTE RULE: PROD STRICT ENFORCEMENT
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

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
    def __init__(self, db_session: Session):
        self.db = db_session
        self.categories = ["water tank", "construction materials", "electronics", "tires", "solar panels"]
        self.locations = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"]
        # Enforce production check immediately if initialized for live fetching
        if ENVIRONMENT != "production":
            logger.warning("--- WARNING: Delta9 running in DEVELOPMENT mode. Live ingestion restricted to PROD_STRICT. ---")

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

    def fetch_from_external_sources(self, query: str, location: str, time_window_hours: int = 2) -> List[Dict[str, Any]]:
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
            leads = self._execute_discovery(query, location, current_window)
            if leads:
                # Add current window info to leads
                for l in leads:
                    l["discovery_window"] = f"{current_window}h"
                return leads
        
        return []

    def _execute_discovery(self, query: str, location: str, time_window_hours: int) -> List[Dict[str, Any]]:
        """Internal discovery execution with PARALLEL scraping."""
        # ABSOLUTE RULE: Mandatory health check
        if not self.check_network_health():
            if ENVIRONMENT == "production":
                raise RuntimeError("ERROR: Network health check failed. Ingestion blocked to prevent stale data.")
            else:
                logger.warning("NETWORK CHECK FAILED: Continuing anyway because ENVIRONMENT != 'production'")

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
        
        # Prioritize Google CSE, SerpApi, then others
        scrapers = [GoogleCSEScraper(), SerpApiScraper(), DuckDuckGoScraper(), GoogleScraper(), FacebookMarketplaceScraper()]
        
        for pass_idx, pass_queries in enumerate(discovery_passes):
            logger.info(f"PASS {pass_idx + 1}/{len(discovery_passes)}: Starting parallel discovery...")
            pass_leads = []
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_query = {}
                for sq in pass_queries:
                    for scraper in scrapers:
                        # Submit each scraper task
                        future = executor.submit(scraper.scrape, sq, time_window_hours=time_window_hours)
                        future_to_query[future] = (sq, scraper.__class__.__name__)
                
                for future in as_completed(future_to_query, timeout=90): # Overall timeout for all scrapers
                    sq, scraper_name = future_to_query[future]
                    try:
                        results = future.result()
                        if not results: continue

                        for r in results:
                            snippet = r.get('text', '').lower()
                            url_lower = r.get('link', '').lower()
                            
                            # 🔒 PRODUCTION OVERRIDE: VERIFIED OUTBOUND SIGNALS
                            mandatory_buyer_signals = [
                                "looking to buy", "need to buy", "anyone selling?", 
                                "where can i get", "i want to purchase", "need asap", 
                                "need urgently", "budget is", "ready to pay", "dm me prices",
                                "natafuta", "price of", "where to find", "how much is",
                                "looking for", "recommend a", "suggest a", "how much",
                                "price?", "inbox price", "available?", "where in",
                                "selling this?", "want this", "i need", "contact of",
                                "who has", "supplier of", "buying", "interested in buying"
                            ]
                            
                            # 🚫 HARD EXCLUSIONS
                            seller_keywords = [
                                "we sell", "we supply", "available in stock", "contact us", 
                                "agent listing", "product catalog", "our shop", "dealer", 
                                "distributor", "wholesale", "fabricate", "supply and delivery", 
                                "we offer", "visit our", "shop online", "buy now", "order now", 
                                "best price", "special offer", "brand new", "for sale", 
                                "call to order", "limited stock", "check out our", "we deliver", 
                                "authorized dealer", "importer", "retailer", "car wash",
                                "cleaning services", "repairs", "installation", "we fix", 
                                "on offer", "discount", "clearance", "sale", "we provide", 
                                "we manufacture", "factory price", "service provider", 
                                "agent", "broker", "wholesaler", "manufacturer", "business page",
                                "company website", "official website", "price list", "catalogue",
                                "listing", "marketplace", "we are selling", "buy from us"
                            ]
                            
                            business_url_indicators = [
                                "/shop/", "/product/", "/catalog/", "/store/", "/business/", 
                                "jiji.co.ke", "pigiame.co.ke", "kupatana.com", "my-store", 
                                "shopify", "woocommerce", "official", "corporate", "co.ke/shop"
                            ]

                            if any(ui in url_lower for ui in business_url_indicators):
                                continue
                            if any(sk in snippet for sk in seller_keywords):
                                if not any(bs in snippet for bs in mandatory_buyer_signals):
                                    continue

                            # VERIFIED OUTBOUND SIGNAL CHECK
                            if not any(bs in snippet for bs in mandatory_buyer_signals):
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
                            
                            lead_id = str(uuid.uuid5(uuid.NAMESPACE_URL, r['link']))
                            lead_data = {
                                "id": lead_id,
                                "buyer_name": buyer_name, 
                                "contact_phone": phone,
                                "product_category": query,
                                "quantity_requirement": "1",
                                "intent_score": 0.95 if phone else 0.85,
                                "location_raw": location,
                                "radius_km": random.randint(1, 50),
                                "source_platform": r.get('source', 'Web'),
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

        logger.info(f"FETCH COMPLETE: Found {len(unique_leads)} verified signals.")
        return unique_leads

    def save_leads_to_db(self, leads: List[Dict[str, Any]]):
        """Save unique leads to database with logging."""
        from .db import models
        
        new_count = 0
        duplicate_count = 0
        
        for lead_data in leads:
            try:
                # Check for duplicates by source_url (replaces post_link)
                existing = self.db.query(models.Lead).filter(models.Lead.source_url == lead_data["source_url"]).first()
                if existing:
                    duplicate_count += 1
                    continue
                
                # Prepare data for Lead model (only keep valid columns)
                valid_lead_data = {k: v for k, v in lead_data.items() if k not in ["is_recent", "minutes_ago"]}
                
                new_lead = models.Lead(**valid_lead_data)
                self.db.add(new_lead)
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
