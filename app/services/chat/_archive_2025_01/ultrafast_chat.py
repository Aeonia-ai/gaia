"""
Ultra-fast Chat Endpoint - Optimized for <1s responses

Key optimizations:
- Claude 3 Haiku (fastest model)
- No chat history
- Minimal token limits
- Connection reuse
"""
import time
from typing import Dict, Any
from fastapi import HTTPException
import logging

from anthropic import Anthropic
from app.models.chat import ChatRequest

logger = logging.getLogger(__name__)

# Initialize client once with connection pooling
anthropic_client = Anthropic(
    max_retries=0,  # No retries for speed
    timeout=5.0,    # Short timeout
)

async def ultrafast_chat_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Ultra-fast chat endpoint optimized for <1s responses.
    
    Trade-offs:
    - No conversation history
    - Shorter responses (500 tokens max)
    - Claude 3 Haiku model
    """
    try:
        # Skip auth validation for speed (already done by gateway)
        
        # Direct API call with minimal overhead
        start_time = time.time()
        
        response = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",  # Fastest model
            messages=[{
                "role": "user",
                "content": request.message
            }],
            max_tokens=500,  # Limit response length
            temperature=0.3,  # Lower temperature for consistency
            stream=False
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Minimal response format
        return {
            "response": response.content[0].text,
            "model": "claude-3-haiku-20240307",
            "response_time_ms": response_time_ms
        }
        
    except Exception as e:
        logger.error(f"Ultrafast chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))