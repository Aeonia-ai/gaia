"""
Test format negotiation for the unified chat endpoint.
Verifies X-Response-Format header properly switches between OpenAI and v0.3 formats.
"""

import pytest
import httpx
import os
from typing import Dict, Any

class TestFormatNegotiation:
    """Test response format negotiation via X-Response-Format header."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL for accessing chat endpoints."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def api_key(self):
        """API key for testing."""
        api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
        if not api_key:
            pytest.skip("No API key available")
        return api_key
    
    @pytest.fixture
    def base_headers(self, api_key):
        """Base headers with API key."""
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_default_format_is_openai(self, gateway_url, base_headers):
        """Without X-Response-Format header, should return OpenAI format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=base_headers,
                json={"message": "Hello, what format are you using?"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # OpenAI format has 'choices' array
            assert "choices" in data
            assert isinstance(data["choices"], list)
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]
            assert "content" in data["choices"][0]["message"]
            
            # Should have metadata with conversation_id
            assert "_metadata" in data
            assert "conversation_id" in data["_metadata"]
    
    @pytest.mark.asyncio
    async def test_explicit_openai_format(self, gateway_url, base_headers):
        """With X-Response-Format: openai, should return OpenAI format."""
        headers = {**base_headers, "X-Response-Format": "openai"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Testing OpenAI format"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify OpenAI format structure
            assert "id" in data
            assert "object" in data
            assert data["object"] == "chat.completion"
            assert "created" in data
            assert "model" in data
            assert "choices" in data
            assert "usage" in data
    
    @pytest.mark.asyncio
    async def test_v03_format(self, gateway_url, base_headers):
        """With X-Response-Format: v0.3, should return v0.3 format."""
        headers = {**base_headers, "X-Response-Format": "v0.3"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Testing v0.3 format"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # v0.3 format has 'response' and 'message' at top level
            assert "response" in data
            assert "message" in data
            assert data["message"] == "Testing v0.3 format"
            
            # Should have conversation_id at top level
            assert "conversation_id" in data
            
            # Should still have metadata
            assert "_metadata" in data
            assert "conversation_id" in data["_metadata"]
            
            # Verify conversation IDs match
            assert data["conversation_id"] == data["_metadata"]["conversation_id"]
    
    @pytest.mark.asyncio
    async def test_conversation_persistence_with_v03_format(self, gateway_url, base_headers):
        """Conversation persistence should work with v0.3 format."""
        headers = {**base_headers, "X-Response-Format": "v0.3"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "My favorite food is pizza"}
            )
            
            assert response1.status_code == 200
            data1 = response1.json()
            conversation_id = data1["conversation_id"]
            
            # Second message with conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What did I just tell you about?",
                    "conversation_id": conversation_id
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should remember the context
            assert "pizza" in data2["response"].lower() or "food" in data2["response"].lower()
    
    @pytest.mark.asyncio
    async def test_invalid_format_defaults_to_openai(self, gateway_url, base_headers):
        """Invalid format should default to OpenAI format."""
        headers = {**base_headers, "X-Response-Format": "invalid-format"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Testing invalid format"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should default to OpenAI format
            assert "choices" in data
            assert "object" in data
            assert data["object"] == "chat.completion"
    
    @pytest.mark.asyncio
    async def test_format_case_insensitive(self, gateway_url, base_headers):
        """Format header should be case-insensitive."""
        headers = {**base_headers, "X-Response-Format": "V0.3"}  # Uppercase
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Testing case sensitivity"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should return v0.3 format despite uppercase
            assert "response" in data
            assert "message" in data
            assert "conversation_id" in data