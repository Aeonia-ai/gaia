"""
Test conversation persistence using the same approach as the web interface.
This mimics how the web UI successfully maintains conversation context.
"""

import pytest
import httpx
import os
from typing import Dict, Any, Optional
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestUserFactory

logger = setup_service_logger("test_web_style_conversation")


class TestWebStyleConversation:
    """Test conversation persistence using web interface patterns."""
    
    @pytest.fixture
    def chat_service_url(self):
        """Direct chat service URL."""
        return os.getenv("CHAT_SERVICE_URL", "http://chat-service:8000")
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def auth_url(self):
        """Auth service URL."""
        return os.getenv("AUTH_URL", "http://auth-service:8000")
    
    @pytest.fixture
    def user_factory(self):
        """Factory for creating test users."""
        factory = TestUserFactory()
        yield factory
        factory.cleanup_all()
    
    async def login_user(self, auth_url: str, email: str, password: str) -> Dict[str, Any]:
        """Login and get JWT."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{auth_url}/auth/login",
                json={"email": email, "password": password}
            )
            assert response.status_code == 200
            data = response.json()
            # Normalize response
            if "session" in data and "access_token" in data["session"]:
                data["access_token"] = data["session"]["access_token"]
            return data
    
    @pytest.mark.asyncio
    async def test_conversation_like_web_ui(self, chat_service_url, gateway_url, auth_url, user_factory):
        """Test conversation persistence using the same flow as the web interface."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        
        jwt_token = login_response["access_token"]
        user_id = login_response["user"]["id"]
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Create a conversation (like web UI does)
            logger.info("Creating conversation...")
            conv_response = await client.post(
                f"{chat_service_url}/conversations",
                headers=headers,
                json={"title": "Test Conversation"}
            )
            assert conv_response.status_code in [200, 201]
            conversation = conv_response.json()
            conversation_id = conversation["id"]
            logger.info(f"Created conversation: {conversation_id}")
            
            # Step 2: Add first user message (like web UI does)
            logger.info("Adding first message...")
            msg1_response = await client.post(
                f"{chat_service_url}/conversations/{conversation_id}/messages",
                headers=headers,
                json={
                    "role": "user",
                    "content": "My favorite number is 42. Please remember this."
                }
            )
            assert msg1_response.status_code in [200, 201]
            
            # Step 3: Send to chat endpoint for AI response
            logger.info("Getting AI response...")
            chat_response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "My favorite number is 42. Please remember this.",
                    "conversation_id": conversation_id
                }
            )
            assert chat_response1.status_code == 200
            ai_response1 = chat_response1.json()
            logger.info(f"AI responded to first message")
            
            # Step 4: Add second user message
            logger.info("Adding second message...")
            msg2_response = await client.post(
                f"{chat_service_url}/conversations/{conversation_id}/messages",
                headers=headers,
                json={
                    "role": "user",
                    "content": "What is my favorite number?"
                }
            )
            assert msg2_response.status_code in [200, 201]
            
            # Step 5: Send to chat endpoint with conversation_id
            logger.info("Getting AI response for second message...")
            chat_response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What is my favorite number?",
                    "conversation_id": conversation_id
                }
            )
            assert chat_response2.status_code == 200
            ai_response2 = chat_response2.json()
            content = ai_response2["choices"][0]["message"]["content"]
            logger.info(f"AI response: {content}")
            
            # Check if context was maintained
            assert "42" in content, f"AI should remember the number 42, but said: {content}"
            logger.info("✅ SUCCESS: AI remembered the context using web UI flow!")
    
    @pytest.mark.asyncio
    async def test_chat_unified_endpoint_with_conversation(self, chat_service_url, auth_url, user_factory):
        """Test the unified chat endpoint directly with conversation management."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        
        jwt_token = login_response["access_token"]
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create conversation first
            conv_response = await client.post(
                f"{chat_service_url}/conversations",
                headers=headers,
                json={"title": "Direct Test"}
            )
            assert conv_response.status_code in [200, 201]
            conversation_id = conv_response.json()["id"]
            
            # Test unified endpoint directly
            logger.info("Testing unified endpoint with conversation_id...")
            
            # First message
            response1 = await client.post(
                f"{chat_service_url}/chat/unified",
                headers=headers,
                json={
                    "message": "Remember: my pet is a golden retriever named Max",
                    "conversation_id": conversation_id
                }
            )
            assert response1.status_code == 200
            
            # Second message
            response2 = await client.post(
                f"{chat_service_url}/chat/unified",
                headers=headers,
                json={
                    "message": "What kind of pet do I have and what's its name?",
                    "conversation_id": conversation_id
                }
            )
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Check response format and content
            if "choices" in data2:
                content = data2["choices"][0]["message"]["content"]
            else:
                content = data2.get("response", "")
            
            logger.info(f"Unified endpoint response: {content}")
            
            # Verify context
            has_retriever = "retriever" in content.lower() or "golden" in content.lower()
            has_max = "max" in content.lower()
            
            assert has_retriever and has_max, f"AI should remember the pet details, but said: {content}"
            logger.info("✅ SUCCESS: Unified endpoint maintains context with conversation_id!")
    
    @pytest.mark.asyncio
    async def test_gateway_without_conversation_id(self, gateway_url, auth_url, user_factory):
        """Test what happens when we don't pass conversation_id (current failing case)."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        
        jwt_token = login_response["access_token"]
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message WITHOUT conversation_id
            logger.info("Sending first message without conversation_id...")
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "My favorite color is purple. Remember this."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            
            # Check if conversation_id is returned
            conv_id = None
            if "_metadata" in data1 and "conversation_id" in data1["_metadata"]:
                conv_id = data1["_metadata"]["conversation_id"]
                logger.info(f"Found conversation_id in metadata: {conv_id}")
            elif "conversation_id" in data1:
                conv_id = data1["conversation_id"]
                logger.info(f"Found conversation_id at top level: {conv_id}")
            else:
                logger.info("No conversation_id returned in response")
            
            # Second message
            logger.info("Sending second message...")
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "What is my favorite color?"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            content = data2["choices"][0]["message"]["content"]
            
            # This will likely fail without conversation_id
            if "purple" in content.lower():
                logger.info(f"✅ Context maintained without conversation_id: {content}")
            else:
                logger.info(f"❌ Context lost without conversation_id: {content}")
                logger.info("This is expected - the API needs conversation_id to maintain context")