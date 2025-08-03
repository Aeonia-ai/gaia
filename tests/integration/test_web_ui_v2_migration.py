"""
Test web UI v2 migration - verifies the new chat endpoints work with unified conversation persistence.
"""

import pytest
import httpx
import json
from typing import Dict, Any

class TestWebUIV2Migration:
    """Test the v2 chat endpoints that use unified conversation persistence."""
    
    @pytest.fixture
    def web_url(self):
        """Web service URL."""
        import os
        # Use localhost:8000 for web service when running in Docker
        return os.getenv("WEB_URL", "http://web:8000")
    
    @pytest.fixture
    async def authenticated_session(self, web_url):
        """Create an authenticated session with the web service."""
        import os
        
        # Get test credentials
        email = os.getenv("TEST_USER_EMAIL", "test@example.com")
        password = os.getenv("TEST_USER_PASSWORD", "TestPassword123!")
        
        async with httpx.AsyncClient(base_url=web_url, follow_redirects=True) as client:
            # Login to get session
            login_response = await client.post(
                "/login",
                data={
                    "email": email,
                    "password": password
                }
            )
            
            # Check if login was successful
            if login_response.status_code != 200:
                pytest.skip(f"Login failed: {login_response.status_code}")
            
            # Return the client with session cookies
            yield client
    
    @pytest.mark.asyncio
    async def test_v2_send_creates_conversation(self, authenticated_session):
        """Test that v2 send endpoint creates a conversation on first message."""
        client = authenticated_session
        
        # Send a message without conversation_id
        response = await client.post(
            "/api/chat/v2/send",
            data={
                "message": "Hello from v2 test"
            }
        )
        
        assert response.status_code == 200
        
        # Response should be HTML with the message
        html = response.text
        assert "Hello from v2 test" in html
        assert "Gaia is thinking..." in html
        
        # Should have SSE setup script
        assert "/api/chat/v2/stream" in html
    
    @pytest.mark.asyncio
    async def test_v2_stream_returns_conversation_id(self, authenticated_session):
        """Test that v2 stream endpoint returns conversation_id for new conversations."""
        client = authenticated_session
        
        # Stream a response without conversation_id
        conversation_id = None
        response_chunks = []
        
        async with client.stream(
            "GET",
            "/api/chat/v2/stream",
            params={
                "message": "What is 2+2?"
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
                        response_chunks.append(chunk)
                        
                        # Check for conversation_id
                        if "conversation_id" in chunk:
                            conversation_id = chunk["conversation_id"]
                    except json.JSONDecodeError:
                        pass
        
        # Should have received a conversation_id
        assert conversation_id is not None
        
        # Should have received content chunks
        content_chunks = [c for c in response_chunks if c.get("type") == "content"]
        assert len(content_chunks) > 0
        
        # Response should mention "4"
        full_response = "".join(c.get("content", "") for c in content_chunks)
        assert "4" in full_response
    
    @pytest.mark.asyncio
    async def test_v2_maintains_conversation_context(self, authenticated_session):
        """Test that v2 endpoints maintain conversation context."""
        client = authenticated_session
        
        # First message - establish context
        conversation_id = None
        
        async with client.stream(
            "GET",
            "/api/chat/v2/stream",
            params={
                "message": "My favorite programming language is Python"
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if "conversation_id" in chunk:
                            conversation_id = chunk["conversation_id"]
                    except:
                        pass
        
        assert conversation_id is not None
        
        # Second message - test context
        response_content = ""
        
        async with client.stream(
            "GET",
            "/api/chat/v2/stream",
            params={
                "message": "What did I just tell you about?",
                "conversation_id": conversation_id
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if chunk.get("type") == "content":
                            response_content += chunk.get("content", "")
                    except:
                        pass
        
        # Should remember Python
        assert "python" in response_content.lower() or "programming" in response_content.lower()
    
    @pytest.mark.asyncio
    async def test_v2_handles_existing_conversation(self, authenticated_session):
        """Test that v2 works with existing conversation IDs."""
        client = authenticated_session
        
        # Create a conversation first
        conversation_id = None
        
        # Get initial conversation_id
        async with client.stream(
            "GET",
            "/api/chat/v2/stream",
            params={
                "message": "Remember the number 42"
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if "conversation_id" in chunk:
                            conversation_id = chunk["conversation_id"]
                    except:
                        pass
        
        # Send another message via the send endpoint with conversation_id
        response = await client.post(
            "/api/chat/v2/send",
            data={
                "message": "What number did I ask you to remember?",
                "conversation_id": conversation_id
            }
        )
        
        assert response.status_code == 200
        html = response.text
        
        # Should include the conversation_id in the SSE URL
        assert f"conversation_id={conversation_id}" in html