from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import os

# Use SQLite for now, easily switch to PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# If DATABASE_URL is empty after strip, fallback to local SQLite
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./intent_radar.db"

# Render/Heroku fix: SQLAlchemy requires 'postgresql://' instead of 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in DATABASE_URL else {}
)

# PROD_STRICT: Enable WAL mode for SQLite to prevent "database is locked" errors
if "sqlite" in DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
        except Exception as e:
            # If we can't set WAL mode because it's locked, it might already be in WAL mode
            # or will be set by another connection later. Don't crash.
            pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
