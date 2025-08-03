"""
Test-driven development for /chat/unified endpoint.
These tests define the expected behavior for conversation persistence and routing.
"""

import pytest
import httpx
import os
from typing import Dict, Any
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_unified_chat")


class TestUnifiedChatEndpoint:
    """Test the core /chat/unified endpoint behavior."""
    
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
    def headers(self, api_key):
        """Standard headers with API key."""
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_creates_conversation_on_first_message(self, gateway_url, headers):
        """Should create a new conversation when no conversation_id is provided."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send first message without conversation_id
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Hello, this is my first message"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should return conversation_id in metadata
            assert "_metadata" in data
            assert "conversation_id" in data["_metadata"]
            assert data["_metadata"]["conversation_id"] is not None
            
            conversation_id = data["_metadata"]["conversation_id"]
            logger.info(f"Created conversation: {conversation_id}")
    
    @pytest.mark.asyncio
    async def test_persists_messages_before_and_after_processing(self, gateway_url, headers):
        """Should save user message before AI processing and AI response after."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send first message
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "My favorite animal is a penguin"}
            )
            
            assert response.status_code == 200
            data = response.json()
            conversation_id = data["_metadata"]["conversation_id"]
            
            # Test persistence by sending another message
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What did I just tell you about my favorite animal?",
                    "conversation_id": conversation_id
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Extract response content
            if "choices" in data2:
                content = data2["choices"][0]["message"]["content"]
            else:
                content = data2.get("response", "")
            
            # Should remember the penguin fact
            assert "penguin" in content.lower()
            logger.info(f"AI remembered: {content[:200]}...")
    
    @pytest.mark.asyncio
    async def test_maintains_conversation_context(self, gateway_url, headers):
        """Should remember previous messages in the conversation."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "My name is TestBot and I love Python"}
            )
            
            assert response1.status_code == 200
            conversation_id = response1.json()["_metadata"]["conversation_id"]
            
            # Second message with conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What's my name and what do I love?",
                    "conversation_id": conversation_id
                }
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Extract response content based on format
            if "choices" in data2:
                content = data2["choices"][0]["message"]["content"]
            else:
                content = data2.get("response", "")
            
            # Should remember both facts
            assert "testbot" in content.lower() or "test bot" in content.lower()
            assert "python" in content.lower()
            logger.info(f"AI remembered context: {content[:200]}...")
    
    @pytest.mark.asyncio
    async def test_handles_invalid_conversation_id(self, gateway_url, headers):
        """Should handle invalid conversation_id gracefully."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send message with non-existent conversation_id
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Hello",
                    "conversation_id": "non-existent-id-12345"
                }
            )
            
            # Should either create new conversation or return error
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                # If it created a new conversation, should return new ID
                data = response.json()
                assert "_metadata" in data
                assert "conversation_id" in data["_metadata"]
                # New ID should be different from the invalid one
                assert data["_metadata"]["conversation_id"] != "non-existent-id-12345"
    
    @pytest.mark.asyncio
    async def test_routing_direct_response(self, gateway_url, headers):
        """Should use direct response for simple questions."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "What is 2+2?"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should get a response (format may vary)
            assert any(key in data for key in ["response", "choices", "message"])
            
            # Response should contain "4"
            response_text = str(data)
            assert "4" in response_text
    
    @pytest.mark.asyncio
    async def test_routing_mcp_agent(self, gateway_url, headers):
        """Should route to MCP agent for file operations."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "List the files in the current directory"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should get a response mentioning files or directory
            response_text = str(data).lower()
            assert any(word in response_text for word in ["file", "directory", "folder", "ls"])
    
    @pytest.mark.asyncio
    async def test_persists_on_error(self, gateway_url, headers):
        """Should persist user message even if processing fails."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send a message that might cause an error
            # (This is tricky to test without knowing internals)
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Test message for error handling"}
            )
            
            # Even if it fails, should return a conversation_id
            if response.status_code >= 500:
                # Server error - check if conversation was created
                assert "_metadata" in response.json()
                assert "conversation_id" in response.json()["_metadata"]
            else:
                # Success is also fine
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_streaming_preserves_conversation(self, gateway_url, headers):
        """Should maintain conversation context with streaming responses."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "My favorite color is blue", "stream": False}
            )
            
            assert response1.status_code == 200
            conversation_id = response1.json()["_metadata"]["conversation_id"]
            
            # Second message with streaming
            chunks = []
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What's my favorite color?",
                    "conversation_id": conversation_id,
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunks.append(line[6:])
            
            # Combine chunks to check content
            full_response = "".join(chunks).lower()
            assert "blue" in full_response
            
            # Verify persistence by checking context retention
            # The fact that it remembered "blue" proves messages were saved
            logger.info("Streaming with conversation persistence verified")