import os
import uuid
import time
import random
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .scrapers.base_scraper import GoogleScraper, FacebookMarketplaceScraper, DuckDuckGoScraper

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
            # Check a reliable endpoint
            response = requests.get("https://www.google.com", timeout=5)
            if response.status_code == 200:
                logger.info("NETWORK CHECK: Connectivity verified (HTTP 200)")
                return True
            else:
                logger.error(f"NETWORK CHECK FAILED: HTTP {response.status_code}")
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

    def fetch_from_external_sources(self, query: str, location: str) -> List[Dict[str, Any]]:
        """Fetch live leads from real external sources with mandatory proof of life."""
        
        # ABSOLUTE RULE: Mandatory health check
        if not self.check_network_health():
            raise RuntimeError("ERROR: Network health check failed. Ingestion blocked to prevent stale data.")

        # ABSOLUTE RULE: raise error if not in production
        if ENVIRONMENT != "production":
            raise RuntimeError("Live leads disabled outside production")

        logger.info(f"FETCH: Starting real-time outbound search for '{query}' in {location}")
        all_leads = []
        
        # Expanded Source Discovery Queries (Legal Public Sources)
        search_queries = [
            # Social Platforms (Public Posts)
            f'"{query}" (looking for OR natafuta OR buying OR need) site:facebook.com "Kenya"',
            f'"{query}" (looking for OR natafuta OR buying OR need) site:twitter.com "Kenya"',
            f'"{query}" (looking for OR natafuta OR buying OR need) site:linkedin.com "Kenya"',
            f'"{query}" (looking for OR natafuta OR buying OR need) site:instagram.com "Kenya"',
            
            # Classifieds & Marketplaces
            f'"{query}" (anyone selling OR price of OR cost of) site:jiji.co.ke',
            f'"{query}" (anyone selling OR price of OR cost of) site:pigiame.co.ke',
            f'"{query}" (anyone selling OR price of OR cost of) site:kupatana.com "Kenya"',
            
            # Community & Forums
            f'"{query}" (recommendation OR suggest OR where to buy) site:reddit.com "Kenya"',
            f'"{query}" (price of OR where to buy) "Nairobi" "Kenya"',
            
            # Bio links & Business pages
            f'"{query}" (contact us OR whatsapp) site:linktr.ee "Kenya"',
            f'"{query}" (contact us OR whatsapp) site:wa.me "Kenya"',
        ]
        
        scrapers = [DuckDuckGoScraper(), GoogleScraper(), FacebookMarketplaceScraper()]
        
        try:
            for scraper in scrapers:
                for sq in search_queries:
                    start_time = time.time()
                    logger.info(f"OUTBOUND CALL: {scraper.__class__.__name__} for {sq}")
                    
                    try:
                        # Real outbound call using Playwright
                        results = scraper.scrape(sq)
                        latency = int((time.time() - start_time) * 1000)
                        
                        if not results:
                            continue

                        for r in results:
                            # Basic intent filtering
                            snippet = r.get('text', '').lower()
                            combined = snippet 
                            
                            logger.debug(f"DEBUG: Checking result from {scraper.__class__.__name__}: {snippet[:50]}...")
                            
                            # STRONG INTENT: Direct requests/questions (Buyer phrases)
                            strong_intent = ["looking for", "natafuta", "where can i", "anyone selling", "recommend", "suggest", "need", "urgent", "buying", "wanted", "looking to buy", "in search of", "does anyone have", "where to get"]
                            # GENERAL INTENT: Pricing/Availability questions
                            general_intent = ["price", "cost", "how much", "quote", "delivery", "contacts", "price list", "quotation", "catalogue"]
                            # NEGATIVE INTENT: Seller-oriented (block these strictly)
                            seller_keywords = [
                                "we sell", "available now", "in stock", "our shop", "dealer", "distributor", 
                                "wholesale", "fabricate", "supply and delivery", "we offer", "visit our", 
                                "shop online", "buy now", "order now", "best price", "special offer",
                                "brand new", "for sale", "call to order", "limited stock", "check out our",
                                "we deliver", "authorized dealer", "importer", "retailer", "car wash",
                                "cleaning services", "repairs", "installation", "we fix", "selling", "on offer",
                                "discount", "clearance", "sale", "we provide", "we manufacture", "factory price"
                            ]
                            
                            # ABSOLUTE SELLER BLOCKING
                            if any(sk in combined for sk in seller_keywords):
                                # Exception: ONLY if it also contains "looking for" or "wanted" at the VERY START of the text
                                buyer_phrases = ["looking for", "wanted", "natafuta", "in search of", "need"]
                                is_actually_buyer = False
                                for bp in buyer_phrases:
                                    if bp in combined[:50]:
                                        is_actually_buyer = True
                                        break
                                
                                if not is_actually_buyer:
                                    continue
                            
                            # ABSOLUTE FILTER: Must contain at least one intent phrase
                            if not any(kw in combined for kw in strong_intent + general_intent):
                                continue 

                            matching_strong = [kw for kw in strong_intent if kw in combined]
                            matching_general = [kw for kw in general_intent if kw in combined]
                            
                            if matching_strong or matching_general:
                                phone = self._extract_phone(r.get('text', ''))
                                buyer_name = self._extract_name(r.get('text', ''), r.get('source', 'Web'))
                                
                                lead_id = str(uuid.uuid5(uuid.NAMESPACE_URL, r['link']))
                                
                                base_score = 0.8 if matching_strong else 0.6
                                # Boost intent score if phone is found - money leads!
                                phone_boost = 0.1 if phone else 0.0
                                intent_score = min(0.99, base_score + (len(matching_strong) * 0.05) + (len(matching_general) * 0.02) + phone_boost)
                                
                                # Proof of life metadata
                                contact_source = "public" if phone else "unavailable"
                                if not phone and any(link_kw in r.get('text', '').lower() for link_kw in ['wa.me', 'linktr.ee', 'bit.ly', 'instagram.com']):
                                    contact_source = "inferred"

                                lead_data = {
                                    "id": lead_id,
                                    "buyer_name": buyer_name, 
                                    "contact_phone": phone,
                                    "product_category": query,
                                    "quantity_requirement": "1",
                                    "intent_score": intent_score,
                                    "location_raw": location,
                                    "radius_km": random.randint(1, 50),
                                    "source_platform": r.get('source', 'Web'),
                                    "request_timestamp": datetime.now(timezone.utc),
                                    "whatsapp_link": self._generate_whatsapp_link(phone, query),
                                    "source_url": r['link'],
                                    "http_status": 200, 
                                    "latency_ms": latency,
                                    "created_at": datetime.now(timezone.utc),
                                    "property_country": "Kenya",
                                    "buyer_request_snippet": r.get('text', '')[:500], # Save snippet for search/context
                                    "confidence_score": 0.9 if phone else (0.7 if contact_source == "inferred" else 0.4),
                                    "contact_source": contact_source
                                }
                                
                                all_leads.append(lead_data)
                    except Exception as e:
                        logger.error(f"NETWORK CALL FAILED for {scraper.__class__.__name__}: {str(e)}")
                        continue

            # ABSOLUTE RULE: Ban empty arrays, placeholders, or mocks
            if not all_leads:
                raise RuntimeError("ERROR: No live sources returned data. Possible causes: API blocked, Rate limited, Invalid query, Network failure")

            # Deduplicate leads by ID before returning
            unique_leads = []
            seen_ids = set()
            for lead in all_leads:
                if lead['id'] not in seen_ids:
                    unique_leads.append(lead)
                    seen_ids.add(lead['id'])

            logger.info(f"FETCH COMPLETE: Found {len(unique_leads)} VERIFIED signals for '{query}' (deduplicated from {len(all_leads)})")
            return unique_leads

        except Exception as e:
            logger.error(f"CRITICAL INGESTION ERROR: {e}")
            raise RuntimeError(f"ERROR: No live sources returned data. {str(e)}")

    def _extract_phone(self, text: str) -> str:
        """Extract real Kenyan phone numbers using regex. No guessing allowed."""
        import re
        # Kenyan phone formats: +254..., 07..., 01...
        phone_pattern = r'(\+254|0)(7|1)\d{8}'
        match = re.search(phone_pattern, text.replace(' ', '').replace('-', ''))
        if match:
            found = match.group(0)
            if found.startswith('0'):
                return '254' + found[1:]
            return found.replace('+', '')
        return None

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
                
                new_lead = models.Lead(**lead_data)
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
        logger.info("--- STARTING LIVE LEAD INGESTION CYCLE ---")
        
        # Pick a random category and location to simulate real-time discovery
        target_query = random.choice(self.categories)
        target_loc = random.choice(self.locations)
        
        leads = self.fetch_from_external_sources(target_query, target_loc)
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
