"""
Redis-based Chat History Manager

Provides high-performance chat history storage with:
- Sub-millisecond reads/writes
- Automatic TTL-based cleanup
- JSON serialization for messages
- Atomic operations
"""
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.shared.redis_client import redis_client
from app.models.chat import Message

logger = logging.getLogger(__name__)


class RedisChatHistory:
    """
    Manages chat history in Redis for ultra-fast access
    
    Key pattern: chat:history:{user_id}
    TTL: Configurable (default 24 hours)
    """
    
    def __init__(self, default_ttl_hours: int = 24):
        self.redis = redis_client.client  # Use the underlying Redis client
        self.default_ttl = timedelta(hours=default_ttl_hours)
        self.key_prefix = "chat:history:"
        
    def _get_key(self, user_id: str) -> str:
        """Generate Redis key for user's chat history"""
        return f"{self.key_prefix}{user_id}"
    
    def initialize_history(self, user_id: str, system_prompt: str) -> None:
        """
        Initialize chat history with system prompt
        
        Args:
            user_id: Unique user identifier
            system_prompt: System prompt to initialize with
        """
        try:
            key = self._get_key(user_id)
            
            # Create system message
            system_message = {
                "role": "system",
                "content": system_prompt,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Initialize history with system message
            self.redis.delete(key)  # Clear any existing
            self.redis.lpush(key, json.dumps(system_message))
            self.redis.expire(key, int(self.default_ttl.total_seconds()))
            
            logger.debug(f"Initialized chat history for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize chat history: {e}")
            raise
    
    def add_message(self, user_id: str, role: str, content: str) -> None:
        """
        Add a message to chat history
        
        Args:
            user_id: Unique user identifier
            role: Message role (user/assistant/system)
            content: Message content
        """
        try:
            key = self._get_key(user_id)
            
            # Create message
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add to history (append to end)
            self.redis.rpush(key, json.dumps(message))
            
            # Refresh TTL
            self.redis.expire(key, int(self.default_ttl.total_seconds()))
            
            # Trim if too long (keep last 100 messages)
            list_length = self.redis.llen(key)
            if list_length > 100:
                # Keep first (system) and last 99 messages
                system_msg = self.redis.lindex(key, 0)
                self.redis.ltrim(key, -99, -1)
                self.redis.lpush(key, system_msg)
            
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            # Don't raise - allow chat to continue without history
    
    def get_history(self, user_id: str) -> List[Message]:
        """
        Get full chat history for a user
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            List of Message objects
        """
        try:
            key = self._get_key(user_id)
            
            # Get all messages
            raw_messages = self.redis.lrange(key, 0, -1)
            
            if not raw_messages:
                return []
            
            # Parse messages
            messages = []
            for raw_msg in raw_messages:
                try:
                    msg_data = json.loads(raw_msg)
                    messages.append(Message(
                        role=msg_data["role"],
                        content=msg_data["content"]
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse message: {e}")
                    continue
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    def get_recent_messages(
        self, 
        user_id: str, 
        count: int = 10
    ) -> List[Message]:
        """
        Get recent messages for context
        
        Args:
            user_id: Unique user identifier
            count: Number of recent messages to retrieve
            
        Returns:
            List of recent Message objects
        """
        try:
            key = self._get_key(user_id)
            
            # Get last N messages
            raw_messages = self.redis.lrange(key, -count, -1)
            
            messages = []
            for raw_msg in raw_messages:
                try:
                    msg_data = json.loads(raw_msg)
                    messages.append(Message(
                        role=msg_data["role"],
                        content=msg_data["content"]
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse message: {e}")
                    continue
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []
    
    def clear_history(self, user_id: str) -> None:
        """
        Clear chat history for a user
        
        Args:
            user_id: Unique user identifier
        """
        try:
            key = self._get_key(user_id)
            self.redis.delete(key)
            logger.debug(f"Cleared chat history for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
    
    def get_message_count(self, user_id: str) -> int:
        """
        Get number of messages in history
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Number of messages (excluding system prompt)
        """
        try:
            key = self._get_key(user_id)
            total = self.redis.llen(key)
            
            # Check if first message is system prompt
            if total > 0:
                first_msg = self.redis.lindex(key, 0)
                if first_msg:
                    msg_data = json.loads(first_msg)
                    if msg_data.get("role") == "system":
                        return total - 1
            
            return total
            
        except Exception as e:
            logger.error(f"Failed to get message count: {e}")
            return 0
    
    def exists(self, user_id: str) -> bool:
        """
        Check if user has chat history
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            True if history exists
        """
        try:
            key = self._get_key(user_id)
            return self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check existence: {e}")
            return False
    
    def set_ttl(self, user_id: str, ttl_hours: int) -> None:
        """
        Set custom TTL for a user's chat history
        
        Args:
            user_id: Unique user identifier
            ttl_hours: TTL in hours
        """
        try:
            key = self._get_key(user_id)
            ttl = timedelta(hours=ttl_hours)
            self.redis.expire(key, int(ttl.total_seconds()))
        except Exception as e:
            logger.error(f"Failed to set TTL: {e}")


# Global instance
redis_chat_history = RedisChatHistory()