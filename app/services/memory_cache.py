"""
In-memory caching service for personas and tools
Adapted from LLM Platform for Gaia Platform architecture
"""
import time
import logging
from typing import Dict, List
from app.shared.tool_provider import ToolProvider
from app.shared.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

# In-memory persona cache - eliminates database lookups after first request
persona_memory_cache: Dict[str, dict] = {}
persona_cache_ttl: Dict[str, float] = {}
PERSONA_CACHE_TTL_SECONDS = 300  # 5 minutes

# In-memory tools cache - eliminates MCP lookups
tools_memory_cache: Dict[str, List] = {}
tools_cache_ttl: Dict[str, float] = {}
TOOLS_CACHE_TTL_SECONDS = 600  # 10 minutes


async def get_cached_persona_memory(persona_id: str, user_id: str) -> dict:
    """Get persona with in-memory caching - eliminates DB lookups after first request"""
    cache_key = f"{user_id}:{persona_id}"
    current_time = time.time()
    
    # Check in-memory cache first
    if (cache_key in persona_memory_cache and 
        current_time < persona_cache_ttl.get(cache_key, 0)):
        logger.debug(f"Memory cache hit for persona {persona_id} (0ms)")
        return persona_memory_cache[cache_key]
    
    # Cache miss - fetch from database (this will be rare after warmup)
    logger.debug(f"Memory cache miss for persona {persona_id}, fetching from DB")
    fetch_start = time.time()
    
    try:
        # Use PromptManager for Gaia Platform
        system_prompt = await PromptManager.get_system_prompt(user_id=user_id)
        
        persona_dict = {
            "name": "Assistant",
            "system_prompt": system_prompt,
            "persona_id": persona_id,
            "user_id": user_id
        }
        
        # Cache in memory for fast access
        persona_memory_cache[cache_key] = persona_dict
        persona_cache_ttl[cache_key] = current_time + PERSONA_CACHE_TTL_SECONDS
        
        fetch_time = (time.time() - fetch_start) * 1000
        logger.info(f"Persona fetched and cached in {fetch_time:.0f}ms")
        
        return persona_dict
            
    except Exception as e:
        logger.warning(f"Error fetching persona {persona_id}: {e}, using fallback")
        fallback_persona = {
            "name": "Assistant", 
            "system_prompt": "You are a helpful AI assistant.",
            "persona_id": persona_id,
            "user_id": user_id
        }
        
        # Cache the fallback too to avoid repeated failures
        persona_memory_cache[cache_key] = fallback_persona
        persona_cache_ttl[cache_key] = current_time + 60  # Shorter TTL for fallback
        
        return fallback_persona


async def get_cached_tools_memory(activity: str) -> List:
    """Get tools with in-memory caching - eliminates MCP lookups after first request"""
    cache_key = activity
    current_time = time.time()
    
    # Check in-memory cache first
    if (cache_key in tools_memory_cache and 
        current_time < tools_cache_ttl.get(cache_key, 0)):
        logger.debug(f"Memory cache hit for tools {activity} (0ms)")
        return tools_memory_cache[cache_key]
    
    # Cache miss - fetch from MCP
    logger.debug(f"Memory cache miss for tools {activity}, fetching from MCP")
    fetch_start = time.time()
    
    try:
        tools = await ToolProvider.get_tools_for_activity(activity)
        
        # Cache in memory for fast access
        tools_memory_cache[cache_key] = tools
        tools_cache_ttl[cache_key] = current_time + TOOLS_CACHE_TTL_SECONDS
        
        fetch_time = (time.time() - fetch_start) * 1000
        logger.info(f"Tools fetched and cached in {fetch_time:.0f}ms")
        
        return tools
        
    except Exception as e:
        logger.warning(f"Error fetching tools for {activity}: {e}")
        # Return empty tools list on error
        empty_tools = []
        tools_memory_cache[cache_key] = empty_tools
        tools_cache_ttl[cache_key] = current_time + 60  # Shorter TTL for fallback
        return empty_tools


def invalidate_persona_cache(user_id: str = None, persona_id: str = None):
    """Invalidate persona cache when personas are updated"""
    if user_id and persona_id:
        # Invalidate specific persona for user
        cache_key = f"{user_id}:{persona_id}"
        persona_memory_cache.pop(cache_key, None)
        persona_cache_ttl.pop(cache_key, None)
        logger.info(f"Invalidated persona cache for {cache_key}")
    elif user_id:
        # Invalidate all personas for user
        keys_to_remove = [key for key in persona_memory_cache.keys() if key.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            persona_memory_cache.pop(key, None)
            persona_cache_ttl.pop(key, None)
        logger.info(f"Invalidated {len(keys_to_remove)} persona cache entries for user {user_id}")
    else:
        # Clear entire cache
        persona_memory_cache.clear()
        persona_cache_ttl.clear()
        logger.info("Cleared entire persona memory cache")


def invalidate_tools_cache(activity: str = None):
    """Invalidate tools cache when tools are updated"""
    if activity:
        # Invalidate specific activity
        tools_memory_cache.pop(activity, None)
        tools_cache_ttl.pop(activity, None)
        logger.info(f"Invalidated tools cache for {activity}")
    else:
        # Clear entire cache
        tools_memory_cache.clear()
        tools_cache_ttl.clear()
        logger.info("Cleared entire tools memory cache")


def get_cache_status() -> dict:
    """Get memory cache status"""
    return {
        "persona_cache_entries": len(persona_memory_cache),
        "tools_cache_entries": len(tools_memory_cache),
        "persona_cache_keys": list(persona_memory_cache.keys()),
        "tools_cache_keys": list(tools_memory_cache.keys())
    }