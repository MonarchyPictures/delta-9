import logging
import re
from typing import Dict, Any, List, Optional
from .metrics import record_verified, CATEGORY_STATS, record_category_lead
from ..config.categories.vehicles_ke import VEHICLES_KE
from ..core.pipeline_mode import BOOTSTRAP_RULES, PIPELINE_MODE

logger = logging.getLogger("ScraperVerifier")

# 🔒 PRODUCTION OVERRIDE: VERIFIED OUTBOUND SIGNALS
MANDATORY_BUYER_SIGNALS = [
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
SELLER_KEYWORDS = [
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

BUSINESS_URL_INDICATORS = [
    "/shop/", "/product/", "/catalog/", "/store/", "/business/", 
    "jiji.co.ke", "pigiame.co.ke", "kupatana.com", "my-store", 
    "shopify", "woocommerce", "official", "corporate", "co.ke/shop"
]

TRUSTED_SOURCES = { 
    "google_maps", 
    "jiji_kenya", 
    "facebook_marketplace",
    "GoogleMapsScraper",
    "JijiKenyaScraper",
    "FacebookMarketplaceScraper"
}

def is_verified_signal(text: str, url: str = "") -> bool:
    """Check if a snippet represents a genuine buyer signal."""
    snippet = text.lower()
    url_lower = url.lower()

    if any(ui in url_lower for ui in BUSINESS_URL_INDICATORS):
        return False
        
    if any(sk in snippet for sk in SELLER_KEYWORDS):
        if not any(bs in snippet for bs in MANDATORY_BUYER_SIGNALS):
            return False

    return any(bs in snippet for bs in MANDATORY_BUYER_SIGNALS)

def adaptive_threshold(category: str, base: float = 0.85, loosen_factor: float = 0.0) -> float:
    """
    Adjust confidence threshold based on historical success rate for the category.
    High success rate -> Lower threshold (easier to verify)
    Low success rate -> Higher threshold (stricter verification)
    loosen_factor: amount to decrease threshold (e.g. 0.1 for 10% lower)
    """
    # 🔒 LOCKED CATEGORY FLOOR: Use VEHICLES_KE floor as base if category matches
    if category.lower() in [VEHICLES_KE["category"]] + VEHICLES_KE["objects"]:
        base = VEHICLES_KE["confidence_floor"]
    
    # 🧪 BOOTSTRAP OVERRIDE: Use lower floor locally
    if PIPELINE_MODE == "bootstrap":
        base = min(base, BOOTSTRAP_RULES["min_confidence"])

    threshold = base
    
    if category in CATEGORY_STATS:
        success_rate = CATEGORY_STATS[category]["verified_rate"]
        
        # Delta-9 learns what works: 
        if success_rate > 0.6:
            threshold -= 0.1
        elif success_rate < 0.2:
            threshold += 0.1
            
    # Apply emergency loosening
    threshold -= loosen_factor
    
    # Cap between 0.5 and 0.95
    return max(0.5, min(0.95, threshold))

def verify_leads(leads: List[Dict[str, Any]], loosen: bool = False) -> List[Dict[str, Any]]: 
    """Cross-source verification and trusted source tagging with adaptive thresholds."""
    # Emergency loosening factor (10% lower)
    loosen_factor = 0.1 if loosen else 0.0
    
    grouped = {} 

    for lead in leads: 
        key = ( 
            lead.get("product_category", "").lower(), 
            lead.get("location_raw", "").lower() 
        ) 
        grouped.setdefault(key, []).append(lead) 

    verified_list = [] 

    for _, group in grouped.items(): 
        sources = {l.get("source") for l in group} 
        scraper_names = {l.get("_scraper_name") for l in group if l.get("_scraper_name")}
        all_sources = sources.union(scraper_names)

        for lead in group: 
            source = lead.get("source")
            scraper_name = lead.get("_scraper_name")
            category = lead.get("product_category", "general")
            confidence = lead.get("confidence_score", 0.0)
            
            # 1. Trusted Source Check
            is_trusted = source in TRUSTED_SOURCES or scraper_name in TRUSTED_SOURCES
            
            # 2. Adaptive Threshold Check (PROD_STRICT that learns)
            threshold = adaptive_threshold(category, loosen_factor=loosen_factor)
            meets_threshold = confidence >= threshold
            
            # 3. Cross-Source Check
            has_cross_match = len(all_sources) >= 2
            
            # Verification Decision
            is_verified = False
            reason = "unverified"
            
            if is_trusted: 
                is_verified = True
                reason = "trusted_source" 
            elif meets_threshold:
                is_verified = True
                reason = f"adaptive_threshold_match({threshold:.2f})"
            elif has_cross_match: 
                is_verified = True
                reason = "cross_source_match" 
            else: 
                is_verified = False
                reason = "single_source_untrusted" 

            # Update lead object
            lead["is_verified_signal"] = 1 if is_verified else 0
            lead["verified"] = is_verified # For frontend/pipeline consistency
            lead["verification_reason"] = reason
            
            # Record metrics
            if is_verified and scraper_name: 
                record_verified(scraper_name)
            
            # Record category stats for future learning (SKIP for sandbox scrapers)
            if not lead.get("is_sandbox"):
                record_category_lead(category, is_verified)
            else:
                logger.info(f"SANDBOX: Lead from {scraper_name} verified but excluded from category learning.")

            verified_list.append(lead) 

    return verified_list
