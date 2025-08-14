"""
Integration tests for v1 API using real API key authentication.
Extracted from mixed v1/v0.3 test file for better test organization.
These tests verify the v1 API works with real authentication, not synthetic JWTs.
"""

import pytest
import httpx
import os
import asyncio
from typing import Dict, Any
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_api_v1_with_real_auth")


class TestV1APIWithRealAuth:
    """Test v1 API endpoints with real API key authentication."""
    
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
            # v1 typically returns OpenAI-compatible format with choices
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]
            assert "content" in data["choices"][0]["message"]
            logger.info("V1 chat simple message succeeded")
    
    @pytest.mark.asyncio
    async def test_v1_chat_streaming(self, gateway_url, headers):
        """Test v1 chat with streaming (as web UI uses it)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            chunks = []
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Count to 3",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunks.append(line[6:])
            
            assert len(chunks) > 0
            # Should have content chunks and a [DONE] marker
            assert any("[DONE]" in chunk for chunk in chunks)
            logger.info(f"V1 streaming chat received {len(chunks)} chunks")
    
    @pytest.mark.asyncio
    async def test_v1_chat_with_conversation_context(self, gateway_url, headers):
        """Test v1 chat with conversation management if supported."""
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
            
            # Check if conversation ID is returned in v1 format
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
                logger.info(f"V1 conversation {conversation_id} tested successfully")
            else:
                logger.info("V1 conversation management not available in response")
    
    @pytest.mark.asyncio
    async def test_v1_model_selection(self, gateway_url, headers):
        """Test v1 API with different models."""
        models_to_test = [
            "claude-3-5-haiku-20241022",
            "gpt-4o-mini",
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            available_models = []
            for model in models_to_test:
                response = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={
                        "message": "Say 'hi'",
                        "model": model,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    available_models.append(model)
                    logger.info(f"V1 API: Model {model} is available")
                else:
                    logger.info(f"V1 API: Model {model} returned {response.status_code}")
            
            # At least one model should be available
            assert len(available_models) > 0, "No models available for v1 API"
    
    @pytest.mark.asyncio
    async def test_v1_auth_validation(self, gateway_url):
        """Test that v1 API properly validates authentication."""
        async with httpx.AsyncClient() as client:
            # Try to access v1 endpoint without auth
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                json={"message": "Hello"}
            )
            assert response.status_code == 401
            logger.info("V1 API: No auth correctly rejected")
    
    @pytest.mark.asyncio
    async def test_v1_invalid_api_key_fails(self, gateway_url):
        """Test that v1 API rejects invalid API key."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers={"X-API-Key": "invalid-key-12345"},
                json={"message": "Hello"}
            )
            assert response.status_code == 401
            logger.info("V1 API: Invalid API key correctly rejected")
    
    @pytest.mark.asyncio
    async def test_v1_response_metadata(self, gateway_url, headers):
        """Test v1 response metadata if available."""
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
            
            # Check for v1 metadata
            if "_metadata" in data:
                metadata = data["_metadata"]
                logger.info(f"V1 response metadata: {metadata}")
                
                # Common v1 metadata fields
                if "route_type" in metadata:
                    logger.info(f"  V1 Route type: {metadata['route_type']}")
                if "total_time_ms" in metadata:
                    logger.info(f"  V1 Total time: {metadata['total_time_ms']}ms")
                if "model" in data:
                    logger.info(f"  V1 Model used: {data['model']}")
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Moved to load tests - see tests/load/test_concurrent_requests.py")
    async def test_v1_concurrent_requests(self, gateway_url, headers):
        """Test v1 API handling concurrent requests with real auth.
        
        This test has been moved to the load test suite because it:
        - Tests system behavior under load, not integration correctness
        - Can trigger rate limits on external APIs
        - Has non-deterministic timing requirements
        
        For integration testing of multi-request scenarios, see:
        - test_v1_chat_with_conversation_context (sequential requests)
        - test_v1_model_selection (different model handling)
        """
        pass  # Moved to load tests