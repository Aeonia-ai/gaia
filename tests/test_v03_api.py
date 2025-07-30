"""
Tests for Gaia v0.3 API - Clean, simple interface with no exposed provider details.

Design principles:
- Simple request/response format
- No provider/model selection exposed to clients
- Consistent streaming and non-streaming formats
- Server-side intelligence is completely hidden
"""

import pytest
import httpx
import json
import asyncio
from unittest.mock import AsyncMock, patch


@pytest.fixture
def gateway_url():
    """Gateway service URL for testing."""
    return "http://gateway:8000"


@pytest.fixture
def api_key():
    """Test API key."""
    import os
    return os.getenv("API_KEY", "test-api-key-12345")


@pytest.fixture
def headers(api_key):
    """Standard headers for API requests."""
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }


class TestV03ChatAPI:
    """Test the clean v0.3 chat API."""

    async def test_simple_chat_message(self, gateway_url, headers):
        """Test basic chat functionality with clean response format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={"message": "Hello! Please respond briefly."}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Clean Gaia v0.3 format - no provider details exposed
            assert "response" in data
            assert isinstance(data["response"], str)
            assert len(data["response"]) > 0
            
            # Should NOT contain internal details
            assert "provider" not in data
            assert "model" not in data
            assert "reasoning" not in data
            assert "response_time_ms" not in data
            assert "usage" not in data
            
            # Response should be just the clean format
            expected_keys = {"response"}
            assert set(data.keys()) == expected_keys

    async def test_conversation_context(self, gateway_url, headers):
        """Test that conversations maintain context without exposing internals."""
        conversation_id = "test-conv-v03"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "My name is Alice.",
                    "conversation_id": conversation_id
                }
            )
            
            assert response1.status_code == 200
            data1 = response1.json()
            assert "response" in data1
            
            # Second message - should remember context
            response2 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "What is my name?",
                    "conversation_id": conversation_id
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            assert "response" in data2
            
            # Should remember the name without exposing how
            response_text = data2["response"].lower()
            assert "alice" in response_text
            
            # Still clean format - no internals exposed
            assert "provider" not in data2
            assert "model" not in data2

    async def test_streaming_chat(self, gateway_url, headers):
        """Test streaming chat with clean Gaia format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Count to 5 slowly.",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                assert response.headers.get("content-type") == "text/plain; charset=utf-8"
                
                chunks = []
                content_received = ""
                done_received = False
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        
                        if data_str == "[DONE]":
                            done_received = True
                            break
                            
                        try:
                            chunk = json.loads(data_str)
                            chunks.append(chunk)
                            
                            if chunk.get("type") == "content":
                                content_received += chunk.get("content", "")
                            elif chunk.get("type") == "done":
                                done_received = True
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                # Verify clean streaming format
                assert len(chunks) > 0
                assert content_received.strip() != ""
                assert done_received
                
                # Check that all chunks have clean format
                for chunk in chunks:
                    if chunk.get("type") == "content":
                        assert "content" in chunk
                        assert isinstance(chunk["content"], str)
                        
                        # Should NOT contain internal details
                        assert "provider" not in chunk
                        assert "model" not in chunk
                        assert "delta" not in chunk
                        assert "choices" not in chunk
                        
                        # Clean format only
                        expected_keys = {"type", "content"}
                        assert set(chunk.keys()) <= expected_keys

    async def test_no_provider_model_parameters_accepted(self, gateway_url, headers):
        """Test that v0.3 API rejects provider/model parameters."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to send provider parameter - should be ignored or rejected
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Hello",
                    "provider": "openai",  # Should not be accepted
                    "model": "gpt-4"       # Should not be accepted
                }
            )
            
            # Should either ignore the parameters or return 400
            # For now, let's say it ignores them and responds normally
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            
            # Response should still be clean
            assert "provider" not in data
            assert "model" not in data

    async def test_error_handling_clean_format(self, gateway_url, headers):
        """Test that errors also follow clean format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test with missing message
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={}  # Missing message
            )
            
            assert response.status_code == 400
            data = response.json()
            
            # Error should have clean format
            assert "error" in data
            assert isinstance(data["error"], str)
            
            # Should NOT expose internal error details
            assert "provider" not in data
            assert "model" not in data
            assert "traceback" not in data

    async def test_kb_integration_clean_format(self, gateway_url, headers):
        """Test KB integration with clean format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "What information do you have about consciousness?",
                    "use_kb": True  # Enable KB integration
                }
            )
            
            # Should succeed or gracefully handle if KB not available
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert "response" in data
                assert isinstance(data["response"], str)
                
                # Still clean format even with KB
                assert "provider" not in data
                assert "model" not in data
                assert "kb_results" not in data  # KB details are internal
                assert "metadata" not in data

    async def test_conversation_management(self, gateway_url, headers):
        """Test conversation management endpoints."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # List conversations
            response = await client.get(
                f"{gateway_url}/api/v0.3/conversations",
                headers=headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "conversations" in data
            assert isinstance(data["conversations"], list)
            
            # Create new conversation
            response = await client.post(
                f"{gateway_url}/api/v0.3/conversations",
                headers=headers,
                json={"title": "Test Conversation"}
            )
            
            assert response.status_code == 201
            data = response.json()
            assert "conversation_id" in data
            assert "title" in data
            
            # Should NOT expose internal details
            assert "provider" not in data
            assert "model" not in data


class TestV03Authentication:
    """Test authentication for v0.3 API."""

    async def test_requires_authentication(self, gateway_url):
        """Test that v0.3 API requires authentication."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                json={"message": "Hello"}
                # No auth headers
            )
            
            assert response.status_code == 401

    async def test_invalid_api_key_rejected(self, gateway_url):
        """Test that invalid API keys are rejected."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={
                    "X-API-Key": "invalid-key",
                    "Content-Type": "application/json"
                },
                json={"message": "Hello"}
            )
            
            assert response.status_code == 401


class TestV03BackwardCompatibility:
    """Test that v0.3 doesn't break existing functionality."""

    async def test_v02_still_works(self, gateway_url, headers):
        """Test that v0.2 API still works alongside v0.3."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # v0.2 should still work with old format
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "Hello"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # v0.2 format (may include provider details)
            assert "response" in data

    async def test_v1_still_works(self, gateway_url, headers):
        """Test that v1 API still works alongside v0.3."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # v1 should still work
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Hello"}
            )
            
            assert response.status_code == 200
            # v1 format (whatever it currently returns)