"""
Ultra-fast Chat with Parallel Redis Operations

Key optimizations:
- Redis pipeline for batch operations
- Parallel history retrieval
- Deferred response storage
- Background tasks for non-critical operations
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, BackgroundTasks
import logging
import json
from datetime import datetime

from anthropic import AsyncAnthropic
from app.models.chat import ChatRequest, Message
from app.shared.redis_client import redis_client
from app.shared.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

# Initialize async client
anthropic_client = AsyncAnthropic(
    max_retries=0,
    timeout=5.0,
)


class ParallelRedisChat:
    """Optimized Redis chat with parallel operations"""
    
    def __init__(self):
        self.redis = redis_client.client
        self.key_prefix = "chat:history:"
        
    def _get_key(self, user_id: str) -> str:
        return f"{self.key_prefix}{user_id}"
    
    async def process_chat(
        self,
        request: ChatRequest,
        auth_principal: Dict[str, Any],
        background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """Process chat with optimized Redis operations"""
        
        start_time = time.time()
        
        # Get user ID
        user_id = auth_principal.get("sub") or auth_principal.get("key")
        if not user_id:
            raise ValueError("No user ID found")
        
        key = self._get_key(user_id)
        
        # Create user message
        user_msg = {
            "role": "user",
            "content": request.message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Use Redis pipeline for parallel operations
        pipe = self.redis.pipeline()
        
        # Check existence and add message in one round trip
        pipe.exists(key)
        pipe.rpush(key, json.dumps(user_msg))
        pipe.expire(key, 86400)  # 24 hour TTL
        pipe.lrange(key, -11, -1)  # Get last 11 messages (including the one we just added)
        
        # Execute all operations in parallel
        redis_start = time.time()
        results = pipe.execute()
        redis_time = int((time.time() - redis_start) * 1000)
        
        exists = results[0]
        recent_raw = results[3]
        
        # Initialize if needed
        if not exists:
            # Add system prompt in background
            system_msg = {
                "role": "system",
                "content": "You are a helpful AI assistant. Be concise.",
                "timestamp": datetime.utcnow().isoformat()
            }
            background_tasks.add_task(self._init_with_system, key, system_msg)
        
        # Parse messages for API
        messages = []
        for raw_msg in recent_raw[-10:]:  # Use last 10 for context
            try:
                msg_data = json.loads(raw_msg)
                if msg_data["role"] != "system":
                    messages.append({
                        "role": msg_data["role"],
                        "content": msg_data["content"]
                    })
            except:
                continue
        
        # Ensure current message is included
        if not messages or messages[-1]["content"] != request.message:
            messages.append({
                "role": "user",
                "content": request.message
            })
        
        # Call Anthropic API
        api_start = time.time()
        response = await anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            messages=messages,
            max_tokens=500,
            temperature=0.3,
            stream=False
        )
        api_time = int((time.time() - api_start) * 1000)
        
        assistant_content = response.content[0].text
        
        # Calculate total time NOW, before any additional operations
        total_time = int((time.time() - start_time) * 1000)
        
        # Add assistant response in background
        assistant_msg = {
            "role": "assistant",
            "content": assistant_content,
            "timestamp": datetime.utcnow().isoformat()
        }
        background_tasks.add_task(self._store_assistant_response, key, assistant_msg)
        
        logger.info(f"Ultrafast Parallel: {total_time}ms (Redis: {redis_time}ms, API: {api_time}ms)")
        
        return {
            "response": assistant_content,
            "model": "claude-3-haiku-20240307",
            "response_time_ms": total_time,
            "api_time_ms": api_time,
            "redis_time_ms": redis_time,
            "context_messages": len(messages),
            "parallel_ops": True
        }
    
    def _init_with_system(self, key: str, system_msg: dict):
        """Initialize with system prompt in background"""
        try:
            # Get current messages
            current = self.redis.lrange(key, 0, -1)
            # Clear and re-add with system first
            pipe = self.redis.pipeline()
            pipe.delete(key)
            pipe.lpush(key, json.dumps(system_msg))
            for msg in current:
                pipe.rpush(key, msg)
            pipe.expire(key, 86400)
            pipe.execute()
        except Exception as e:
            logger.error(f"Failed to init system prompt: {e}")
    
    def _store_assistant_response(self, key: str, assistant_msg: dict):
        """Store assistant response in background"""
        try:
            pipe = self.redis.pipeline()
            pipe.rpush(key, json.dumps(assistant_msg))
            pipe.expire(key, 86400)
            pipe.ltrim(key, -100, -1)  # Keep last 100 messages
            pipe.execute()
        except Exception as e:
            logger.error(f"Failed to store assistant response: {e}")


# Global instance
parallel_redis_chat = ParallelRedisChat()


async def ultrafast_redis_parallel_endpoint(
    request: ChatRequest,
    auth_principal: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Ultra-fast chat endpoint with parallel Redis operations
    
    Target: <400ms consistent response times
    """
    return await parallel_redis_chat.process_chat(request, auth_principal, background_tasks)