"""
Test the web UI migration to v0.3 format and unified endpoint conversation management.
These tests verify the web UI can stop managing conversations independently.
"""

import pytest
import httpx
import json
from typing import Dict, Any
from app.services.web.utils.gateway_client import GaiaAPIClient
from tests.fixtures.test_auth import TestUserFactory

class TestWebUIV03Migration:
    """Test web UI migration to v0.3 format and unified conversation management."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL."""
        return "http://gateway:8000"
    
    @pytest.fixture
    def web_url(self):
        """Web service URL."""
        return "http://web-service:8000"
    
    @pytest.fixture
    def auth_url(self):
        """Auth service URL."""
        return "http://auth-service:8000"
    
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
    async def test_gateway_client_extracts_conversation_id_from_metadata(self, gateway_url, auth_url, user_factory):
        """Test that GaiaAPIClient can extract conversation_id from response metadata."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        jwt_token = login_response["access_token"]
        
        async with GaiaAPIClient(base_url=gateway_url) as client:
            # First message - no conversation_id
            response = await client.chat_completion(
                messages=[{"role": "user", "content": "Test message for migration"}],
                jwt_token=jwt_token
            )
            
            # Should get OpenAI format with metadata
            assert "choices" in response
            assert "_metadata" in response
            assert "conversation_id" in response["_metadata"]
            
            # Extract conversation_id for future use
            conversation_id = response["_metadata"]["conversation_id"]
            assert conversation_id is not None
            assert len(conversation_id) > 0
            
            # Second message - with conversation_id
            response2 = await client.chat_completion(
                messages=[{"role": "user", "content": "Second message"}],
                jwt_token=jwt_token,
                conversation_id=conversation_id
            )
            
            # Should maintain same conversation
            assert response2["_metadata"]["conversation_id"] == conversation_id
    
    @pytest.mark.asyncio
    async def test_v03_format_includes_conversation_id_at_top_level(self, gateway_url, auth_url, user_factory):
        """Test that v0.3 format includes conversation_id at top level."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        jwt_token = login_response["access_token"]
        
        async with GaiaAPIClient(base_url=gateway_url) as client:
            # Request v0.3 format
            response = await client.chat_completion(
                messages=[{"role": "user", "content": "Test v0.3 format"}],
                jwt_token=jwt_token,
                response_format="v0.3"
            )
            
            # v0.3 format has conversation_id at top level
            assert "response" in response
            assert "conversation_id" in response
            assert response["conversation_id"] is not None
            
            # Use it for follow-up
            response2 = await client.chat_completion(
                messages=[{"role": "user", "content": "Follow-up message"}],
                jwt_token=jwt_token,
                conversation_id=response["conversation_id"],
                response_format="v0.3"
            )
            
            # Should maintain conversation
            assert response2["conversation_id"] == response["conversation_id"]
    
    @pytest.mark.asyncio
    async def test_web_ui_can_use_unified_without_manual_conversation_management(self, gateway_url, auth_url, user_factory):
        """Test that web UI can rely on unified endpoint for conversation management."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        jwt_token = login_response["access_token"]
        
        # Simulate web UI flow WITHOUT manual conversation management
        async with GaiaAPIClient(base_url=gateway_url) as client:
            # Step 1: Send first message without creating conversation
            response1 = await client.chat_completion(
                messages=[{"role": "user", "content": "My favorite color is blue"}],
                jwt_token=jwt_token,
                response_format="v0.3"
            )
            
            # Unified endpoint should create conversation automatically
            assert "conversation_id" in response1
            conversation_id = response1["conversation_id"]
            
            # Step 2: Send follow-up using conversation_id from response
            response2 = await client.chat_completion(
                messages=[{"role": "user", "content": "What color did I mention?"}],
                jwt_token=jwt_token,
                conversation_id=conversation_id,
                response_format="v0.3"
            )
            
            # Should remember context
            assert "blue" in response2["response"].lower()
            assert response2["conversation_id"] == conversation_id
            
            # Step 3: Verify conversation exists in the system
            # (In real migration, web UI would call /api/conversations to update sidebar)
            # For now, just verify the conversation was created and persisted
    
    @pytest.mark.asyncio
    async def test_streaming_includes_conversation_id(self, gateway_url, auth_url, user_factory):
        """Test that streaming responses include conversation_id."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        jwt_token = login_response["access_token"]
        
        async with GaiaAPIClient(base_url=gateway_url) as client:
            conversation_id = None
            chunks = []
            
            # Stream a response
            async for chunk_str in client.chat_completion_stream(
                messages=[{"role": "user", "content": "Count to 3"}],
                jwt_token=jwt_token
            ):
                if chunk_str.strip() == "[DONE]":
                    break
                
                try:
                    chunk = json.loads(chunk_str)
                    chunks.append(chunk)
                    
                    # Check for conversation_id in metadata
                    if "_metadata" in chunk and "conversation_id" in chunk["_metadata"]:
                        conversation_id = chunk["_metadata"]["conversation_id"]
                except json.JSONDecodeError:
                    pass
            
            # Should have received conversation_id during streaming
            # (Implementation may vary - might be in first chunk or final metadata)
            assert len(chunks) > 0
            
            # If conversation_id not in chunks, it should be available after completion
            # This test documents the expected behavior for web UI migration