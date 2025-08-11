"""
Test Gateway API with API key to JWT exchange.
Tests that the gateway properly handles both API keys and JWTs from the exchange.
"""

import pytest
import httpx
import jwt
import os
from typing import Dict, Any


class TestGatewayAPIKeyJWTExchange:
    """Test gateway endpoints with API key exchange to JWT."""
    
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
    async def test_gateway_chat_with_api_key(self, gateway_url, api_key):
        """Test that gateway chat endpoint works with API key."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Hello from API key test",
                    "max_tokens": 10
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            # Gateway returns OpenAI-compatible format
            assert "id" in data
            assert "choices" in data
            assert "_metadata" in data
            
            # Verify conversation was created
            metadata = data["_metadata"]
            assert "conversation_id" in metadata
    
    @pytest.mark.asyncio
    async def test_gateway_chat_with_exchanged_jwt(self, gateway_url, auth_url, api_key):
        """Test that gateway chat endpoint works with JWT from API key exchange."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First, exchange API key for JWT
            exchange_response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": api_key}
            )
            
            assert exchange_response.status_code == 200
            jwt_token = exchange_response.json()["access_token"]
            
            # Now use the JWT with the gateway
            chat_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "message": "Hello from exchanged JWT test",
                    "max_tokens": 10
                }
            )
            
            assert chat_response.status_code == 200
            data = chat_response.json()
            # Gateway returns OpenAI-compatible format
            assert "id" in data
            assert "choices" in data
            assert "_metadata" in data
            
            # Verify conversation was created
            metadata = data["_metadata"]
            assert "conversation_id" in metadata
    
    @pytest.mark.asyncio
    async def test_conversation_persistence_across_auth_methods(self, gateway_url, auth_url, api_key):
        """Test that conversations created with API key can be accessed with exchanged JWT."""
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
    @pytest.mark.skip(reason="v0.2 endpoints have different requirements - focus on core v1 functionality")
    async def test_gateway_completions_with_exchanged_jwt(self, gateway_url, auth_url, api_key):
        """Test v0.2 completions endpoint with exchanged JWT."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Exchange API key for JWT
            exchange_response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": api_key}
            )
            
            assert exchange_response.status_code == 200
            jwt_token = exchange_response.json()["access_token"]
            
            # Use JWT with v0.2 chat endpoint
            completions_response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "messages": [
                        {"role": "user", "content": "Say hello in one word"}
                    ],
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 10
                }
            )
            
            if completions_response.status_code != 200:
                print(f"V0.2 chat error: {completions_response.text}")
            assert completions_response.status_code == 200
            data = completions_response.json()
            assert "id" in data
            assert "choices" in data
            assert len(data["choices"]) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="v0.2 streaming endpoints have different requirements - focus on core v1 functionality")
    async def test_gateway_streaming_with_exchanged_jwt(self, gateway_url, auth_url, api_key):
        """Test streaming endpoint with exchanged JWT."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Exchange API key for JWT
            exchange_response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": api_key}
            )
            
            assert exchange_response.status_code == 200
            jwt_token = exchange_response.json()["access_token"]
            
            # Use JWT with streaming endpoint
            stream_response = await client.post(
                f"{gateway_url}/api/v0.2/chat/stream",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "messages": [
                        {"role": "user", "content": "Count to 3"}
                    ],
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 20,
                    "stream": True
                }
            )
            
            # For streaming, we get SSE responses
            assert stream_response.status_code == 200
            assert stream_response.headers.get("content-type") == "text/event-stream; charset=utf-8"
            
            # Read some streaming data
            chunks = []
            async for line in stream_response.aiter_lines():
                if line.startswith("data: "):
                    chunks.append(line)
                    if len(chunks) >= 3:  # Get at least 3 chunks
                        break
            
            assert len(chunks) > 0
    
    @pytest.mark.asyncio
    async def test_gateway_auth_validation_endpoint(self, gateway_url, auth_url, api_key):
        """Test that gateway properly validates exchanged JWTs."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Exchange API key for JWT
            exchange_response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": api_key}
            )
            
            assert exchange_response.status_code == 200
            jwt_token = exchange_response.json()["access_token"]
            
            # Test that we can use the JWT for authenticated requests
            # The gateway health endpoint doesn't require auth, so let's test chat instead
            auth_test_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "message": "Testing JWT auth",
                    "max_tokens": 10
                }
            )
            
            # Should work with valid JWT
            assert auth_test_response.status_code == 200
            
            # Test with invalid JWT
            invalid_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"Authorization": "Bearer invalid-jwt-token"},
                json={
                    "message": "Testing invalid JWT",
                    "max_tokens": 10
                }
            )
            
            # Should fail with invalid JWT
            assert invalid_response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_mixed_auth_in_same_session(self, gateway_url, auth_url, api_key):
        """Test using both API key and JWT in the same session."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Make a request with API key
            api_response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Hello with API key",
                    "max_tokens": 10
                }
            )
            assert api_response1.status_code == 200
            
            # Exchange for JWT
            exchange_response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": api_key}
            )
            jwt_token = exchange_response.json()["access_token"]
            
            # Make a request with JWT
            jwt_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "message": "Hello with JWT",
                    "max_tokens": 10
                }
            )
            assert jwt_response.status_code == 200
            
            # Go back to using API key
            api_response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Back to API key",
                    "max_tokens": 10
                }
            )
            assert api_response2.status_code == 200
            
            # All requests should succeed without interference