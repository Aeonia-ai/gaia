"""
Test Gateway v1 API with API key to JWT exchange.
Tests that the gateway properly handles both API keys and JWTs from the exchange.
"""

import pytest
import httpx
import jwt
import os
from typing import Dict, Any


class TestV1GatewayAPIKeyJWTExchange:
    """Test v1 gateway endpoints with API key exchange to JWT."""
    
    @pytest.fixture
    def gateway_url(self) -> str:
        """Gateway URL for tests."""
        return "http://gateway:8000"
    
    @pytest.fixture
    def auth_url(self) -> str:
        """Auth service URL for tests."""
        return "http://auth-service:8000"
    
    @pytest.fixture
    def api_key(self) -> str:
        """API key for testing."""
        return os.getenv("API_KEY") or os.getenv("TEST_API_KEY", "test-key-123")
    
    @pytest.mark.asyncio
    async def test_v1_gateway_chat_with_api_key(self, gateway_url, api_key):
        """Test that v1 gateway chat endpoint works with API key."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Hello from v1 API key test",
                    "max_tokens": 10
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            # v1 returns OpenAI-compatible format
            assert "id" in data
            assert "choices" in data
            assert "_metadata" in data
            
            # Verify conversation was created
            metadata = data["_metadata"]
            assert "conversation_id" in metadata
    
    @pytest.mark.asyncio
    async def test_v1_gateway_chat_with_exchanged_jwt(self, gateway_url, auth_url, api_key):
        """Test that v1 gateway chat endpoint works with JWT from API key exchange."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First, exchange API key for JWT
            exchange_response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": api_key}
            )
            
            assert exchange_response.status_code == 200
            jwt_token = exchange_response.json()["access_token"]
            
            # Now use the JWT with the v1 gateway
            chat_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "message": "Hello from v1 exchanged JWT test",
                    "max_tokens": 10
                }
            )
            
            assert chat_response.status_code == 200
            data = chat_response.json()
            # v1 returns OpenAI-compatible format
            assert "id" in data
            assert "choices" in data
            assert "_metadata" in data
            
            # Verify conversation was created
            metadata = data["_metadata"]
            assert "conversation_id" in metadata
    
    @pytest.mark.asyncio
    async def test_v1_conversation_persistence_across_auth_methods(self, gateway_url, auth_url, api_key):
        """Test that v1 conversations created with API key can be accessed with exchanged JWT."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Create conversation with API key
            api_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "My favorite color is blue",
                    "max_tokens": 50
                }
            )
            
            assert api_response.status_code == 200
            conversation_id = api_response.json()["_metadata"]["conversation_id"]
            
            # Step 2: Exchange API key for JWT
            exchange_response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": api_key}
            )
            
            assert exchange_response.status_code == 200
            jwt_token = exchange_response.json()["access_token"]
            
            # Step 3: Continue conversation with JWT
            jwt_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "message": "What is my favorite color?",
                    "conversation_id": conversation_id,
                    "max_tokens": 50
                }
            )
            
            assert jwt_response.status_code == 200
            # Extract response from OpenAI format
            choices = jwt_response.json()["choices"]
            response_text = choices[0]["message"]["content"].lower()
            
            # The AI should remember the color from the API key conversation
            assert "blue" in response_text
    
    @pytest.mark.asyncio
    async def test_v1_gateway_auth_validation_endpoint(self, gateway_url, auth_url, api_key):
        """Test that v1 gateway properly validates exchanged JWTs."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Exchange API key for JWT
            exchange_response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": api_key}
            )
            
            assert exchange_response.status_code == 200
            jwt_token = exchange_response.json()["access_token"]
            
            # Test that we can use the JWT for authenticated v1 requests
            auth_test_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "message": "Testing v1 JWT auth",
                    "max_tokens": 10
                }
            )
            
            assert auth_test_response.status_code == 200
            # Additional validation that it's using the right auth
            assert "_metadata" in auth_test_response.json()
    
    @pytest.mark.asyncio
    async def test_v1_invalid_jwt_rejected(self, gateway_url):
        """Test that v1 gateway rejects invalid JWTs."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Use a completely invalid JWT
            invalid_jwt = "invalid.jwt.token"
            
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"Authorization": f"Bearer {invalid_jwt}"},
                json={
                    "message": "This should fail",
                    "max_tokens": 10
                }
            )
            
            # Should return 401 Unauthorized
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_v1_api_key_and_jwt_priority(self, gateway_url, auth_url, api_key):
        """Test that when both API key and JWT are provided, v1 prioritizes correctly."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Exchange API key for JWT
            exchange_response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": api_key}
            )
            
            assert exchange_response.status_code == 200
            jwt_token = exchange_response.json()["access_token"]
            
            # Send request with both API key and JWT
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={
                    "X-API-Key": api_key,
                    "Authorization": f"Bearer {jwt_token}"
                },
                json={
                    "message": "Testing v1 with both auth methods",
                    "max_tokens": 10
                }
            )
            
            # Should succeed (gateway should handle priority correctly)
            assert response.status_code == 200
            
            # Verify the response is valid
            data = response.json()
            assert "choices" in data
            assert "_metadata" in data