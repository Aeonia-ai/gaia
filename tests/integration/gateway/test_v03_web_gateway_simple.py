"""
Simple test to verify web gateway client works with v0.3 API.
Uses API key authentication to avoid Supabase dependency.
"""

import pytest
import httpx
import json
from typing import Dict, Any


class TestV03WebGatewaySimple:
    """Simple tests for v0.3 web gateway integration."""
    
    pytestmark = pytest.mark.xdist_group("v03_web_gateway_simple")
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL."""
        import os
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def api_key(self):
        """API key for testing."""
        import os
        api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY", "test-key-123")
        return api_key
    
    @pytest.fixture
    def headers(self, api_key):
        """Standard headers with API key."""
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_v03_direct_gateway_request_clean_format(self, gateway_url, headers):
        """Test direct v0.3 gateway request returns clean format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Hello from v0.3 web test",
                    "stream": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should get v0.3 clean format
            assert "response" in data
            assert "conversation_id" in data
            assert len(data) == 2  # Only these two fields
            
            # Should NOT have OpenAI format fields
            assert "choices" not in data
            assert "object" not in data
            assert "_metadata" not in data
    
    @pytest.mark.asyncio
    async def test_v03_conversation_persistence_automatic(self, gateway_url, headers):
        """Test v0.3 conversation persistence works automatically."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message - create conversation
            response1 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={"message": "Remember the number 42"}
            )
            
            assert response1.status_code == 200
            data1 = response1.json()
            assert "conversation_id" in data1
            conversation_id = data1["conversation_id"]
            
            # Second message - use conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "What number did I mention?",
                    "conversation_id": conversation_id
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should remember the number
            assert "42" in data2["response"]
            assert data2["conversation_id"] == conversation_id
    
    @pytest.mark.asyncio
    async def test_v03_clean_interface_hides_internals(self, gateway_url, headers):
        """Test that v0.3 hides all internal implementation details."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Tell me about your model and provider",
                    "stream": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify clean interface
            assert set(data.keys()) == {"response", "conversation_id"}
            
            # Response should not mention technical details
            response_text = data["response"].lower()
            
            # Should not expose implementation details
            forbidden_terms = [
                "claude-3",
                "anthropic",
                "openai",
                "gpt-",
                "provider",
                "model_name",
                "api_key"
            ]
            
            for term in forbidden_terms:
                assert term not in response_text, f"v0.3 should not expose term: {term}"
    
    @pytest.mark.asyncio
    async def test_v03_streaming_response(self, gateway_url, headers):
        """Test v0.3 streaming response format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Count to three",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                
                chunks = []
                full_response = ""
                conversation_id = None
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str and data_str != "[DONE]":
                            try:
                                chunk = json.loads(data_str)
                                chunks.append(chunk)
                                
                                # v0.3 streaming should have clean format
                                if "response" in chunk:
                                    full_response += chunk["response"]
                                if "conversation_id" in chunk:
                                    conversation_id = chunk["conversation_id"]
                                
                                # Should not contain internal details
                                assert "provider" not in chunk
                                assert "model" not in chunk
                                assert "choices" not in chunk
                                
                            except json.JSONDecodeError:
                                continue
                
                assert len(chunks) > 0
                assert conversation_id is not None
                assert len(full_response) > 0
    
    @pytest.mark.asyncio
    async def test_v03_error_handling_clean_format(self, gateway_url):
        """Test that v0.3 errors also follow clean format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send request without API key
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                json={"message": "This should fail"}
            )
            
            # Should return proper error status
            assert response.status_code in [401, 403]
            
            # Error response should not expose internal details
            if response.headers.get("content-type", "").startswith("application/json"):
                error_data = response.json()
                error_text = str(error_data).lower()
                
                # Should not expose internal service names
                internal_terms = ["chat-service", "auth-service", "gateway-service"]
                for term in internal_terms:
                    assert term not in error_text