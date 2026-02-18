
import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic.v1 import BaseSettings
    except ImportError:
        from pydantic import BaseSettings

class Settings(BaseSettings):
    # Existing config or defaults
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Delta 9"
    
    # SERPAPI Configuration
    SERPAPI_KEY: Optional[str] = None
    SERPAPI_ENGINE: str = "google"
    SERPAPI_REGION: str = "ke"
    SERPAPI_LANGUAGE: str = "en"
    
    # Other settings from .env
    DATABASE_URL: Optional[str] = None
    MIN_INTENT_SCORE: float = 0.75
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
