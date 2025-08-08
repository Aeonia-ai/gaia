"""
Simple test to verify web gateway client works with conversation persistence.
Uses API key authentication to avoid Supabase dependency.
"""

import pytest
import httpx
import json
from typing import Dict, Any
from app.services.web.utils.gateway_client import GaiaAPIClient

class TestWebGatewaySimple:
    """Simple tests for web gateway integration."""
    
    pytestmark = pytest.mark.xdist_group("web_gateway_simple")
    
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
    async def test_direct_gateway_request_openai_format(self, gateway_url, headers):
        """Test direct gateway request returns OpenAI format with conversation_id."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "Hello from web test"}],
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
    async def test_direct_gateway_request_v03_format(self, gateway_url, headers):
        """Test direct gateway request with v0.3 format header."""
        headers_v03 = headers.copy()
        headers_v03["X-Response-Format"] = "v0.3"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers_v03,
                json={
                    "messages": [{"role": "user", "content": "Hello in v0.3 format"}],
                    "model": "claude-3-5-sonnet-20241022"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should get v0.3 format
            assert "response" in data
            assert "conversation_id" in data
            
            # Should NOT have OpenAI format fields
            assert "choices" not in data
            assert "object" not in data
    
    @pytest.mark.asyncio
    async def test_gateway_client_with_api_key(self, gateway_url, api_key):
        """Test GaiaAPIClient falls back to API key when JWT is invalid."""
        async with GaiaAPIClient(base_url=gateway_url) as client:
            # Pass "dev-token-12345" which triggers API key fallback
            response = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello via client"}],
                jwt_token="dev-token-12345"  # Triggers API key auth
            )
            
            # Should get OpenAI format by default
            assert "choices" in response
            assert "_metadata" in response
            assert "conversation_id" in response["_metadata"]
    
    @pytest.mark.asyncio
    async def test_conversation_persistence_with_api_key(self, gateway_url, headers):
        """Test conversation persistence works with API key auth."""
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