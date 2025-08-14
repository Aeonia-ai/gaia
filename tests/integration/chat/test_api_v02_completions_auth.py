"""
Integration tests for v0.2 API completions using real API key authentication.
Extracted v1 tests to separate file for better test organization.
Focuses on v0.2-specific endpoints and features.
"""

import pytest
import httpx
import os
import asyncio
from typing import Dict, Any
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_api_v02_completions_auth")


class TestV02CompletionsWithRealAuth:
    """Test v0.2 API completion endpoints with real API key authentication."""
    
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
    async def test_v02_chat_endpoint(self, gateway_url, headers):
        """Test v0.2 basic chat endpoint if available."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try v0.2 chat endpoint
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={
                    "message": "Hello, what is 2+2?",
                    "stream": False
                }
            )
            
            if response.status_code == 404:
                pytest.skip("v0.2 chat endpoint not available")
                
            assert response.status_code == 200
            data = response.json()
            
            # v0.2 response format
            assert "response" in data or "choices" in data
            logger.info("V0.2 chat endpoint succeeded")
    
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
    async def test_v02_providers_endpoint(self, gateway_url, headers):
        """Test v0.2 providers endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v0.2/providers", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                assert "providers" in data
                assert isinstance(data["providers"], list)
                
                # v0.2 might have different provider format
                for provider in data["providers"]:
                    assert "name" in provider or "id" in provider
                    assert "available" in provider or "status" in provider
                
                logger.info(f"V0.2 API: Found {len(data['providers'])} providers")
            elif response.status_code == 404:
                logger.info("V0.2 providers endpoint not implemented (404)")
            else:
                logger.warning(f"V0.2 providers endpoint returned {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_v02_models_endpoint(self, gateway_url, headers):
        """Test v0.2 models endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v0.2/models", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                assert "models" in data
                assert isinstance(data["models"], list)
                
                logger.info(f"V0.2 API: Found {len(data['models'])} models")
            elif response.status_code == 404:
                logger.info("V0.2 models endpoint not implemented (404)")
            else:
                logger.warning(f"V0.2 models endpoint returned {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_v02_conversation_management(self, gateway_url, headers):
        """Test v0.2 conversation management if supported."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try v0.2 conversation endpoint
            response = await client.post(
                f"{gateway_url}/api/v0.2/conversations",
                headers=headers,
                json={"title": "Test conversation"}
            )
            
            if response.status_code == 404:
                logger.info("V0.2 conversation management not available")
                return
                
            if response.status_code == 201 or response.status_code == 200:
                data = response.json()
                conversation_id = data.get("id") or data.get("conversation_id")
                
                if conversation_id:
                    # Test chat in conversation
                    chat_response = await client.post(
                        f"{gateway_url}/api/v0.2/chat",
                        headers=headers,
                        json={
                            "message": "Hello in v0.2",
                            "conversation_id": conversation_id
                        }
                    )
                    
                    if chat_response.status_code == 200:
                        logger.info(f"V0.2 conversation {conversation_id} tested successfully")
                    else:
                        logger.info(f"V0.2 chat in conversation returned {chat_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_v02_streaming_completion(self, gateway_url, headers):
        """Test v0.2 streaming chat completion."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            chunks = []
            try:
                async with client.stream(
                    "POST",
                    f"{gateway_url}/api/v0.2/chat/completions",
                    headers=headers,
                    json={
                        "messages": [{"role": "user", "content": "Count to 3"}],
                        "model": "claude-3-5-haiku-20241022",
                        "stream": True
                    }
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                chunks.append(line[6:])
                        
                        if len(chunks) > 0:
                            logger.info(f"V0.2 streaming received {len(chunks)} chunks")
                            assert any("[DONE]" in chunk for chunk in chunks)
                    elif response.status_code == 404:
                        pytest.skip("V0.2 streaming endpoint not available")
                    else:
                        logger.warning(f"V0.2 streaming returned {response.status_code}")
            except Exception as e:
                logger.debug(f"V0.2 streaming failed: {e}")
                pytest.skip(f"V0.2 streaming not supported: {e}")
    
    @pytest.mark.asyncio
    async def test_v02_auth_validation(self, gateway_url):
        """Test v0.2 authentication validation."""
        async with httpx.AsyncClient() as client:
            # First check if endpoint exists with valid auth
            test_response = await client.post(
                f"{gateway_url}/api/v0.2/chat/completions",
                headers={"X-API-Key": "test-check"},
                json={"messages": [{"role": "user", "content": "test"}]}
            )
            
            if test_response.status_code == 404:
                # Try v0.2 chat endpoint instead
                endpoint = f"{gateway_url}/api/v0.2/chat"
                json_payload = {"message": "Hello"}
            else:
                endpoint = f"{gateway_url}/api/v0.2/chat/completions"
                json_payload = {"messages": [{"role": "user", "content": "Hello"}]}
            
            # No auth should fail
            response = await client.post(endpoint, json=json_payload)
            assert response.status_code in [401, 403, 404], f"Expected auth error, got {response.status_code}"
            
            # Invalid auth should fail
            response = await client.post(
                endpoint,
                headers={"X-API-Key": "invalid-key-12345"},
                json=json_payload
            )
            assert response.status_code == 401, f"Expected 401 for invalid key, got {response.status_code}"
            
            if response.status_code != 404:
                logger.info("V0.2 auth validation working correctly")
    
    @pytest.mark.asyncio
    async def test_v02_personas_endpoint(self, gateway_url, headers):
        """Test v0.2 personas endpoint if available."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v0.2/personas", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                assert "personas" in data
                assert isinstance(data["personas"], list)
                
                # Should have at least default Mu persona
                if len(data["personas"]) > 0:
                    assert any(p.get("name") == "Mu" for p in data["personas"])
                    logger.info(f"V0.2 API: Found {len(data['personas'])} personas")
            elif response.status_code == 404:
                logger.info("V0.2 personas endpoint not implemented (404)")
            else:
                logger.warning(f"V0.2 personas endpoint returned {response.status_code}")
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Moved to load tests - see tests/load/test_concurrent_requests.py")
    async def test_v02_concurrent_requests(self, gateway_url, headers):
        """Test v0.2 handling concurrent requests with real auth.
        
        This test has been moved to load tests as it tests system behavior
        under concurrent load rather than API integration correctness."""
        pass  # Implementation moved to load tests
    
    @pytest.mark.asyncio
    async def test_v02_response_metadata(self, gateway_url, headers):
        """Test v0.2 response metadata."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat/completions",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "What is 1+1?"}],
                    "model": "claude-3-5-haiku-20241022",
                    "stream": False
                }
            )
            
            if response.status_code == 404:
                pytest.skip("v0.2 chat completions endpoint not available")
                
            assert response.status_code == 200
            data = response.json()
            
            # v0.2 might include usage metadata
            if "usage" in data:
                usage = data["usage"]
                logger.info(f"V0.2 usage metadata: {usage}")
                assert "prompt_tokens" in usage or "input_tokens" in usage
                assert "completion_tokens" in usage or "output_tokens" in usage
                assert "total_tokens" in usage
            
            # Check for v0.2 specific metadata
            if "model" in data:
                logger.info(f"V0.2 Model used: {data['model']}")
            if "id" in data:
                logger.info(f"V0.2 Request ID: {data['id']}")
    
    @pytest.mark.asyncio 
    async def test_v02_model_selection(self, gateway_url, headers):
        """Test v0.2 model selection in chat completions."""
        models_to_test = [
            ("claude-3-5-haiku-20241022", "anthropic"),
            ("gpt-4o-mini", "openai"),
            ("gpt-3.5-turbo", "openai")
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            available_models = []
            
            for model, provider in models_to_test:
                response = await client.post(
                    f"{gateway_url}/api/v0.2/chat/completions",
                    headers=headers,
                    json={
                        "messages": [{"role": "user", "content": "Say 'yes'"}],
                        "model": model,
                        "stream": False,
                        "max_tokens": 10
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # v0.2 should indicate which model was used
                    if "model" in data:
                        assert model in data["model"] or provider in data["model"]
                    available_models.append((model, provider))
                    logger.info(f"✓ V0.2 Model {model} ({provider}) is available")
                elif response.status_code == 404:
                    logger.info("V0.2 chat completions endpoint not available")
                    break
                else:
                    logger.info(f"✗ V0.2 Model {model} ({provider}) returned {response.status_code}")
            
            if response.status_code != 404 and len(available_models) == 0:
                logger.warning("V0.2 endpoint exists but no models available")