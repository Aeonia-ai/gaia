"""
Test v1 API conversation persistence with different approaches.
Extracted from mixed version test file for better organization.
"""

import pytest
import httpx
import os
import json
from typing import Dict, Any
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestUserFactory

logger = setup_service_logger("test_v1_conversation_persistence")


class TestV1ConversationPersistence:
    """Test v1 API conversation context maintenance."""
    
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
            
            # v1 format validation
            assert "choices" in data1
            assert len(data1["choices"]) > 0
            assert "message" in data1["choices"][0]
            
            logger.info(f"V1 first response metadata: {data1.get('_metadata', {})}")
            
            # Check if conversation_id is in response
            conversation_id = None
            if "_metadata" in data1:
                conversation_id = data1["_metadata"].get("conversation_id")
                logger.info(f"V1 Conversation ID from metadata: {conversation_id}")
            
            # Try to find conversation_id in other places
            if not conversation_id and "conversation_id" in data1:
                conversation_id = data1["conversation_id"]
                logger.info(f"V1 Conversation ID from top level: {conversation_id}")
            
            # Second message - try without conversation_id first
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=api_headers,
                json={"message": "What is my favorite number?"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            content2 = data2["choices"][0]["message"]["content"]
            logger.info(f"V1 second response (no conv_id): {content2[:200]}...")
            
            # Check if context was maintained
            has_context = "42" in content2.lower()
            logger.info(f"V1 context maintained without conversation_id: {has_context}")
            
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
                logger.info(f"V1 third response (with conv_id): {content3[:200]}...")
                
                has_context_with_id = "42" in content3.lower()
                logger.info(f"V1 context maintained with conversation_id: {has_context_with_id}")
    
    @pytest.mark.asyncio
    async def test_v1_conversation_with_supabase_auth(self, gateway_url, auth_url, user_factory):
        """Test v1 conversation persistence with Supabase JWT auth."""
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
            
            # v1 format validation
            assert "choices" in data1
            
            # Log all possible conversation ID locations
            logger.info("V1: Checking for conversation ID in response:")
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
            logger.info(f"V1 JWT auth context maintained: {has_context}")
            logger.info(f"V1 Response excerpt: {content2[:200]}...")
    
    @pytest.mark.asyncio
    async def test_v1_explicit_conversation_creation(self, gateway_url, api_headers):
        """Test v1 explicit conversation creation if supported."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to create a conversation through v1 API
            # Note: v1 might not have explicit conversation endpoints
            conv_response = await client.post(
                f"{gateway_url}/api/v1/conversations",
                headers=api_headers,
                json={"title": "V1 Test Conversation"}
            )
            
            if conv_response.status_code in [200, 201]:
                conv_data = conv_response.json()
                conversation_id = conv_data.get("id") or conv_data.get("conversation_id")
                logger.info(f"V1 Created conversation: {conversation_id}")
                
                # Send message with explicit conversation ID
                msg_response = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=api_headers,
                    json={
                        "message": "Hello in v1 conversation",
                        "conversation_id": conversation_id
                    }
                )
                
                if msg_response.status_code == 200:
                    logger.info("V1: Successfully sent message to specific conversation")
                    data = msg_response.json()
                    assert "choices" in data
                else:
                    logger.info(f"V1: Message to conversation failed: {msg_response.status_code}")
            else:
                logger.info(f"V1: Conversation creation endpoint not available: {conv_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_v1_streaming_conversation_persistence(self, gateway_url, api_headers):
        """Test if v1 streaming maintains conversation context."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            conversation_id = None
            
            # First streaming message
            chunks1 = []
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v1/chat",
                headers=api_headers,
                json={
                    "message": "My favorite programming language is Python. Remember this.",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        chunks1.append(data_str)
                        
                        # Look for conversation_id in streaming chunks
                        if data_str != "[DONE]":
                            try:
                                chunk_data = json.loads(data_str)
                                if not conversation_id and "conversation_id" in chunk_data:
                                    conversation_id = chunk_data["conversation_id"]
                                elif not conversation_id and "_metadata" in chunk_data:
                                    conversation_id = chunk_data["_metadata"].get("conversation_id")
                            except json.JSONDecodeError:
                                continue
            
            logger.info(f"V1 streaming: Found conversation_id: {conversation_id}")
            
            # Second message to test persistence
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=api_headers,
                json={
                    "message": "What is my favorite programming language?",
                    "conversation_id": conversation_id
                } if conversation_id else {
                    "message": "What is my favorite programming language?"
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            content2 = data2["choices"][0]["message"]["content"]
            
            has_context = "python" in content2.lower()
            logger.info(f"V1 streaming context maintained: {has_context}")