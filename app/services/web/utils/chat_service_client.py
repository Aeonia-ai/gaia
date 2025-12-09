"""
Chat Service Client for Web Service
Handles communication with the chat service for conversation management
"""
import httpx
import json
from typing import List, Dict, Any, Optional
from app.shared.logging import setup_service_logger
from app.shared.config import settings

logger = setup_service_logger("chat_service_client")

class ChatServiceClient:
    """Client for chat service conversation management"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'CHAT_SERVICE_URL', 'http://chat-service:8000')
        logger.info(f"Initialized ChatServiceClient with base_url: {self.base_url}")
    
    def _get_headers(self, jwt_token: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, str]:
        """Get headers for chat service requests"""
        headers = {"Content-Type": "application/json"}
        
        # If JWT token is provided, use it for authentication
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        # If API key is provided, use it (for backwards compatibility)
        elif api_key:
            headers["X-API-Key"] = api_key
        # No fallback - authentication must be explicitly provided
        
        return headers
    
    async def create_conversation(self, user_id: str, title: str = "New Conversation", 
                                 jwt_token: Optional[str] = None) -> Dict[str, Any]:
        """Create a new conversation"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/conversations",
                    headers=self._get_headers(jwt_token),
                    json={"title": title}
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Created conversation {result['id']} for user {user_id}")
                return result
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise
    
    async def get_conversations(self, user_id: str, jwt_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        try:
            headers = self._get_headers(jwt_token)
            logger.debug(f"[CHAT_CLIENT] Calling {self.base_url}/conversations with headers: {list(headers.keys())}")
            if 'Authorization' in headers:
                logger.debug(f"[CHAT_CLIENT] Authorization header present: Bearer {headers['Authorization'][7:37]}...")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/conversations",
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                conversations = result.get("conversations", [])
                logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
                return conversations
        except Exception as e:
            logger.error(f"[CHAT_CLIENT] Error getting conversations: {e}")
            raise
    
    async def get_conversation(self, user_id: str, conversation_id: str, 
                              jwt_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a specific conversation"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/conversations/{conversation_id}",
                    headers=self._get_headers(jwt_token)
                )
                if response.status_code == 404:
                    logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
                    return None
                response.raise_for_status()
                result = response.json()
                logger.info(f"Retrieved conversation {conversation_id} for user {user_id}")
                return result
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            raise
    
    async def update_conversation(self, user_id: str, conversation_id: str, 
                                 title: Optional[str] = None, preview: Optional[str] = None,
                                 jwt_token: Optional[str] = None) -> bool:
        """Update conversation metadata"""
        try:
            update_data = {}
            if title is not None:
                update_data["title"] = title
            if preview is not None:
                update_data["preview"] = preview
                
            if not update_data:
                return True  # Nothing to update
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/conversations/{conversation_id}",
                    headers=self._get_headers(jwt_token),
                    json=update_data
                )
                if response.status_code == 404:
                    logger.warning(f"Conversation {conversation_id} not found for update")
                    return False
                response.raise_for_status()
                logger.info(f"Updated conversation {conversation_id}")
                return True
        except Exception as e:
            logger.error(f"Error updating conversation: {e}")
            raise
    
    async def delete_conversation(self, user_id: str, conversation_id: str,
                                 jwt_token: Optional[str] = None) -> bool:
        """Delete a conversation"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/conversations/{conversation_id}",
                    headers=self._get_headers(jwt_token)
                )
                if response.status_code == 404:
                    logger.warning(f"Conversation {conversation_id} not found for deletion")
                    return False
                response.raise_for_status()
                logger.info(f"Deleted conversation {conversation_id}")
                return True
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            raise
    
    async def add_message(self, conversation_id: str, role: str, content: str,
                         model: Optional[str] = None, provider: Optional[str] = None,
                         tokens_used: Optional[int] = None,
                         jwt_token: Optional[str] = None) -> Dict[str, Any]:
        """Add a message to a conversation"""
        try:
            message_data = {
                "role": role,
                "content": content
            }
            if model:
                message_data["model"] = model
            if provider:
                message_data["provider"] = provider
            if tokens_used is not None:
                message_data["tokens_used"] = tokens_used
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/conversations/{conversation_id}/messages",
                    headers=self._get_headers(jwt_token),
                    json=message_data
                )
                if response.status_code == 404:
                    raise ValueError(f"Conversation {conversation_id} not found")
                response.raise_for_status()
                result = response.json()
                logger.info(f"Added {role} message to conversation {conversation_id}")
                return result
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise
    
    async def get_messages(self, conversation_id: str, 
                          jwt_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all messages for a conversation"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/conversations/{conversation_id}/messages",
                    headers=self._get_headers(jwt_token)
                )
                response.raise_for_status()
                result = response.json()
                messages = result.get("messages", [])
                logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
                return messages
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            raise
    
    async def search_conversations(self, user_id: str, query: str,
                                  jwt_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search conversations by title or content"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/conversations/search/{query}",
                    headers=self._get_headers(jwt_token)
                )
                response.raise_for_status()
                result = response.json()
                conversations = result.get("conversations", [])
                logger.info(f"Found {len(conversations)} conversations matching '{query}' for user {user_id}")
                return conversations
        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            raise
    
    async def get_conversation_stats(self, user_id: str,
                                    jwt_token: Optional[str] = None) -> Dict[str, int]:
        """Get conversation statistics for a user"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/conversations/stats",
                    headers=self._get_headers(jwt_token)
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Retrieved stats for user {user_id}: {result}")
                return result
        except Exception as e:
            logger.error(f"Error getting conversation stats: {e}")
            raise

# Global instance
chat_service_client = ChatServiceClient()