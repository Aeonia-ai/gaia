"""
Persistent Memory for Lightweight Chat

Implements database-backed conversation memory using Gaia's existing
PostgreSQL and Redis infrastructure.
"""
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from sqlalchemy import Column, String, Text, DateTime, Integer, JSON
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

from app.shared.database import Base, get_db_session
from app.shared.redis_client import redis_client
from app.models.chat import Message

logger = logging.getLogger(__name__)


# Database model for conversation history
class ConversationHistory(Base):
    """
    PostgreSQL table for persistent conversation storage.
    
    Follows MCP-Agent best practices from community implementations.
    """
    __tablename__ = "conversation_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    message_role = Column(String, nullable=False)  # user, assistant, system
    message_content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata = Column(JSON, nullable=True)  # For future extensions


class PersistentMemoryManager:
    """
    Manages conversation memory with Redis caching and PostgreSQL persistence.
    
    Architecture:
    - Redis: Fast cache with TTL (active conversations)
    - PostgreSQL: Long-term storage (all conversations)
    - Automatic sync between cache and database
    """
    
    def __init__(self, redis_ttl_hours: int = 2):
        self.redis_ttl = redis_ttl_hours * 3600  # Convert to seconds
        
    def _get_redis_key(self, user_id: str) -> str:
        """Generate Redis key for user's conversation"""
        return f"chat:history:{user_id}"
    
    async def get_conversation_history(
        self, 
        user_id: str, 
        limit: int = 50
    ) -> List[Message]:
        """
        Get conversation history with Redis cache fallback to PostgreSQL.
        
        Pattern from community: Try cache first, then database.
        """
        # Try Redis first
        redis_key = self._get_redis_key(user_id)
        
        try:
            cached_data = await redis_client.get(redis_key)
            if cached_data:
                logger.debug(f"Found conversation in Redis for user {user_id}")
                messages_data = json.loads(cached_data)
                return [Message(**msg) for msg in messages_data]
        except Exception as e:
            logger.warning(f"Redis read error: {e}, falling back to database")
        
        # Fallback to PostgreSQL
        async with get_db_session() as session:
            query = select(ConversationHistory).where(
                ConversationHistory.user_id == user_id
            ).order_by(
                ConversationHistory.timestamp.desc()
            ).limit(limit)
            
            result = await session.execute(query)
            rows = result.scalars().all()
            
            # Convert to Message objects (newest first in DB, so reverse)
            messages = [
                Message(role=row.message_role, content=row.message_content)
                for row in reversed(rows)
            ]
            
            # Cache in Redis for next time
            if messages:
                await self._cache_messages(user_id, messages)
            
            return messages
    
    async def add_message(
        self, 
        user_id: str, 
        message: Message,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a message to both Redis cache and PostgreSQL.
        
        Implements write-through caching pattern.
        """
        # Save to PostgreSQL first (source of truth)
        async with get_db_session() as session:
            db_message = ConversationHistory(
                user_id=user_id,
                message_role=message.role,
                message_content=message.content,
                metadata=metadata
            )
            session.add(db_message)
            await session.commit()
            logger.debug(f"Saved message to database for user {user_id}")
        
        # Update Redis cache
        try:
            # Get current cache
            redis_key = self._get_redis_key(user_id)
            cached_data = await redis_client.get(redis_key)
            
            if cached_data:
                messages_data = json.loads(cached_data)
            else:
                messages_data = []
            
            # Append new message
            messages_data.append(message.model_dump())
            
            # Keep cache size reasonable (last 50 messages)
            if len(messages_data) > 50:
                messages_data = messages_data[-50:]
            
            # Save back to Redis with TTL
            await redis_client.setex(
                redis_key,
                self.redis_ttl,
                json.dumps(messages_data)
            )
            logger.debug(f"Updated Redis cache for user {user_id}")
            
        except Exception as e:
            logger.error(f"Redis write error: {e}, data saved to DB only")
    
    async def _cache_messages(self, user_id: str, messages: List[Message]):
        """Cache messages in Redis"""
        try:
            redis_key = self._get_redis_key(user_id)
            messages_data = [msg.model_dump() for msg in messages]
            
            await redis_client.setex(
                redis_key,
                self.redis_ttl,
                json.dumps(messages_data)
            )
        except Exception as e:
            logger.warning(f"Failed to cache messages: {e}")
    
    async def clear_history(self, user_id: str):
        """Clear conversation history for a user"""
        # Clear Redis
        try:
            redis_key = self._get_redis_key(user_id)
            await redis_client.delete(redis_key)
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")
        
        # Clear PostgreSQL
        async with get_db_session() as session:
            await session.execute(
                ConversationHistory.__table__.delete().where(
                    ConversationHistory.user_id == user_id
                )
            )
            await session.commit()
            logger.info(f"Cleared conversation history for user {user_id}")
    
    async def get_conversation_summary(
        self, 
        user_id: str,
        max_messages: int = 20
    ) -> str:
        """
        Get a summarized version of conversation history.
        
        Implements summarization pattern from Redis/LangGraph examples.
        """
        messages = await self.get_conversation_history(user_id, limit=max_messages)
        
        if not messages:
            return "No previous conversation."
        
        # Simple summary (could use LLM for better summaries)
        summary_parts = []
        for i, msg in enumerate(messages[-10:]):  # Last 10 messages
            if msg.role == "user":
                summary_parts.append(f"User: {msg.content[:100]}...")
            elif msg.role == "assistant":
                summary_parts.append(f"Assistant: {msg.content[:100]}...")
        
        return "\n".join(summary_parts)


# Global instance
memory_manager = PersistentMemoryManager()


# Enhanced lightweight chat with persistent memory
class PersistentLightweightChat:
    """
    Lightweight chat service with database-backed memory.
    
    Combines mcp-agent patterns with persistent storage.
    """
    
    def __init__(self):
        from app.services.chat.lightweight_chat import LightweightChatService
        self.base_service = LightweightChatService()
        self.memory = memory_manager
    
    async def process_chat_with_memory(
        self,
        request,
        auth_principal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process chat with persistent memory instead of in-memory storage.
        """
        auth_key = auth_principal.get("sub") or auth_principal.get("key")
        if not auth_key:
            raise ValueError("Invalid auth")
        
        # Get conversation history from database
        history = await self.memory.get_conversation_history(auth_key)
        
        # Build context from persistent history
        context_messages = []
        for msg in history[-10:]:  # Last 10 messages for context
            if msg.role in ["user", "assistant"]:
                context_messages.append(f"{msg.role}: {msg.content}")
        
        # Add current message to context
        full_prompt = ""
        if context_messages:
            full_prompt = "Previous conversation:\n" + "\n".join(context_messages) + "\n\n"
        full_prompt += f"User: {request.message}"
        
        # Use base service for LLM interaction
        # (This part would integrate with the lightweight chat's LLM logic)
        
        # Save new messages to persistent storage
        user_message = Message(role="user", content=request.message)
        await self.memory.add_message(auth_key, user_message)
        
        # Generate response (simplified - would use actual LLM)
        response_content = f"Response based on {len(history)} messages of history"
        
        assistant_message = Message(role="assistant", content=response_content)
        await self.memory.add_message(auth_key, assistant_message)
        
        return {
            "response": response_content,
            "history_length": len(history) + 2
        }


# Usage example
"""
# In your chat endpoint:
from app.services.chat.persistent_memory import PersistentLightweightChat

persistent_chat = PersistentLightweightChat()

@router.post("/persistent-chat")
async def chat_with_memory(request, auth=Depends(get_current_auth)):
    return await persistent_chat.process_chat_with_memory(request, auth)
"""