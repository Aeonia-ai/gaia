"""
Simple Lightweight Chat - Direct Anthropic Integration

TODO: This is Tech Debt, remove
Ultra-fast chat endpoint that bypasses mcp-agent overhead
and uses the Anthropic client directly.
"""
from typing import Dict, Any, List
from fastapi import Depends, HTTPException
import logging
import time
import os

from anthropic import Anthropic

from app.shared.security import get_current_auth_legacy as get_current_auth
from app.models.chat import ChatRequest, Message

logger = logging.getLogger(__name__)

# Initialize Anthropic client once
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# In-memory chat histories
chat_histories: Dict[str, List[Message]] = {}


async def simple_lightweight_chat_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any] = Depends(get_current_auth)
):
    """
    Ultra-lightweight chat endpoint using direct Anthropic client.
    
    No mcp-agent overhead, just pure speed.
    """
    try:
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
        if not auth_key:
            raise HTTPException(status_code=401, detail="Invalid auth")
        
        # Initialize chat history if needed
        if auth_key not in chat_histories:
            chat_histories[auth_key] = []
            logger.info(f"Initialized chat history for user: {auth_key}")
        
        # Build conversation context
        messages = []
        for msg in chat_histories[auth_key][-10:]:  # Last 10 messages
            messages.append({
                "role": msg.role if msg.role != "system" else "user",
                "content": msg.content
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # Call Anthropic directly
        start_time = time.time()
        response = anthropic_client.messages.create(
            model=request.model or "claude-sonnet-4-5",
            messages=messages,
            max_tokens=2000,
            temperature=0.7
        )
        response_time = time.time() - start_time
        
        # Extract response content
        response_text = response.content[0].text
        
        # Update history
        chat_histories[auth_key].extend([
            Message(role="user", content=request.message),
            Message(role="assistant", content=response_text)
        ])
        
        # Keep history manageable
        if len(chat_histories[auth_key]) > 50:
            chat_histories[auth_key] = chat_histories[auth_key][-50:]
        
        # Return OpenAI-compatible response
        return {
            "id": f"chat-{auth_key}-{len(chat_histories[auth_key])}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model or "claude-sonnet-4-5",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            "_response_time_ms": int(response_time * 1000)
        }
        
    except Exception as e:
        logger.error(f"Simple lightweight chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))