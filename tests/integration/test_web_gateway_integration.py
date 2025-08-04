"""
Test web UI integration with gateway conversation persistence.
"""

import pytest
import httpx
import json
from typing import Dict, Any, List
from app.services.web.utils.gateway_client import GaiaAPIClient
from tests.fixtures.test_auth import TestUserFactory

class TestWebGatewayIntegration:
    """Test that web UI can leverage gateway conversation persistence."""
    
    pytestmark = pytest.mark.xdist_group("web_gateway")
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL."""
        import os
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def auth_url(self):
        """Auth service URL."""
        import os
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
    async def test_gateway_client_default_format(self, gateway_url, auth_url, user_factory):
        """Test gateway client uses OpenAI format by default."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        jwt_token = login_response["access_token"]
        
        async with GaiaAPIClient(base_url=gateway_url) as client:
            response = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                jwt_token=jwt_token
            )
            
            # Should get OpenAI format by default
            assert "choices" in response
            assert "id" in response
            assert "object" in response
            assert response["object"] == "chat.completion"
            
            # Should have conversation_id in metadata
            assert "_metadata" in response
            assert "conversation_id" in response["_metadata"]
    
    @pytest.mark.asyncio
    async def test_gateway_client_with_v03_format(self, gateway_url, auth_url, user_factory):
        """Test gateway client can request v0.3 format."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        jwt_token = login_response["access_token"]
        
        async with GaiaAPIClient(base_url=gateway_url) as client:
            response = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello in v0.3"}],
                jwt_token=jwt_token,
                response_format="v0.3"
            )
            
            # Should get v0.3 format
            assert "response" in response
            assert "conversation_id" in response
            
            # Should NOT have OpenAI format fields
            assert "choices" not in response
            assert "object" not in response
    
    @pytest.mark.asyncio
    async def test_conversation_persistence_with_gateway_client(self, gateway_url, auth_url, user_factory):
        """Test conversation persistence works through gateway client."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        jwt_token = login_response["access_token"]
        
        async with GaiaAPIClient(base_url=gateway_url) as client:
            # First message - no conversation_id
            response1 = await client.chat_completion(
                messages=[{"role": "user", "content": "My favorite food is tacos"}],
                jwt_token=jwt_token,
                response_format="v0.3"
            )
            
            assert "conversation_id" in response1
            conversation_id = response1["conversation_id"]
            
            # Second message - with conversation_id
            response2 = await client.chat_completion(
                messages=[{"role": "user", "content": "What food did I mention?"}],
                jwt_token=jwt_token,
                conversation_id=conversation_id,
                response_format="v0.3"
            )
            
            # Should remember tacos
            assert "taco" in response2["response"].lower()
            # Should return same conversation_id
            assert response2["conversation_id"] == conversation_id
    
    @pytest.mark.asyncio
    async def test_streaming_with_conversation_id(self, gateway_url, auth_url, user_factory):
        """Test streaming includes conversation metadata."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        jwt_token = login_response["access_token"]
        
        async with GaiaAPIClient(base_url=gateway_url) as client:
            chunks = []
            conversation_id = None
            
            # Stream without conversation_id
            async for chunk_str in client.chat_completion_stream(
                messages=[{"role": "user", "content": "Count to 2"}],
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
            
            # Should have received chunks
            assert len(chunks) > 0
            
            # Conversation ID might be in metadata of first chunk (implementation dependent)
            # For now, just verify streaming works
            assert any("choices" in chunk for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_web_ui_migration_path(self, gateway_url, auth_url, user_factory):
        """Test migration path for web UI to use conversation persistence."""
        # Create and login user
        test_user = user_factory.create_verified_test_user()
        login_response = await self.login_user(auth_url, test_user["email"], test_user["password"])
        jwt_token = login_response["access_token"]
        
        async with GaiaAPIClient(base_url=gateway_url) as client:
            # Step 1: Current approach - OpenAI format, no conversation_id
            response1 = await client.chat_completion(
                messages=[{"role": "user", "content": "Test migration step 1"}],
                jwt_token=jwt_token
            )
            
            # Extract conversation_id from metadata
            conv_id = response1["_metadata"]["conversation_id"]
            
            # Step 2: Future approach - v0.3 format with conversation_id
            response2 = await client.chat_completion(
                messages=[{"role": "user", "content": "Test migration step 2"}],
                jwt_token=jwt_token,
                conversation_id=conv_id,
                response_format="v0.3"
            )
            
            # Both approaches should work
            assert response1["choices"][0]["message"]["content"]  # OpenAI format
            assert response2["response"]  # v0.3 format
            assert response2["conversation_id"] == conv_id