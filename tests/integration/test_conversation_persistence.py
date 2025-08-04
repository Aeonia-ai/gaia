"""
Test conversation persistence with different approaches.
This test investigates why conversation context is lost between messages.
"""

import pytest
import httpx
import os
import json
from typing import Dict, Any
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestUserFactory

logger = setup_service_logger("test_conversation_persistence")


class TestConversationPersistence:
    """Test different approaches to maintaining conversation context."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def chat_url(self):
        """Direct chat service URL."""
        return os.getenv("CHAT_URL", "http://chat-service:8000")
    
    @pytest.fixture
    def auth_url(self):
        """Auth service URL."""
        return os.getenv("AUTH_URL", "http://auth-service:8000")
    
    @pytest.fixture
    def api_key(self):
        """Get API key for testing."""
        api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
        if not api_key:
            pytest.skip("No API key available")
        return api_key
    
    @pytest.fixture
    def api_headers(self, api_key):
        """Headers with API key auth."""
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
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
    async def test_v1_chat_persistence_with_api_key(self, gateway_url, api_headers):
        """Test if v1 chat maintains context with API key auth."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=api_headers,
                json={"message": "My favorite number is 42. Please remember this."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            logger.info(f"First response metadata: {data1.get('_metadata', {})}")
            
            # Check if conversation_id is in response
            conversation_id = None
            if "_metadata" in data1:
                conversation_id = data1["_metadata"].get("conversation_id")
                logger.info(f"Conversation ID from metadata: {conversation_id}")
            
            # Try to find conversation_id in other places
            if not conversation_id and "conversation_id" in data1:
                conversation_id = data1["conversation_id"]
                logger.info(f"Conversation ID from top level: {conversation_id}")
            
            # Second message - try without conversation_id first
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=api_headers,
                json={"message": "What is my favorite number?"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            content2 = data2["choices"][0]["message"]["content"]
            logger.info(f"Second response (no conv_id): {content2[:200]}...")
            
            # Check if context was maintained
            has_context = "42" in content2.lower()
            logger.info(f"Context maintained without conversation_id: {has_context}")
            
            # If we have a conversation_id, try with it
            if conversation_id:
                response3 = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=api_headers,
                    json={
                        "message": "What is my favorite number?",
                        "conversation_id": conversation_id
                    }
                )
                assert response3.status_code == 200
                data3 = response3.json()
                content3 = data3["choices"][0]["message"]["content"]
                logger.info(f"Third response (with conv_id): {content3[:200]}...")
                
                has_context_with_id = "42" in content3.lower()
                logger.info(f"Context maintained with conversation_id: {has_context_with_id}")
    
    @pytest.mark.asyncio
    async def test_v02_chat_persistence(self, gateway_url, api_headers):
        """Test if v0.2 chat endpoint maintains context."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=api_headers,
                json={"message": "My favorite color is blue. Remember this."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            logger.info(f"v0.2 response structure: {list(data1.keys())}")
            
            # Second message
            response2 = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=api_headers,
                json={"message": "What is my favorite color?"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            content2 = data2.get("response", "")
            logger.info(f"v0.2 second response: {content2[:200]}...")
            
            has_context = "blue" in content2.lower()
            logger.info(f"v0.2 context maintained: {has_context}")
    
    @pytest.mark.asyncio
    async def test_direct_chat_endpoints(self, chat_url, api_headers):
        """Test direct chat service endpoints for conversation support."""
        endpoints_to_test = [
            ("/chat", "Basic chat endpoint"),
            ("/chat/direct", "Direct chat endpoint"),
            ("/chat/direct-db", "Database-backed chat"),
            ("/chat/unified", "Unified chat endpoint")
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint, description in endpoints_to_test:
                try:
                    # Send a test message
                    response = await client.post(
                        f"{chat_url}{endpoint}",
                        headers=api_headers,
                        json={"message": "Hello, testing conversation support"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"{description} ({endpoint}): SUCCESS")
                        logger.info(f"  Response keys: {list(data.keys())}")
                        
                        # Check for conversation_id
                        if "conversation_id" in data:
                            logger.info(f"  Has conversation_id at top level")
                        elif "_metadata" in data and "conversation_id" in data["_metadata"]:
                            logger.info(f"  Has conversation_id in metadata")
                        else:
                            logger.info(f"  No conversation_id found")
                    else:
                        logger.info(f"{description} ({endpoint}): {response.status_code}")
                except Exception as e:
                    logger.info(f"{description} ({endpoint}): ERROR - {e}")
    
    @pytest.mark.asyncio
    async def test_conversation_with_supabase_auth(self, gateway_url, auth_url, user_factory):
        """Test conversation persistence with Supabase JWT auth."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        
        headers = {"Authorization": f"Bearer {login_response['access_token']}"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "My name is TestBot. Remember my name."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            
            # Log all possible conversation ID locations
            logger.info("Checking for conversation ID in response:")
            logger.info(f"  Top level keys: {list(data1.keys())}")
            if "_metadata" in data1:
                logger.info(f"  Metadata keys: {list(data1['_metadata'].keys())}")
            
            # Second message without conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "What is my name?"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            content2 = data2["choices"][0]["message"]["content"]
            
            has_context = "testbot" in content2.lower()
            logger.info(f"JWT auth context maintained: {has_context}")
            logger.info(f"Response excerpt: {content2[:200]}...")
    
    @pytest.mark.asyncio
    async def test_explicit_conversation_endpoints(self, gateway_url, api_headers):
        """Test endpoints that explicitly handle conversations."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to create a conversation first
            conv_response = await client.post(
                f"{gateway_url}/api/v0.2/conversations",
                headers=api_headers,
                json={"name": "Test Conversation"}
            )
            
            if conv_response.status_code == 200:
                conv_data = conv_response.json()
                conversation_id = conv_data.get("id") or conv_data.get("conversation_id")
                logger.info(f"Created conversation: {conversation_id}")
                
                # Send message to specific conversation
                msg_response = await client.post(
                    f"{gateway_url}/api/v0.2/conversations/{conversation_id}/messages",
                    headers=api_headers,
                    json={"message": "Hello in specific conversation"}
                )
                
                if msg_response.status_code == 200:
                    logger.info("Successfully sent message to specific conversation")
                else:
                    logger.info(f"Message to conversation failed: {msg_response.status_code}")
            else:
                logger.info(f"Conversation creation endpoint not available: {conv_response.status_code}")