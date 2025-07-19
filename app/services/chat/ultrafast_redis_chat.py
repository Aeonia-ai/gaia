"""
Ultra-fast Chat with Redis History

Combines:
- Claude 3 Haiku for speed
- Redis for chat history
- Minimal overhead
- Target: <1s response time
"""
import time
from typing import Dict, Any, Optional
from fastapi import HTTPException
import logging

from anthropic import AsyncAnthropic
from app.models.chat import ChatRequest
from app.services.chat.redis_chat_history import redis_chat_history
from app.shared.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

# Initialize async client for better performance
anthropic_client = AsyncAnthropic(
    max_retries=0,  # No retries for speed
    timeout=5.0,    # Short timeout
)


async def ultrafast_redis_chat_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Ultra-fast chat with Redis-backed history
    
    Optimizations:
    - Async Anthropic client
    - Redis for history (sub-ms access)
    - Claude 3 Haiku
    - Parallel operations where possible
    """
    try:
        start_time = time.time()
        
        # Get user ID
        user_id = auth_principal.get("sub") or auth_principal.get("key")
        if not user_id:
            raise ValueError("No user ID found")
        
        # Check if history exists
        history_exists = redis_chat_history.exists(user_id)
        
        # Initialize if needed
        if not history_exists:
            system_prompt = await PromptManager.get_system_prompt(user_id=user_id)
            redis_chat_history.initialize_history(user_id, system_prompt)
        
        # Add user message
        redis_chat_history.add_message(user_id, "user", request.message)
        
        # Get recent context (last 5 messages for speed)
        recent_messages = redis_chat_history.get_recent_messages(user_id, count=5)
        
        # Build messages for API - separate system from messages
        messages = []
        system_prompt = None
        
        for msg in recent_messages:
            if msg.content and msg.content.strip():
                if msg.role == "system":
                    system_prompt = msg.content
                else:
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # Call Haiku (async for better concurrency)
        api_start = time.time()
        api_params = {
            "model": "claude-3-haiku-20240307",
            "messages": messages,
            "max_tokens": 1000,  # Slightly more than ultrafast
            "temperature": 0.3,
            "stream": False
        }
        
        # Add system prompt if available
        if system_prompt:
            api_params["system"] = system_prompt
            
        response = await anthropic_client.messages.create(**api_params)
        api_time = int((time.time() - api_start) * 1000)
        
        assistant_content = response.content[0].text
        
        # Add assistant response
        redis_chat_history.add_message(user_id, "assistant", assistant_content)
        
        total_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"Ultrafast Redis chat: {total_time}ms (API: {api_time}ms)")
        
        return {
            "response": assistant_content,
            "model": "claude-3-haiku-20240307",
            "response_time_ms": total_time,
            "api_time_ms": api_time,
            "history_length": len(recent_messages) + 2  # +2 for user and assistant
        }
        
    except Exception as e:
        logger.error(f"Ultrafast Redis chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Preload system prompts for common personas
async def preload_prompts():
    """Preload common prompts into memory for speed"""
    try:
        # This would cache frequently used prompts
        await PromptManager.get_system_prompt()
        logger.info("Preloaded system prompts")
    except Exception as e:
        logger.warning(f"Failed to preload prompts: {e}")


# Note: preload_prompts() can be called manually if needed