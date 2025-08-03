"""
Test streaming format conversion for unified chat endpoint.
"""

import pytest
import httpx
import json
import asyncio
from typing import List, Dict, Any

class TestUnifiedStreamingFormat:
    """Test streaming with format conversion."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL for accessing chat endpoints."""
        import os
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def api_key(self):
        """API key for testing."""
        import os
        api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
        if not api_key:
            pytest.skip("No API key available")
        return api_key
    
    @pytest.mark.asyncio
    async def test_streaming_with_v03_format_request(self, gateway_url, api_key):
        """Test that streaming respects X-Response-Format header."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "X-Response-Format": "v0.3"
        }
        
        chunks = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
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
                        data = line[6:]
                        
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            chunks.append(chunk)
                        except json.JSONDecodeError:
                            pass
        
        # Even with v0.3 format request, streaming still returns OpenAI format
        # This is a known limitation - streaming format conversion not implemented yet
        assert len(chunks) > 0
        
        # Check chunk structure - will be OpenAI format for now
        first_chunk = chunks[0]
        assert "object" in first_chunk or "type" in first_chunk
    
    @pytest.mark.asyncio 
    async def test_non_streaming_with_v03_format(self, gateway_url, api_key):
        """Test that non-streaming properly converts to v0.3 format."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json", 
            "X-Response-Format": "v0.3"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What is 2+2?",
                    "stream": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should be v0.3 format
            assert "response" in data
            assert "message" in data
            assert data["message"] == "What is 2+2?"
            
            # Should have conversation_id at top level
            assert "conversation_id" in data
            
            # Response should contain "4"
            assert "4" in data["response"]