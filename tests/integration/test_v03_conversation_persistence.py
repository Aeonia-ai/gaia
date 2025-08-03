"""
Test v0.3 endpoint conversation persistence.
"""

import pytest
import httpx
import json
from typing import Dict, Any

class TestV03ConversationPersistence:
    """Test the v0.3 chat endpoint with conversation persistence."""
    
    # Run all tests in this class in the same worker to avoid parallel LLM calls
    pytestmark = pytest.mark.xdist_group("v03_persistence")
    
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
    
    @pytest.fixture
    def headers(self, api_key):
        """Standard headers with API key."""
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_v03_creates_conversation(self, gateway_url, headers):
        """v0.3 endpoint should create conversation and return ID."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={"message": "Hello from v0.3 test"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # v0.3 format should have response and conversation_id
            assert "response" in data
            assert "conversation_id" in data
            assert data["conversation_id"] is not None
            
            # Response should acknowledge the message
            assert len(data["response"]) > 0
    
    @pytest.mark.asyncio
    async def test_v03_maintains_conversation_context(self, gateway_url, headers):
        """v0.3 endpoint should maintain conversation context."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={"message": "My favorite color is purple"}
            )
            
            assert response1.status_code == 200
            data1 = response1.json()
            conversation_id = data1["conversation_id"]
            
            # Second message with conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "What color did I mention?",
                    "conversation_id": conversation_id
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should remember purple
            assert "purple" in data2["response"].lower()
            
            # Should return same conversation_id
            assert data2["conversation_id"] == conversation_id
    
    @pytest.mark.asyncio
    async def test_v03_streaming_format(self, gateway_url, headers):
        """v0.3 streaming should use clean format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            chunks = []
            
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
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
                        
                        try:
                            chunk = json.loads(data)
                            chunks.append(chunk)
                            
                            # Check for done message
                            if chunk.get("type") == "done":
                                break
                        except json.JSONDecodeError:
                            pass
            
            # Should have content chunks
            content_chunks = [c for c in chunks if c.get("type") == "content"]
            assert len(content_chunks) > 0
            
            # Should have done chunk
            done_chunks = [c for c in chunks if c.get("type") == "done"]
            assert len(done_chunks) == 1
    
    @pytest.mark.asyncio
    async def test_direct_v03_endpoint(self, gateway_url, headers):
        """Test v0.3 endpoint returns clean format with math."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={"message": "What is 5+5?"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should get v0.3 format response
            assert "response" in data
            assert "10" in data["response"]
            
            # Should have conversation_id
            assert "conversation_id" in data