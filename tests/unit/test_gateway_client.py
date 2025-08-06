"""
Unit tests for GatewayClient functionality.

Tests the gateway client that web UI uses to communicate with backend services.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import json
import httpx
from httpx import Response, AsyncClient

from app.services.web.utils.gateway_client import GaiaAPIClient


class TestGaiaAPIClient:
    """Unit tests for GaiaAPIClient"""
    
    @pytest.fixture
    def client(self):
        """Create a GaiaAPIClient instance"""
        return GaiaAPIClient(base_url="http://gateway:8000")
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Create a mock httpx async client"""
        client = AsyncMock(spec=AsyncClient)
        return client
    
    @pytest.mark.asyncio
    async def test_chat_completion_basic(self, client, mock_httpx_client):
        """Test basic chat completion request"""
        # Mock response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Test response"
                }
            }]
        }
        mock_httpx_client.post.return_value = mock_response
        
        with patch.object(client, 'client', mock_httpx_client):
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                jwt_token="test-jwt-token"
            )
            
            # Verify request was made correctly
            mock_httpx_client.post.assert_called_once()
            call_args = mock_httpx_client.post.call_args
            assert call_args[0][0] == "/api/v1/chat"
            assert "message" in call_args[1]["json"]
            
            # Verify response
            assert result["choices"][0]["message"]["content"] == "Test response"
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_conversation_id(self, client, mock_httpx_client):
        """Test chat completion with conversation ID"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}],
            "conversation_id": "conv-123"
        }
        mock_httpx_client.post.return_value = mock_response
        
        with patch.object(client, 'client', mock_httpx_client):
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                jwt_token="test-jwt-token",
                conversation_id="conv-123"
            )
            
            # Verify conversation_id was included in request
            call_args = mock_httpx_client.post.call_args
            assert call_args[1]["json"]["conversation_id"] == "conv-123"
            
            # Verify response includes conversation_id
            assert result["conversation_id"] == "conv-123"
    
    @pytest.mark.asyncio
    async def test_chat_completion_v03_format(self, client, mock_httpx_client):
        """Test chat completion with v0.3 format"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Test response",
            "conversation_id": "conv-123"
        }
        mock_httpx_client.post.return_value = mock_response
        
        with patch.object(client, 'client', mock_httpx_client):
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                jwt_token="test-jwt-token",
                response_format="v0.3"
            )
            
            # Verify format header was set
            call_args = mock_httpx_client.post.call_args
            headers = call_args[1].get("headers", {})
            assert headers.get("X-Response-Format") == "v0.3"
            
            # Verify response format
            assert "response" in result
            assert result["response"] == "Test response"
    
    @pytest.mark.asyncio
    async def test_streaming_response(self, client, mock_httpx_client):
        """Test streaming chat completion"""
        # Create mock streaming response - decode to strings
        async def mock_iter_lines():
            yield 'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
            yield 'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
            yield 'data: [DONE]\n\n'
        
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.aiter_lines = mock_iter_lines
        
        mock_httpx_client.stream.return_value.__aenter__.return_value = mock_response
        mock_httpx_client.stream.return_value.__aexit__.return_value = None
        
        with patch.object(client, 'client', mock_httpx_client):
            chunks = []
            async for line in client.chat_completion_stream(
                messages=[{"role": "user", "content": "Hello"}],
                jwt_token="test-jwt-token"
            ):
                # The method yields raw SSE lines, need to parse
                if line.startswith('{"choices"'):
                    import json
                    chunks.append(json.loads(line))
            
            # Verify streaming was used
            mock_httpx_client.stream.assert_called_once()
            
            # Verify chunks were parsed correctly
            assert len(chunks) == 2
            assert chunks[0]["choices"][0]["delta"]["content"] == "Hello"
            assert chunks[1]["choices"][0]["delta"]["content"] == " world"
    
    @pytest.mark.asyncio
    async def test_get_conversations(self, client, mock_httpx_client):
        """Test getting conversations list"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "conversations": [
                {"id": "conv-1", "title": "Chat 1"},
                {"id": "conv-2", "title": "Chat 2"}
            ],
            "has_more": False
        }
        mock_httpx_client.get.return_value = mock_response
        
        with patch.object(client, 'client', mock_httpx_client):
            result = await client.get_conversations(jwt_token="test-jwt-token")
            
            # Verify request
            mock_httpx_client.get.assert_called_once()
            call_args = mock_httpx_client.get.call_args
            assert "/api/v1/conversations" in call_args[0][0]
            
            # Verify response - get_conversations returns list directly
            assert len(result) == 2
            assert result[0]["title"] == "Chat 1"
    
    # GaiaAPIClient doesn't have delete_conversation method
    # Removed test for non-existent method
    
    @pytest.mark.asyncio
    async def test_error_handling_404(self, client, mock_httpx_client):
        """Test handling 404 errors"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_httpx_client.get.side_effect = httpx.HTTPStatusError(
            message="Not found",
            request=Mock(),
            response=mock_response
        )
        
        with patch.object(client, 'client', mock_httpx_client):
            # Test with get_conversations which actually exists
            result = await client.get_conversations(jwt_token="test-jwt")
            # Method handles errors and returns empty list
            assert result == []
    
    @pytest.mark.asyncio
    async def test_auth_headers(self, client, mock_httpx_client):
        """Test that auth headers are included"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"conversations": []}
        mock_httpx_client.get.return_value = mock_response
        
        with patch.object(client, 'client', mock_httpx_client):
            # Use get_conversations which requires auth
            await client.get_conversations(jwt_token="test-jwt-token")
            
            # Verify auth header was included
            call_args = mock_httpx_client.get.call_args
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test-jwt-token"
    
    @pytest.mark.asyncio
    async def test_conversation_context_handling(self, client, mock_httpx_client):
        """Test proper handling of conversation context"""
        # First request creates conversation
        mock_response1 = Mock(spec=Response)
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "choices": [{"message": {"content": "Hi there!"}}],
            "conversation_id": "new-conv-123"
        }
        
        # Second request uses existing conversation
        mock_response2 = Mock(spec=Response)
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "choices": [{"message": {"content": "I remember you!"}}],
            "conversation_id": "new-conv-123"
        }
        
        mock_httpx_client.post.side_effect = [mock_response1, mock_response2]
        
        with patch.object(client, 'client', mock_httpx_client):
            # First message - no conversation ID
            result1 = await client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                jwt_token="test-jwt-token"
            )
            assert result1["conversation_id"] == "new-conv-123"
            
            # Second message - with conversation ID
            result2 = await client.chat_completion(
                messages=[{"role": "user", "content": "Do you remember me?"}],
                jwt_token="test-jwt-token",
                conversation_id="new-conv-123"
            )
            
            # Verify second request included conversation_id
            second_call = mock_httpx_client.post.call_args_list[1]
            assert second_call[1]["json"]["conversation_id"] == "new-conv-123"