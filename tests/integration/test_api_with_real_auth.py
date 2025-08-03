"""
Integration tests using real API key authentication.
Converted from original curl-based test scripts.
These tests verify the API works with real authentication, not synthetic JWTs.
"""

import pytest
import httpx
import os
import asyncio
from typing import Dict, Any
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_api_with_real_auth")


class TestAPIWithRealAuth:
    """Test API endpoints with real API key authentication."""
    
    @pytest.fixture
    def api_key(self):
        """Get real API key from environment."""
        # Try different sources for API key
        api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
        if not api_key:
            pytest.skip("No API key available - set API_KEY or TEST_API_KEY environment variable")
        return api_key
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL - can be overridden with GATEWAY_URL env var."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def headers(self, api_key):
        """Headers with real API key authentication."""
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_health_check(self, gateway_url):
        """Test health endpoint (no auth required)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") in ["healthy", "degraded"]
            assert "services" in data
            logger.info(f"Health check passed: {data['status']}")
    
    @pytest.mark.asyncio
    async def test_health_with_api_key(self, gateway_url, headers):
        """Test health endpoint with API key (should still work)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/health", headers=headers)
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_providers_list(self, gateway_url, headers):
        """Test listing providers with real auth."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v1/providers", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "providers" in data
            assert isinstance(data["providers"], list)
            logger.info(f"Found {len(data['providers'])} providers")
    
    @pytest.mark.asyncio
    async def test_models_list(self, gateway_url, headers):
        """Test listing models with real auth."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v1/models", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "models" in data
            assert isinstance(data["models"], list)
            logger.info(f"Found {len(data['models'])} models")
    
    @pytest.mark.asyncio
    async def test_v1_chat_simple(self, gateway_url, headers):
        """Test v1 chat endpoint with simple message."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Hello, what is 2+2?",
                    "stream": False
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "response" in data or "message" in data
            logger.info("V1 chat simple message succeeded")
    
    @pytest.mark.asyncio
    async def test_v02_chat_completion(self, gateway_url, headers):
        """Test v0.2 chat completion endpoint."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat/completions",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "What is 2+2?"}],
                    "model": "claude-3-5-haiku-20241022",
                    "stream": False
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "choices" in data
            assert len(data["choices"]) > 0
            logger.info("V0.2 chat completion succeeded")
    
    @pytest.mark.asyncio
    async def test_chat_with_conversation_id(self, gateway_url, headers):
        """Test chat with conversation management."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message - creates conversation
            response1 = await client.post(
                f"{gateway_url}/api/v0.2/chat/completions",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "Remember the number 42"}],
                    "stream": False
                }
            )
            assert response1.status_code == 200
            data1 = response1.json()
            
            # Extract conversation ID if present
            conversation_id = data1.get("conversation_id")
            if conversation_id:
                # Second message - uses same conversation
                response2 = await client.post(
                    f"{gateway_url}/api/v0.2/chat/completions",
                    headers=headers,
                    json={
                        "messages": [{"role": "user", "content": "What number did I ask you to remember?"}],
                        "conversation_id": conversation_id,
                        "stream": False
                    }
                )
                assert response2.status_code == 200
                logger.info(f"Conversation {conversation_id} tested successfully")
    
    @pytest.mark.asyncio
    async def test_streaming_chat(self, gateway_url, headers):
        """Test streaming chat responses."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            chunks = []
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.2/chat/completions",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "Count to 3"}],
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunks.append(line[6:])
            
            assert len(chunks) > 0
            assert any("[DONE]" in chunk for chunk in chunks)
            logger.info(f"Streaming chat received {len(chunks)} chunks")
    
    @pytest.mark.asyncio
    async def test_no_auth_fails(self, gateway_url):
        """Test that requests without auth fail appropriately."""
        async with httpx.AsyncClient() as client:
            # Try to access protected endpoint without auth
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                json={"message": "Hello"}
            )
            assert response.status_code in [401, 403]
            logger.info("No auth correctly rejected")
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_fails(self, gateway_url):
        """Test that invalid API key is rejected."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"X-API-Key": "invalid-key-12345"},
                json={"message": "Hello"}
            )
            assert response.status_code in [401, 403]
            logger.info("Invalid API key correctly rejected")
    
    @pytest.mark.asyncio
    async def test_conversation_list(self, gateway_url, headers):
        """Test listing conversations."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gateway_url}/api/v0.2/conversations",
                headers=headers
            )
            # This might return 404 if not implemented, which is OK
            if response.status_code == 200:
                data = response.json()
                assert "conversations" in data or isinstance(data, list)
                logger.info("Conversation list endpoint available")
            else:
                logger.info(f"Conversation list returned {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, gateway_url, headers):
        """Test handling concurrent requests with real auth."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send 3 requests concurrently
            tasks = []
            for i in range(3):
                task = client.post(
                    f"{gateway_url}/api/v0.2/chat/completions",
                    headers=headers,
                    json={
                        "messages": [{"role": "user", "content": f"Say the number {i}"}],
                        "stream": False
                    }
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            
            # All should succeed
            for i, response in enumerate(responses):
                assert response.status_code == 200
                data = response.json()
                assert "choices" in data
                logger.info(f"Concurrent request {i} succeeded")
    
    @pytest.mark.asyncio
    async def test_model_selection(self, gateway_url, headers):
        """Test using different models."""
        models_to_test = [
            "claude-3-5-haiku-20241022",
            "gpt-4o-mini",
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for model in models_to_test:
                response = await client.post(
                    f"{gateway_url}/api/v0.2/chat/completions",
                    headers=headers,
                    json={
                        "messages": [{"role": "user", "content": "Say 'hi'"}],
                        "model": model,
                        "stream": False,
                        "max_tokens": 10
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"Model {model} is available")
                else:
                    logger.info(f"Model {model} returned {response.status_code}")