"""
Test v0.3 Clean API endpoints.
Tests the simplified v0.3 interface that hides all provider details.
"""

import pytest
import httpx
import json
import os
from typing import Dict, Any, Optional


class TestV03Endpoints:
    """Test v0.3 clean API endpoints with API key to JWT exchange."""
    
    @pytest.fixture
    def gateway_url(self) -> str:
        """Gateway URL for tests."""
        return "http://gateway:8000"
    
    @pytest.fixture
    def auth_url(self) -> str:
        """Auth service URL for tests."""
        return "http://auth-service:8000"
    
    @pytest.fixture
    def api_key(self) -> str:
        """API key for testing."""
        return os.getenv("API_KEY") or os.getenv("TEST_API_KEY", "test-key-123")
    
    @pytest.fixture
    async def jwt_token(self, auth_url: str, api_key: str) -> str:
        """Exchange API key for JWT token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": api_key}
            )
            assert response.status_code == 200
            return response.json()["access_token"]
    
    @pytest.mark.asyncio
    async def test_v03_chat_non_streaming_with_api_key(self, gateway_url, api_key):
        """Test v0.3 chat endpoint with API key (non-streaming)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "What is 2+2?",
                    "stream": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # v0.3 clean format only has 'response' field
            assert "response" in data
            assert isinstance(data["response"], str)
            assert len(data["response"]) > 0
            
            # Should NOT have provider details
            assert "provider" not in data
            assert "model" not in data
            assert "_metadata" not in data
            assert "choices" not in data
            
            # Might have conversation_id for continuity
            # (optional field, not always present on first message)
    
    @pytest.mark.asyncio
    async def test_v03_chat_non_streaming_with_jwt(self, gateway_url, jwt_token):
        """Test v0.3 chat endpoint with JWT (non-streaming)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "message": "Hello, how are you?",
                    "stream": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Clean format validation
            assert "response" in data
            assert isinstance(data["response"], str)
            
            # No internal details exposed
            assert all(key not in data for key in ["provider", "model", "_metadata", "choices", "usage"])
    
    @pytest.mark.asyncio 
    async def test_v03_chat_streaming(self, gateway_url, api_key):
        """Test v0.3 streaming chat endpoint."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Count to 3",
                    "stream": True
                }
            )
            
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert content_type.startswith("text/event-stream")
            
            # Collect streaming chunks
            chunks = []
            done_received = False
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    
                    if data_str:
                        try:
                            chunk_data = json.loads(data_str)
                            chunks.append(chunk_data)
                            
                            # Verify clean format
                            assert "type" in chunk_data
                            assert chunk_data["type"] in ["content", "done", "metadata"]

                            if chunk_data["type"] == "content":
                                assert "content" in chunk_data
                                assert isinstance(chunk_data["content"], str)
                            elif chunk_data["type"] == "metadata":
                                # Metadata chunks provide conversation_id, tool status, etc.
                                # Just verify it's valid JSON - content varies by phase
                                assert isinstance(chunk_data, dict)
                            elif chunk_data["type"] == "done":
                                done_received = True
                                break
                        except json.JSONDecodeError:
                            # Skip non-JSON lines (heartbeats, etc)
                            continue
                
                # Stop after collecting some chunks
                if len(chunks) > 10:
                    break
            
            # Verify we got content and done signal
            assert len(chunks) > 0
            assert any(c["type"] == "content" for c in chunks)
            assert done_received or len(chunks) > 10  # Either done or we stopped early
    
    @pytest.mark.asyncio
    async def test_v03_chat_with_conversation_continuity(self, gateway_url, api_key):
        """Test conversation continuity with v0.3 format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "My name is TestBot. Remember it.",
                    "stream": False
                }
            )
            
            assert response1.status_code == 200
            data1 = response1.json()
            assert "response" in data1
            
            # Extract conversation_id if present
            conversation_id = data1.get("conversation_id")
            
            # Second message in same conversation
            request_data = {
                "message": "What is my name?",
                "stream": False
            }
            
            if conversation_id:
                request_data["conversation_id"] = conversation_id
            
            response2 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json=request_data
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            assert "response" in data2
            
            # The response should reference the name from the first message
            response_text = data2["response"].lower()
            assert "testbot" in response_text or "test bot" in response_text
    
    @pytest.mark.asyncio
    async def test_v03_chat_missing_message_field(self, gateway_url, api_key):
        """Test v0.3 chat endpoint with missing required field."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "stream": False
                    # Missing 'message' field
                }
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
            assert "message" in data["error"].lower()
    
    @pytest.mark.asyncio
    async def test_v03_list_conversations(self, gateway_url, api_key):
        """Test v0.3 list conversations endpoint."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First create a conversation
            chat_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "Create a test conversation",
                    "stream": False
                }
            )
            assert chat_response.status_code == 200
            
            # Now list conversations
            list_response = await client.get(
                f"{gateway_url}/api/v0.3/conversations",
                headers={"X-API-Key": api_key}
            )
            
            assert list_response.status_code == 200
            data = list_response.json()
            
            # Verify clean format
            assert "conversations" in data
            assert isinstance(data["conversations"], list)
            
            if len(data["conversations"]) > 0:
                conv = data["conversations"][0]
                assert "conversation_id" in conv
                assert "title" in conv
                assert "created_at" in conv
                
                # Should NOT have internal details
                assert "provider" not in conv
                assert "model" not in conv
                assert "metadata" not in conv
    
    @pytest.mark.asyncio
    async def test_v03_create_conversation(self, gateway_url, api_key):
        """Test v0.3 create conversation endpoint."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/conversations",
                headers={"X-API-Key": api_key},
                json={
                    "title": "Test Conversation v0.3"
                }
            )
            
            assert response.status_code == 201
            data = response.json()
            
            # Verify clean format
            assert "conversation_id" in data
            assert "title" in data
            assert data["title"] == "Test Conversation v0.3"
            
            # Should NOT have internal details
            assert all(key not in data for key in ["provider", "model", "_metadata", "user_id"])
    
    @pytest.mark.asyncio
    async def test_v03_mixed_auth_methods(self, gateway_url, api_key, jwt_token):
        """Test v0.3 endpoints work with both API key and JWT."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Start a chat with API key (let it create conversation automatically)
            chat1_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": api_key},
                json={
                    "message": "First message with API key in mixed auth test",
                    "stream": False
                }
            )
            assert chat1_response.status_code == 200
            chat1_data = chat1_response.json()
            assert "response" in chat1_data
            
            # Extract conversation_id if present
            conversation_id = chat1_data.get("conversation_id")
            
            # Skip conversation continuity test for now - just verify both auth methods work
            # This shows that v0.3 endpoints accept both API keys and JWTs
            
            # Test creating conversation with JWT
            conv_response = await client.post(
                f"{gateway_url}/api/v0.3/conversations",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"title": "JWT Created Conversation"}
            )
            
            assert conv_response.status_code == 201
            jwt_conv_id = conv_response.json()["conversation_id"]
            
            # List conversations with JWT should include the created conversation
            list_response = await client.get(
                f"{gateway_url}/api/v0.3/conversations",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            assert list_response.status_code == 200
            conversations = list_response.json()["conversations"]
            conv_ids = [c["conversation_id"] for c in conversations]
            assert jwt_conv_id in conv_ids
            
            # Both auth methods work for v0.3 endpoints
            assert chat1_response.status_code == 200
            assert conv_response.status_code == 201
            assert list_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_v03_format_conversion_completeness(self, gateway_url, api_key):
        """Test that v0.3 format conversion handles all response types correctly."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test various message types that might trigger different internal formats
            test_messages = [
                "What is the weather like?",  # Simple query
                "Write a haiku about testing",  # Creative task
                "Explain quantum computing",  # Complex explanation
                "Hi!",  # Simple greeting
            ]
            
            for message in test_messages:
                response = await client.post(
                    f"{gateway_url}/api/v0.3/chat",
                    headers={"X-API-Key": api_key},
                    json={
                        "message": message,
                        "stream": False
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Always clean format
                assert "response" in data
                assert isinstance(data["response"], str)
                assert len(data["response"]) > 0
                
                # Never expose internals
                forbidden_keys = [
                    "provider", "model", "choices", "usage", 
                    "_metadata", "route_type", "routing_time_ms",
                    "llm_time_ms", "total_time_ms", "request_id"
                ]
                for key in forbidden_keys:
                    assert key not in data, f"Found forbidden key '{key}' in response"