from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Enum, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class ContactStatus(enum.Enum):
    NOT_CONTACTED = "not_contacted"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    REJECTED = "rejected"

class CRMStatus(enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    REPLIED = "replied"
    NEGOTIATING = "negotiating"
    CONVERTED = "converted"
    DEAD = "dead"

class Lead(Base):
    __tablename__ = "leads"

    # Lead Identification & Metadata
    id = Column(String, primary_key=True, index=True) # Maps to lead_id
    buyer_name = Column(String)
    contact_phone = Column(String, index=True) # Maps to phone
    product_category = Column(String, index=True) # Maps to product
    quantity_requirement = Column(String) # Maps to quantity
    intent_score = Column(Float) # Maps to intent_strength
    location_raw = Column(String) # Maps to location
    radius_km = Column(Float, default=0.0) # Maps to distance_km
    source_platform = Column(String, index=True) # Maps to source
    request_timestamp = Column(DateTime) # Maps to timestamp
    
    # NEW: WhatsApp Integration
    whatsapp_link = Column(String)
    contact_method = Column(String) # NEW: Explicit contact method from scraper
    
    # NEW: Status & Proof of Life (PROD STRICT)
    status = Column(Enum(CRMStatus), default=CRMStatus.NEW)
    source_url = Column(String)
    http_status = Column(Integer)
    latency_ms = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Legacy/Extended Fields (Keep for compatibility if needed, or remove if strictly following new schema)
    post_link = Column(String, unique=True)
    property_country = Column(String, default="Kenya", index=True)
    is_hot_lead = Column(Integer, default=0)
    buyer_request_snippet = Column(String)
    urgency_level = Column(String, default="low") # NEW: High/Medium/Low
    confidence_score = Column(Float, default=0.0)
    is_saved = Column(Integer, default=0)
    is_verified_signal = Column(Integer, default=1) # PROD_STRICT: Signal verification flag
    notes = Column(String)
    contact_source = Column(String) # public | inferred | unavailable
    
    def to_dict(self):
        return {
            "lead_id": self.id,
            "buyer_name": self.buyer_name,
            "phone": self.contact_phone,
            "product": self.product_category,
            "quantity": self.quantity_requirement,
            "intent_strength": self.intent_score,
            "location": self.location_raw,
            "distance_km": self.radius_km,
            "source": self.source_platform,
            "timestamp": self.request_timestamp.isoformat() if self.request_timestamp else None,
            "whatsapp_link": self.whatsapp_link,
            "status": self.status.value,
            "source_url": self.source_url,
            "buyer_intent_quote": self.buyer_request_snippet, # Step 5: Exact text
            "urgency_level": getattr(self, "urgency_level", "low"), # Ensure it exists
            "contact_method": self.contact_method or self.whatsapp_link or f"DM via {self.source_platform}",
            "confidence_score": self.confidence_score,
            "contact_source": self.contact_source
        }

class SearchPattern(Base):
    __tablename__ = "search_patterns"
    
    id = Column(Integer, primary_key=True)
    keyword = Column(String, unique=True)
    category = Column(String)
    is_active = Column(Integer, default=1)

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    query = Column(String)
    location = Column(String, default="Kenya")
    radius = Column(Integer, default=50) # Discovery radius in km
    min_intent_score = Column(Float, default=0.7) # Minimum intent score to accept
    is_active = Column(Integer, default=1)
    enable_alerts = Column(Integer, default=1) # New: enable real-time alerts
    last_run = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    lead_id = Column(String, ForeignKey("leads.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    message = Column(String)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True)
    value = Column(JSON)
    updated_at = Column(DateTime, onupdate=func.now())

class SellerProduct(Base):
    __tablename__ = "seller_products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    category = Column(String)
    specs = Column(JSON) # e.g. {"capacity": "50000L", "material": "Plastic"}
    price = Column(Float)
    location = Column(String)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

class ScraperMetric(Base):
    __tablename__ = "scraper_metrics"
    
    id = Column(Integer, primary_key=True)
    scraper_name = Column(String, unique=True, index=True)
    runs = Column(Integer, default=0)
    leads_found = Column(Integer, default=0)
    verified_leads = Column(Integer, default=0)
    failures = Column(Integer, default=0)
    consecutive_failures = Column(Integer, default=0)
    last_success = Column(DateTime)
    history = Column(JSON) # List of last 20 runs
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class CategoryMetric(Base):
    __tablename__ = "category_metrics"
    
    id = Column(Integer, primary_key=True)
    category_name = Column(String, unique=True, index=True)
    total_leads = Column(Integer, default=0)
    verified_leads = Column(Integer, default=0)
    verified_rate = Column(Float, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())