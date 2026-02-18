from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Enum, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
import hashlib
from app.db.base_class import Base

# Imported definitions
from app.models.lead import Lead, ContactStatus, CRMStatus

class BuyerLead(Base):
    """
    🎯 BUYERS TABLE (MINIMAL) - Standardized schema for buyer-only ingestion.
    """
    __tablename__ = "buyer_leads"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    platform = Column(String)
    intent = Column(String)
    location = Column(String)
    contact = Column(String)
    contact_status = Column(String)
    confidence = Column(Float) # SQL REAL maps to Float in SQLAlchemy
    posted_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

class AgentRunLog(Base):
    __tablename__ = "agent_run_logs"

    id = Column(Integer, primary_key=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    run_time = Column(DateTime, default=func.now())
    leads_found = Column(Integer, default=0)
    errors = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0)

    agent = relationship("Agent", backref="run_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": str(self.agent_id),
            "run_time": self.run_time.isoformat() if self.run_time else None,
            "leads_found": self.leads_found,
            "errors": self.errors,
            "duration_ms": self.duration_ms
        }

class BuyerIntent(Base):
    __tablename__ = "buyer_intents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True) # The agent or user who has this intent
    interest_type = Column(String, index=True) # Flexible: "Toyota", "iPhone", "Apartment"
    vehicle_type = Column(String, index=True) # DEPRECATED: use interest_type
    budget_min = Column(Float, default=0.0)
    budget_max = Column(Float)
    location = Column(String, index=True)
    urgency = Column(String, default="medium") # high, medium, low
    
    # Metadata
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "interest_type": self.interest_type or self.vehicle_type,
            "vehicle_type": self.vehicle_type, # Legacy support
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "location": self.location,
            "urgency": self.urgency,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class SearchPattern(Base):
    __tablename__ = "search_patterns"
    
    id = Column(Integer, primary_key=True)
    keyword = Column(String, unique=True)
    category = Column(String)
    is_active = Column(Integer, default=1)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String, index=True) # WHATSAPP_TAP, LEAD_DISCOVERED, SEARCH_PERFORMED
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    session_id = Column(String, index=True, nullable=True) # To group user behavior
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    extra_metadata = Column(JSON, nullable=True) # For additional info like product name, etc.

# Import Agent from new location but allow it to be accessed via models.Agent
from app.models.agent import Agent
from app.models.agent_raw_lead import AgentRawLead
from app.models.notification import Notification

class AgentLead(Base):
    __tablename__ = "agent_leads"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"))
    discovered_at = Column(DateTime, server_default=func.now())

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True)
    value = Column(JSON)
    updated_at = Column(DateTime, onupdate=func.now())

class ScraperMetric(Base):
    __tablename__ = "scraper_metrics"
    
    id = Column(Integer, primary_key=True)
    scraper_name = Column(String, unique=True, index=True)
    runs = Column(Integer, default=0)
    leads_found = Column(Integer, default=0)
    verified_leads = Column(Integer, default=0)
    failures = Column(Integer, default=0)
    consecutive_failures = Column(Integer, default=0)
    avg_latency = Column(Float, default=0.0) # Average runtime in seconds
    avg_confidence = Column(Float, default=0.0) # Average intent score of leads
    avg_freshness = Column(Float, default=0.0) # NEW: Average age of signals in minutes
    avg_geo_score = Column(Float, default=0.0) # NEW: Average geographic relevance of leads
    priority_score = Column(Float, default=0.0) # Unified ranking score
    priority_boost = Column(Float, default=1.0) # Priority multiplier
    auto_disabled = Column(Integer, default=0) # 0 = active, 1 = disabled
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

class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String, index=True, nullable=True)
    scraper_name = Column(String, index=True, nullable=True)
    error_type = Column(String, index=True) # TIMEOUT, CRASH, NETWORK
    error_message = Column(Text)
    stack_trace = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
