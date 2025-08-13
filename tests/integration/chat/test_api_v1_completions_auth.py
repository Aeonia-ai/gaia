"""
Integration tests for v1 API completions using real API key authentication.
Extracted from mixed v1/v0.2 test file for better test organization.
"""

import pytest
import httpx
import os
import asyncio
from typing import Dict, Any
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_api_v1_completions_auth")


class TestV1CompletionsWithRealAuth:
    """Test v1 API completion endpoints with real API key authentication."""
    
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
    async def test_v1_chat_completion_format(self, gateway_url, headers):
        """Test v1 chat endpoint returns OpenAI-compatible completion format."""
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
            assert "role" in data["choices"][0]["message"]
            
            # Additional OpenAI-compatible fields
            assert data["choices"][0]["message"]["role"] == "assistant"
            assert "finish_reason" in data["choices"][0]
            
            content = data["choices"][0]["message"]["content"]
            logger.info(f"V1 chat completion response: {content[:100]}...")
    
    @pytest.mark.asyncio
    async def test_v1_streaming_completion(self, gateway_url, headers):
        """Test v1 streaming returns OpenAI-compatible SSE format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            chunks = []
            content_received = ""
            
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
                        data_str = line[6:]
                        chunks.append(data_str)
                        
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            import json
                            chunk_data = json.loads(data_str)
                            
                            # v1 streaming should have OpenAI-compatible format
                            if "choices" in chunk_data:
                                assert len(chunk_data["choices"]) > 0
                                if "delta" in chunk_data["choices"][0]:
                                    delta = chunk_data["choices"][0]["delta"]
                                    if "content" in delta:
                                        content_received += delta["content"]
                        except json.JSONDecodeError:
                            continue
            
            assert len(chunks) > 0
            assert any("[DONE]" in chunk for chunk in chunks)
            assert content_received.strip() != ""
            logger.info(f"V1 streaming received {len(chunks)} chunks")
    
    @pytest.mark.asyncio
    async def test_v1_model_selection(self, gateway_url, headers):
        """Test v1 API with explicit model selection."""
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
                    data = response.json()
                    # v1 should return model info
                    if "model" in data:
                        # Model might be mapped to a different version
                        actual_model = data["model"]
                        logger.info(f"  Requested: {model}, Got: {actual_model}")
                    available_models.append((model, provider))
                    logger.info(f"✓ V1 Model {model} ({provider}) is available")
                else:
                    logger.info(f"✗ V1 Model {model} ({provider}) returned {response.status_code}")
            
            assert len(available_models) > 0, "No models available for v1 API"
            logger.info(f"V1 API: Found {len(available_models)} working models")
    
    @pytest.mark.asyncio
    async def test_v1_conversation_with_metadata(self, gateway_url, headers):
        """Test v1 chat with conversation management and metadata."""
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
            
            # v1 format with choices
            assert "choices" in data1
            
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
                data2 = response2.json()
                assert "choices" in data2
                logger.info(f"V1 conversation {conversation_id} tested successfully")
            else:
                logger.info("V1 conversation management not available in response")
    
    @pytest.mark.asyncio
    async def test_v1_response_metadata(self, gateway_url, headers):
        """Test v1 response includes appropriate metadata."""
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
            
            # v1 OpenAI-compatible format
            assert "choices" in data
            assert "id" in data  # Request ID
            assert "created" in data  # Timestamp
            assert "object" in data  # Should be "chat.completion"
            
            # Check for extended metadata
            if "_metadata" in data:
                metadata = data["_metadata"]
                logger.info(f"V1 response metadata: {metadata}")
                
                # Common v1 metadata fields
                if "route_type" in metadata:
                    logger.info(f"  V1 Route type: {metadata['route_type']}")
                if "total_time_ms" in metadata:
                    logger.info(f"  V1 Total time: {metadata['total_time_ms']}ms")
                if "provider" in metadata:
                    logger.info(f"  V1 Provider used: {metadata['provider']}")
    
    @pytest.mark.asyncio
    async def test_v1_providers_endpoint(self, gateway_url, headers):
        """Test v1 providers endpoint if available."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v1/providers", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                assert "providers" in data
                assert isinstance(data["providers"], list)
                
                # v1 provider format
                for provider in data["providers"]:
                    assert "name" in provider
                    assert "available" in provider
                    if "models" in provider:
                        assert isinstance(provider["models"], list)
                
                logger.info(f"V1 API: Found {len(data['providers'])} providers")
            elif response.status_code == 404:
                logger.info("V1 providers endpoint not implemented (404)")
            else:
                logger.warning(f"V1 providers endpoint returned {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_v1_models_endpoint(self, gateway_url, headers):
        """Test v1 models endpoint if available."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v1/models", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                assert "models" in data
                assert isinstance(data["models"], list)
                
                # v1 model format
                for model in data["models"]:
                    assert "id" in model or "model_id" in model
                    assert "provider" in model or "owned_by" in model
                
                logger.info(f"V1 API: Found {len(data['models'])} models")
            elif response.status_code == 404:
                logger.info("V1 models endpoint not implemented (404)")
            else:
                logger.warning(f"V1 models endpoint returned {response.status_code}")
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Moved to load tests - see tests/load/test_concurrent_requests.py")
    async def test_v1_concurrent_completions(self, gateway_url, headers):
        """Test v1 API handling concurrent completion requests.
        
        This test has been moved to the load test suite because it:
        - Tests system behavior under load, not integration correctness
        - Can trigger rate limits on external APIs
        - Has non-deterministic timing requirements
        """
        pass  # Moved to load tests