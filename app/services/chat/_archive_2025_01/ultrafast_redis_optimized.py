"""
Ultra-fast Chat with Redis History - Optimized Version

Key optimizations:
- Claude 3 Haiku (fastest model)
- Minimal context (last 3 messages)
- Lower token limit (500)
- No system prompt for speed
- Connection reuse
"""
import time
import asyncio
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


async def ultrafast_redis_optimized_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Optimized ultra-fast chat with Redis-backed history
    
    Target: <500ms consistent response times
    """
    try:
        start_time = time.time()
        
        # Get user ID
        user_id = auth_principal.get("sub") or auth_principal.get("key")
        if not user_id:
            raise ValueError("No user ID found")
        
        # Check if history exists
        history_exists = redis_chat_history.exists(user_id)
        
        # Initialize if needed (minimal system prompt)
        if not history_exists:
            redis_chat_history.initialize_history(user_id, "You are a helpful AI assistant. Be concise.")
        
        # Add user message (must be synchronous to be included in context)
        redis_chat_history.add_message(user_id, "user", request.message)
        
        # Get recent context (last 10 messages for better memory)
        recent_messages = redis_chat_history.get_recent_messages(user_id, count=10)
        
        # Build messages for API - no system prompt for speed
        messages = []
        
        for msg in recent_messages:
            if msg.content and msg.content.strip() and msg.role != "system":
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Ensure we have the current message
        if not messages or messages[-1]["content"] != request.message:
            messages.append({
                "role": "user",
                "content": request.message
            })
        
        # Call Haiku with optimized parameters
        api_start = time.time()
        response = await anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            messages=messages,
            max_tokens=500,   # Lower token limit for speed
            temperature=0.3,  # Consistent responses
            stream=False
        )
        api_time = int((time.time() - api_start) * 1000)
        
        assistant_content = response.content[0].text
        
        # Calculate response time BEFORE any additional operations
        total_time = int((time.time() - start_time) * 1000)
        
        # Prepare response to return immediately
        result = {
            "response": assistant_content,
            "model": "claude-3-haiku-20240307",
            "response_time_ms": total_time,
            "api_time_ms": api_time,
            "context_messages": len(messages),
            "history_length": redis_chat_history.get_message_count(user_id) + 2  # +2 for user and assistant
        }
        
        # Add assistant response asynchronously AFTER preparing the response
        # This happens in the background after we return to the user
        loop = asyncio.get_event_loop()
        loop.call_soon(lambda: redis_chat_history.add_message(user_id, "assistant", assistant_content))
        
        logger.info(f"Ultrafast Redis Optimized: {total_time}ms (API: {api_time}ms)")
        
        return result
        
    except Exception as e:
        logger.error(f"Ultrafast Redis optimized error: {e}")
        raise HTTPException(status_code=500, detail=str(e))