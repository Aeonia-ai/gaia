"""
Integration tests using real API key authentication.
Fixed version that handles actual response formats.
"""

import pytest
import httpx
import os
import asyncio
from typing import Dict, Any
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_api_with_real_auth")


class TestAPIWithRealAuthFixed:
    """Test API endpoints with real API key authentication - fixed for actual responses."""
    
    @pytest.fixture
    def api_key(self):
        """Get real API key from environment."""
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
    async def test_v1_chat_simple(self, gateway_url, headers):
        """Test v1 chat endpoint with correct response format."""
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
            
            # v1 returns OpenAI-compatible format
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]
            assert "content" in data["choices"][0]["message"]
            
            content = data["choices"][0]["message"]["content"]
            logger.info(f"V1 chat response: {content[:100]}...")
    
    @pytest.mark.asyncio
    async def test_v02_chat_completion(self, gateway_url, headers):
        """Test v0.2 chat completion endpoint."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First check if endpoint exists
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat/completions",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "What is 2+2?"}],
                    "model": "claude-3-5-haiku-20241022",
                    "stream": False
                }
            )
            
            if response.status_code == 404:
                pytest.skip("v0.2 chat completions endpoint not available")
            
            assert response.status_code == 200
            data = response.json()
            assert "choices" in data
            assert len(data["choices"]) > 0
            logger.info("V0.2 chat completion succeeded")
    
    @pytest.mark.asyncio
    async def test_providers_models_endpoints(self, gateway_url, headers):
        """Test providers and models endpoints availability."""
        endpoints = [
            ("/api/v1/providers", "providers"),
            ("/api/v1/models", "models"),
            ("/api/v0.2/providers", "providers"),
            ("/api/v0.2/models", "models")
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint, expected_key in endpoints:
                response = await client.get(f"{gateway_url}{endpoint}", headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"{endpoint} is available")
                    if expected_key in data:
                        logger.info(f"  Found {len(data[expected_key])} items")
                elif response.status_code == 404:
                    logger.info(f"{endpoint} not implemented (404)")
                else:
                    logger.warning(f"{endpoint} returned {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_chat_with_conversation(self, gateway_url, headers):
        """Test chat with conversation management if supported."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Remember the number 42",
                    "stream": False
                }
            )
            assert response1.status_code == 200
            data1 = response1.json()
            
            # Check if conversation ID is returned
            conversation_id = None
            if "conversation_id" in data1:
                conversation_id = data1["conversation_id"]
            elif "_metadata" in data1 and "conversation_id" in data1["_metadata"]:
                conversation_id = data1["_metadata"]["conversation_id"]
            
            if conversation_id:
                # Second message in same conversation
                response2 = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={
                        "message": "What number did I ask you to remember?",
                        "conversation_id": conversation_id,
                        "stream": False
                    }
                )
                assert response2.status_code == 200
                logger.info(f"Conversation {conversation_id} tested successfully")
            else:
                logger.info("Conversation management not available in response")
    
    @pytest.mark.asyncio
    async def test_streaming_chat(self, gateway_url, headers):
        """Test streaming chat if endpoint exists."""
        endpoints_to_try = [
            "/api/v1/chat",
            "/api/v0.2/chat/completions",
            "/api/v0.2/chat/stream"
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in endpoints_to_try:
                chunks = []
                try:
                    async with client.stream(
                        "POST",
                        f"{gateway_url}{endpoint}",
                        headers=headers,
                        json={
                            "message": "Count to 3",
                            "messages": [{"role": "user", "content": "Count to 3"}],
                            "stream": True
                        }
                    ) as response:
                        if response.status_code == 200:
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    chunks.append(line[6:])
                            
                            if len(chunks) > 0:
                                logger.info(f"Streaming worked on {endpoint} - received {len(chunks)} chunks")
                                return
                        elif response.status_code == 404:
                            continue
                except Exception as e:
                    logger.debug(f"Streaming failed on {endpoint}: {e}")
                    continue
            
            logger.info("No streaming endpoints available")
    
    @pytest.mark.asyncio
    async def test_auth_validation(self, gateway_url):
        """Test authentication validation."""
        async with httpx.AsyncClient() as client:
            # No auth should fail
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                json={"message": "Hello"}
            )
            assert response.status_code in [401, 403]
            
            # Invalid auth should fail
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"X-API-Key": "invalid-key-12345"},
                json={"message": "Hello"}
            )
            assert response.status_code in [401, 403]
            logger.info("Auth validation working correctly")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_real_auth(self, gateway_url, headers):
        """Test handling concurrent requests with real auth."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send 3 requests concurrently
            tasks = []
            for i in range(3):
                task = client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={
                        "message": f"Say the number {i}",
                        "stream": False
                    }
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            
            # All should succeed
            success_count = 0
            for i, response in enumerate(responses):
                if response.status_code == 200:
                    success_count += 1
                    data = response.json()
                    logger.info(f"Concurrent request {i} succeeded")
            
            assert success_count == 3, f"Only {success_count}/3 concurrent requests succeeded"
    
    @pytest.mark.asyncio
    async def test_response_metadata(self, gateway_url, headers):
        """Test response metadata if available."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What is 1+1?",
                    "stream": False
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            # Check for metadata
            if "_metadata" in data:
                metadata = data["_metadata"]
                logger.info(f"Response metadata: {metadata}")
                
                # Common metadata fields
                if "route_type" in metadata:
                    logger.info(f"  Route type: {metadata['route_type']}")
                if "total_time_ms" in metadata:
                    logger.info(f"  Total time: {metadata['total_time_ms']}ms")
                if "model" in data:
                    logger.info(f"  Model used: {data['model']}")
    
    @pytest.mark.asyncio 
    async def test_model_availability(self, gateway_url, headers):
        """Test which models are actually available."""
        models_to_test = [
            ("claude-3-5-haiku-20241022", "anthropic"),
            ("gpt-4o-mini", "openai"),
            ("gpt-3.5-turbo", "openai")
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            available_models = []
            
            for model, provider in models_to_test:
                response = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={
                        "message": "Say 'yes'",
                        "model": model,
                        "stream": False,
                        "max_tokens": 10
                    }
                )
                
                if response.status_code == 200:
                    available_models.append((model, provider))
                    logger.info(f"✓ Model {model} ({provider}) is available")
                else:
                    logger.info(f"✗ Model {model} ({provider}) returned {response.status_code}")
            
            assert len(available_models) > 0, "No models available"
            logger.info(f"Found {len(available_models)} working models")