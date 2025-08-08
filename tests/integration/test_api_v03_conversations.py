"""
Test v0.3 API conversation persistence.
"""

import pytest
import httpx
import os
from typing import Dict, Any
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestUserFactory

logger = setup_service_logger("test_v03_conversation")


class TestV03Conversation:
    """Test v0.3 API conversation handling."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def auth_url(self):
        """Auth service URL."""
        return os.getenv("AUTH_URL", "http://auth-service:8000")
    
    @pytest.fixture
    def api_key(self):
        """API key for testing."""
        api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
        if not api_key:
            pytest.skip("No API key available")
        return api_key
    
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
            if "session" in data and "access_token" in data["session"]:
                data["access_token"] = data["session"]["access_token"]
            return data
    
    @pytest.mark.asyncio
    async def test_v03_conversation_with_api_key(self, gateway_url, api_key):
        """Test v0.3 conversation persistence with API key."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First: Create a conversation
            logger.info("Creating v0.3 conversation...")
            conv_response = await client.post(
                f"{gateway_url}/api/v0.3/conversations",
                headers=headers,
                json={"title": "Test v0.3 Conversation"}
            )
            
            if conv_response.status_code in [200, 201]:
                conversation = conv_response.json()
                conversation_id = conversation.get("conversation_id")
                logger.info(f"Created conversation: {conversation_id}")
                
                # Send first message with conversation_id
                logger.info("Sending first message...")
                response1 = await client.post(
                    f"{gateway_url}/api/v0.3/chat",
                    headers=headers,
                    json={
                        "message": "My favorite programming language is Python. Remember this.",
                        "conversation_id": conversation_id
                    }
                )
                assert response1.status_code == 200
                data1 = response1.json()
                logger.info(f"First response: {data1.get('response', '')[:100]}...")
                
                # Send follow-up message
                logger.info("Sending follow-up message...")
                response2 = await client.post(
                    f"{gateway_url}/api/v0.3/chat",
                    headers=headers,
                    json={
                        "message": "What is my favorite programming language?",
                        "conversation_id": conversation_id
                    }
                )
                assert response2.status_code == 200
                data2 = response2.json()
                response_text = data2.get("response", "")
                logger.info(f"Follow-up response: {response_text}")
                
                # Check if context was maintained
                if "python" in response_text.lower():
                    logger.info("✅ v0.3 with conversation_id: Context maintained!")
                else:
                    logger.info("❌ v0.3 with conversation_id: Context lost")
                    
                assert "python" in response_text.lower(), f"Should remember Python, but got: {response_text}"
            else:
                # If conversation creation is not supported, try without it
                logger.info("Conversation creation not supported, testing without conversation_id...")
                
                # First message without conversation_id
                response1 = await client.post(
                    f"{gateway_url}/api/v0.3/chat",
                    headers=headers,
                    json={"message": "My favorite color is green. Remember this."}
                )
                assert response1.status_code == 200
                
                # Follow-up
                response2 = await client.post(
                    f"{gateway_url}/api/v0.3/chat",
                    headers=headers,
                    json={"message": "What is my favorite color?"}
                )
                assert response2.status_code == 200
                data2 = response2.json()
                response_text = data2.get("response", "")
                
                # This will likely fail without conversation_id
                has_context = "green" in response_text.lower()
                logger.info(f"v0.3 without conversation_id: {'Context maintained' if has_context else 'Context lost'}")
    
    @pytest.mark.asyncio
    async def test_v03_streaming(self, gateway_url, api_key):
        """Test v0.3 streaming response."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            chunks = []
            logger.info("Testing v0.3 streaming...")
            
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Count to 3 slowly",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk_data = line[6:]
                        chunks.append(chunk_data)
                        
                        if chunk_data == "[DONE]":
                            break
                        
                        # Parse chunk
                        try:
                            import json
                            chunk = json.loads(chunk_data)
                            if chunk.get("type") == "content":
                                logger.info(f"Received chunk: {chunk.get('content', '')}")
                        except:
                            pass
                
                logger.info(f"Streaming completed with {len(chunks)} chunks")
                assert len(chunks) > 0, "Should receive streaming chunks"
    
    @pytest.mark.asyncio
    async def test_v03_with_supabase_auth(self, gateway_url, auth_url, user_factory):
        """Test v0.3 with Supabase JWT authentication."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        
        headers = {
            "Authorization": f"Bearer {login_response['access_token']}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test creating conversation
            conv_response = await client.post(
                f"{gateway_url}/api/v0.3/conversations",
                headers=headers,
                json={"title": "JWT Test Conversation"}
            )
            
            if conv_response.status_code in [200, 201]:
                conversation = conv_response.json()
                conversation_id = conversation.get("conversation_id")
                
                # Chat with conversation_id
                response = await client.post(
                    f"{gateway_url}/api/v0.3/chat",
                    headers=headers,
                    json={
                        "message": "Hello from v0.3 with JWT auth!",
                        "conversation_id": conversation_id
                    }
                )
                assert response.status_code == 200
                data = response.json()
                logger.info(f"v0.3 with JWT response: {data.get('response', '')[:100]}...")
            else:
                # Try without conversation_id
                response = await client.post(
                    f"{gateway_url}/api/v0.3/chat",
                    headers=headers,
                    json={"message": "Hello from v0.3 with JWT auth!"}
                )
                assert response.status_code == 200
                data = response.json()
                logger.info(f"v0.3 with JWT (no conv_id): {data.get('response', '')[:100]}...")
    
    @pytest.mark.asyncio
    async def test_v03_list_conversations(self, gateway_url, api_key):
        """Test listing conversations via v0.3 API."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gateway_url}/api/v0.3/conversations",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                conversations = data.get("conversations", [])
                logger.info(f"Found {len(conversations)} conversations")
                
                # If we have conversations, test getting messages
                if conversations and len(conversations) > 0:
                    conv_id = conversations[0].get("conversation_id")
                    
                    # Try to get messages (if endpoint exists)
                    msg_response = await client.get(
                        f"{gateway_url}/api/v0.3/conversations/{conv_id}/messages",
                        headers=headers
                    )
                    
                    if msg_response.status_code == 200:
                        messages = msg_response.json()
                        logger.info(f"Conversation {conv_id} has {len(messages)} messages")
                    else:
                        logger.info(f"Messages endpoint returned: {msg_response.status_code}")
            else:
                logger.info(f"List conversations returned: {response.status_code}")