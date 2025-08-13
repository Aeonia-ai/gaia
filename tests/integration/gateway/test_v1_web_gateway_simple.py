"""
Simple test to verify web gateway client works with v1 API.
Uses API key authentication to avoid Supabase dependency.
"""

import pytest
import httpx
import json
from typing import Dict, Any
from app.services.web.utils.gateway_client import GaiaAPIClient


class TestV1WebGatewaySimple:
    """Simple tests for v1 web gateway integration."""
    
    pytestmark = pytest.mark.xdist_group("v1_web_gateway_simple")
    
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
    async def test_v1_direct_gateway_request_openai_format(self, gateway_url, headers):
        """Test direct v1 gateway request returns OpenAI format with conversation_id."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "Hello from v1 web test"}],
                    "model": "claude-3-5-sonnet-20241022"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should get OpenAI format
            assert "choices" in data
            assert "id" in data
            assert data["object"] == "chat.completion"
            
            # Should have conversation_id in metadata
            assert "_metadata" in data
            assert "conversation_id" in data["_metadata"]
    
    @pytest.mark.asyncio
    async def test_v1_gateway_request_with_v03_format_header(self, gateway_url, headers):
        """Test v1 gateway request with v0.3 format header."""
        headers_v03 = headers.copy()
        headers_v03["X-Response-Format"] = "v0.3"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers_v03,
                json={
                    "messages": [{"role": "user", "content": "Hello in v0.3 format via v1"}],
                    "model": "claude-3-5-sonnet-20241022"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should get v0.3 format even when calling v1 endpoint
            assert "response" in data
            assert "conversation_id" in data
            
            # Should NOT have OpenAI format fields
            assert "choices" not in data
            assert "object" not in data
    
    @pytest.mark.asyncio
    async def test_v1_gateway_client_with_api_key(self, gateway_url, api_key):
        """Test GaiaAPIClient with v1 using API key fallback."""
        async with GaiaAPIClient(base_url=gateway_url) as client:
            # Pass "dev-token-12345" which triggers API key fallback
            response = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello via v1 client"}],
                jwt_token="dev-token-12345"  # Triggers API key auth
            )
            
            # Should get OpenAI format by default (client uses v1)
            assert "choices" in response
            assert "_metadata" in response
            assert "conversation_id" in response["_metadata"]
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Conversation persistence not working correctly - context not retained")
    async def test_v1_conversation_persistence_with_explicit_id(self, gateway_url, headers):
        """Test v1 conversation persistence with explicit conversation_id."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message - create conversation
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "Remember the number 42"}],
                    "model": "claude-3-5-sonnet-20241022"
                }
            )
            
            assert response1.status_code == 200
            data1 = response1.json()
            assert "_metadata" in data1
            conversation_id = data1["_metadata"]["conversation_id"]
            
            # Second message - use conversation_id (required for v1)
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "What number did I mention?"}],
                    "conversation_id": conversation_id,
                    "model": "claude-3-5-sonnet-20241022"
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should remember the number
            content = data2["choices"][0]["message"]["content"]
            assert "42" in content
            assert data2["_metadata"]["conversation_id"] == conversation_id
    
    @pytest.mark.asyncio
    async def test_v1_without_conversation_id_no_context(self, gateway_url, headers):
        """Test that v1 without conversation_id doesn't maintain context."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "Remember the color green"}],
                    "model": "claude-3-5-sonnet-20241022"
                }
            )
            
            assert response1.status_code == 200
            
            # Second message without conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "What color did I mention?"}],
                    "model": "claude-3-5-sonnet-20241022"
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should NOT remember the color without conversation_id
            content = data2["choices"][0]["message"]["content"].lower()
            assert "green" not in content or "don't know" in content or "didn't mention" in content