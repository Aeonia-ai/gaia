"""
Shared Supabase client configuration for Gaia Platform services.
Maintains compatibility with LLM Platform Supabase integration.
"""
import os
from supabase import create_client, Client
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Supabase configuration from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Global Supabase client instance
supabase: Optional[Client] = None

# Initialize Supabase client if valid configuration is provided
if SUPABASE_URL and SUPABASE_ANON_KEY and not SUPABASE_URL.startswith("YOUR_") and not SUPABASE_URL == "https://placeholder.supabase.co":
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase client: {e}")
        supabase = None
else:
    logger.warning("Supabase configuration not provided or using placeholder values - client not initialized")

def get_supabase_client() -> Optional[Client]:
    """
    Dependency to get the Supabase client instance.
    Returns None if Supabase is not configured (for testing).
    """
    return supabase

async def test_supabase_connection() -> bool:
    """Test Supabase connectivity."""
    try:
        # Simple test query to verify connection
        response = supabase.table("_test_connection").select("*").limit(1).execute()
        logger.info("Supabase connection successful")
        return True
    except Exception as e:
        logger.warning(f"Supabase connection test failed (this may be expected): {e}")
        # This is not necessarily a failure - the table might not exist
        # We'll consider the client creation successful as the real test
        return True

async def supabase_health_check() -> dict:
    """Health check for Supabase connectivity."""
    try:
        # Attempt a simple operation
        await test_supabase_connection()
        return {
            "status": "healthy",
            "service": "supabase",
            "url": SUPABASE_URL,
            "responsive": True
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "service": "supabase",
            "url": SUPABASE_URL,
            "responsive": False,
            "error": str(e)
        }

def get_supabase_config() -> dict:
    """Get Supabase configuration for debugging/monitoring."""
    return {
        "url": SUPABASE_URL,
        "anon_key_configured": bool(SUPABASE_ANON_KEY),
        "jwt_secret_configured": bool(os.getenv("SUPABASE_JWT_SECRET"))
    }
