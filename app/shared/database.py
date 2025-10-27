"""
Shared database configuration for Gaia Platform services.
Maintains compatibility with LLM Platform database schema.
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from functools import lru_cache
import logging
from contextlib import asynccontextmanager
import asyncpg

logger = logging.getLogger(__name__)

# Database URL from environment with postgres:// -> postgresql:// conversion
raw_database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/llm_platform")
# Convert postgres:// to postgresql:// for SQLAlchemy compatibility
DATABASE_URL = raw_database_url.replace("postgres://", "postgresql://", 1) if raw_database_url.startswith("postgres://") else raw_database_url

# SQLAlchemy engine configuration
# Use same patterns as LLM Platform for compatibility
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections every hour
    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "20")),      # Increased from 5
    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "30")), # Increased from 10
    pool_timeout=30,
    pool_reset_on_return='commit'  # Better connection hygiene
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

# Alias for backward compatibility
get_db = get_database_session

def get_database_url() -> str:
    """Get the current database URL."""
    return DATABASE_URL

# Alias for backward compatibility
get_db = get_database_session

def test_database_connection() -> bool:
    """Test database connectivity."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
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
            result = connection.execute(text("SELECT 1"))
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
        "pool_size": int(os.getenv("DATABASE_POOL_SIZE", "20")),
        "max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", "30")),
        "pool_timeout": int(os.getenv("DATABASE_POOL_TIMEOUT", "30")),
        "pool_recycle": int(os.getenv("DATABASE_POOL_RECYCLE", "3600")),
    }

# Async database pool for asyncpg
_async_pool = None

async def get_async_pool():
    """Get or create async database pool."""
    global _async_pool
    if _async_pool is None:
        # Parse database URL to get connection params
        import urllib.parse
        parsed = urllib.parse.urlparse(DATABASE_URL)

        # Init callback to register pgvector for all connections
        async def init_connection(conn):
            try:
                from pgvector.asyncpg import register_vector
                await register_vector(conn)
                logger.debug("Registered pgvector type for new connection")
            except ImportError:
                logger.debug("pgvector.asyncpg not available - vector type not registered")
            except Exception as e:
                logger.warning(f"Failed to register pgvector type: {e}")

        _async_pool = await asyncpg.create_pool(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:],  # Remove leading /
            min_size=5,
            max_size=20,
            command_timeout=10,
            init=init_connection  # Register pgvector for every new connection
        )
        logger.info("Database pool created with pgvector type registration")
    return _async_pool

async def close_async_pool():
    """Close the async database pool."""
    global _async_pool
    if _async_pool:
        await _async_pool.close()
        _async_pool = None

@asynccontextmanager
async def get_db_session():
    """Async context manager for database sessions."""
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        yield connection

def get_database():
    """Get database connection pool (for KB storage compatibility)."""
    # This returns a pool-like object for KB storage
    class AsyncPoolWrapper:
        @asynccontextmanager
        async def acquire(self):
            async with get_db_session() as conn:
                yield conn
    
    return AsyncPoolWrapper()
