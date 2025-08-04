"""
Simple test to verify web UI can migrate to unified endpoint.
Uses direct HTTP calls to avoid import issues.
"""

import pytest
import httpx
import os

class TestWebUIMigrationSimple:
    """Test web UI can use unified endpoint without manual conversation management."""
    
    @pytest.fixture
    def gateway_url(self):
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def api_key(self):
        return os.getenv("API_KEY", "test-key-123")
    
    @pytest.mark.asyncio
    async def test_unified_endpoint_creates_conversations(self, gateway_url, api_key):
        """Test that unified endpoint creates and manages conversations automatically."""
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message - no conversation_id
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "My favorite animal is a cat",
                    "model": "claude-3-5-sonnet-20241022"
                }
            )
            
            assert response1.status_code == 200
            data1 = response1.json()
            
            # Should have conversation_id in metadata
            assert "_metadata" in data1
            assert "conversation_id" in data1["_metadata"]
            conversation_id = data1["_metadata"]["conversation_id"]
            
            # Second message - with conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What animal did I mention?",
                    "conversation_id": conversation_id,
                    "model": "claude-3-5-sonnet-20241022"
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should remember context
            content = data2["choices"][0]["message"]["content"].lower()
            assert "cat" in content
            
            # Should maintain conversation
            assert data2["_metadata"]["conversation_id"] == conversation_id
    
    @pytest.mark.asyncio
    async def test_v03_format_with_conversation_management(self, gateway_url, api_key):
        """Test v0.3 format includes conversation_id at top level."""
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "X-Response-Format": "v0.3"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Remember the number 42"}
            )
            
            assert response1.status_code == 200
            data1 = response1.json()
            
            # v0.3 format has conversation_id at top level
            assert "response" in data1
            assert "conversation_id" in data1
            conversation_id = data1["conversation_id"]
            
            # Second message
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What number did I ask you to remember?",
                    "conversation_id": conversation_id
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should remember
            assert "42" in data2["response"]
            assert data2["conversation_id"] == conversation_id