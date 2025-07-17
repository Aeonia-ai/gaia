"""
Shared database configuration for Gaia Platform services.
Maintains compatibility with LLM Platform database schema.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/llm_platform")

# SQLAlchemy engine configuration
# Use same patterns as LLM Platform for compatibility
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections every hour
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for database models
Base = declarative_base()

def get_database_session():
    """
    Dependency to get database session.
    Compatible with LLM Platform dependency injection pattern.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_database_url() -> str:
    """Get the current database URL."""
    return DATABASE_URL

# Alias for backward compatibility
get_db = get_database_session

def test_database_connection() -> bool:
    """Test database connectivity."""
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

# Database health check for service monitoring
async def database_health_check() -> dict:
    """Async health check for database connectivity."""
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            return {
                "status": "healthy",
                "database": "postgresql",
                "responsive": True
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "postgresql",
            "responsive": False,
            "error": str(e)
        }

@lru_cache()
def get_database_settings() -> dict:
    """Get database configuration settings."""
    return {
        "url": DATABASE_URL,
        "echo": os.getenv("DATABASE_ECHO", "false").lower() == "true",
        "pool_size": int(os.getenv("DATABASE_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
        "pool_timeout": int(os.getenv("DATABASE_POOL_TIMEOUT", "30")),
        "pool_recycle": int(os.getenv("DATABASE_POOL_RECYCLE", "3600")),
    }
