"""
Comprehensive v1 API endpoint tests for Gaia Platform.
Migrated from manual test scripts for automated testing.
Tests v1 OpenAI-compatible API endpoints specifically.
"""

import pytest
import httpx
import os
import asyncio
from typing import Dict, Any, List, Tuple
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestAuthManager

logger = setup_service_logger("test_v1_api_comprehensive")


class TestV1ComprehensiveAPIEndpoints:
    """Test all major v1 API endpoints."""
    
    pytestmark = pytest.mark.xdist_group("v1_comprehensive")
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway service URL for testing."""
        return "http://gateway:8000"
    
    @pytest.fixture
    def auth_manager(self):
        """Provide test authentication manager."""
        return TestAuthManager(test_type="unit")
    
    @pytest.fixture
    def headers(self, auth_manager):
        """Standard headers with JWT authentication."""
        auth_headers = auth_manager.get_auth_headers(
            email="test@test.local",
            role="authenticated"
        )
        return {
            **auth_headers,
            "Content-Type": "application/json"
        }
    
    @pytest.fixture
    def v1_endpoints(self, gateway_url) -> List[Tuple[str, str, Dict[str, Any], str]]:
        """List of v1 endpoints to test with method, URL, data, and description."""
        return [
            # Health checks and version info
            ("GET", f"{gateway_url}/health", None, "Gateway health"),
            ("GET", f"{gateway_url}/", None, "Root endpoint (version info)"),
            
            # v1 API tests
            ("GET", f"{gateway_url}/api/v1/chat/status", None, "v1 chat status"),
            ("POST", f"{gateway_url}/api/v1/chat", {"message": "Hello v1 test"}, "v1 chat completion"),
            ("DELETE", f"{gateway_url}/api/v1/chat/history", None, "v1 clear chat history"),
        ]
    
    async def make_request(self, method: str, url: str, headers: Dict[str, str], data: Dict[str, Any] = None) -> Tuple[bool, int, Dict[str, Any]]:
        """Make HTTP request and return success, status code, and response data."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return False, 0, {"error": f"Unsupported method: {method}"}
                
                success = response.status_code < 400
                try:
                    response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"raw": response.text}
                except:
                    response_data = {"raw": response.text}
                
                return success, response.status_code, response_data
                
        except Exception as e:
            return False, 0, {"error": str(e)}
    
    @pytest.mark.asyncio
    async def test_v1_all_endpoints_respond(self, v1_endpoints, headers):
        """Test that all v1 endpoints respond (not necessarily successfully, but respond)."""
        results = []
        
        for method, url, data, description in v1_endpoints:
            logger.info(f"Testing: {description}")
            success, status_code, response_data = await self.make_request(method, url, headers, data)
            
            # Service should respond (not connection error)
            assert status_code != 0, f"Connection failed for {description}: {response_data.get('error')}"
            
            results.append((description, success, status_code, response_data))
            logger.info(f"  {description}: {status_code} - {'✅ Success' if success else '❌ Failed'}")
        
        # Log summary
        total_tests = len(results)
        passed_tests = sum(1 for _, success, _, _ in results if success)
        logger.info(f"v1 Summary: {passed_tests}/{total_tests} endpoints successful")
        
        # At least some core endpoints should work
        assert passed_tests > 0, "No v1 endpoints responded successfully"
    
    @pytest.mark.asyncio
    async def test_v1_chat_endpoint_functional(self, gateway_url, headers):
        """Test that v1 chat endpoint works and returns OpenAI-compatible format."""
        success, status_code, response_data = await self.make_request(
            "POST", f"{gateway_url}/api/v1/chat", headers, 
            {"message": "Hello v1! How are you? Please respond briefly."}
        )
        
        assert success, f"v1 chat endpoint failed: {status_code} - {response_data}"
        
        # v1 should have OpenAI-compatible "choices" format
        assert "choices" in response_data, f"No choices field in v1 chat response: {response_data}"
        assert len(response_data["choices"]) > 0, "v1 should have at least one choice"
        assert "message" in response_data["choices"][0], "v1 choice should have message"
        assert "content" in response_data["choices"][0]["message"], "v1 message should have content"
        
        content = response_data["choices"][0]["message"]["content"]
        assert isinstance(content, str), "v1 content should be a string"
        assert len(content) > 0, "v1 content should not be empty"
        
        # v1 should have metadata with conversation_id
        assert "_metadata" in response_data, "v1 should have _metadata field"
        assert "conversation_id" in response_data["_metadata"], "v1 metadata should have conversation_id"
        
        logger.info(f"v1 chat response preview: {content[:100]}...")
    
    @pytest.mark.asyncio
    async def test_v1_openai_compatibility(self, gateway_url, headers):
        """Test that v1 API is OpenAI-compatible."""
        # Test with OpenAI-style request format
        openai_request = {
            "messages": [{"role": "user", "content": "Hello from OpenAI-style request"}],
            "model": "claude-3-5-sonnet-20241022"
        }
        
        success, status_code, response_data = await self.make_request(
            "POST", f"{gateway_url}/api/v1/chat", headers, openai_request
        )
        
        assert success, f"OpenAI-style request failed: {status_code} - {response_data}"
        
        # Should have OpenAI-compatible response structure
        assert "choices" in response_data, "Missing 'choices' field"
        assert "id" in response_data, "Missing 'id' field"
        assert response_data.get("object") == "chat.completion", "Wrong 'object' field"
        
        # Check choice structure
        choice = response_data["choices"][0]
        assert "message" in choice, "Missing 'message' in choice"
        assert "role" in choice["message"], "Missing 'role' in message"
        assert "content" in choice["message"], "Missing 'content' in message"
        assert choice["message"]["role"] == "assistant", "Wrong role in response"
        
        logger.info("v1 API is properly OpenAI-compatible")
    
    @pytest.mark.asyncio
    async def test_v1_chat_history_management(self, gateway_url, headers):
        """Test v1 chat history creation and clearing."""
        # Send a message to create history
        success, status_code, response_data = await self.make_request(
            "POST", f"{gateway_url}/api/v1/chat", headers, 
            {"message": "Remember my name is TestUser v1"}
        )
        
        assert success, f"Failed to create v1 chat history: {status_code} - {response_data}"
        logger.info("Created v1 chat history successfully")
        
        # Extract conversation_id
        conversation_id = response_data["_metadata"]["conversation_id"]
        assert conversation_id, "v1 should return conversation_id"
        
        # Test conversation persistence with explicit conversation_id
        success, status_code, response_data = await self.make_request(
            "POST", f"{gateway_url}/api/v1/chat", headers,
            {
                "message": "What's my name?",
                "conversation_id": conversation_id
            }
        )
        
        if success:
            content = response_data["choices"][0]["message"]["content"]
            assert "TestUser" in content, "v1 should remember context with conversation_id"
            logger.info("v1 conversation persistence works")
        
        # Clear history
        success, status_code, clear_data = await self.make_request(
            "DELETE", f"{gateway_url}/api/v1/chat/history", headers
        )
        
        if success:
            logger.info("Cleared v1 chat history successfully")
            assert "status" in clear_data or "cleared" in str(clear_data).lower()

    @pytest.mark.asyncio
    async def test_v1_response_format_consistency(self, gateway_url, headers):
        """Test that v1 responses are consistently OpenAI-compatible."""
        test_messages = [
            "What is 2+2?",
            "Tell me a joke", 
            "What's the weather like?"
        ]
        
        for message in test_messages:
            success, status_code, response_data = await self.make_request(
                "POST", f"{gateway_url}/api/v1/chat", headers, 
                {"message": message}
            )
            
            assert success, f"v1 request failed for '{message}': {status_code}"
            
            # Check consistent OpenAI format
            assert "choices" in response_data, f"Missing 'choices' field for message: {message}"
            assert "id" in response_data, f"Missing 'id' field for message: {message}"
            assert "_metadata" in response_data, f"Missing '_metadata' field for message: {message}"
            
            # Should NOT have v0.2 format fields
            assert "response" not in response_data or "_metadata" in response_data, "v1 should not have simple 'response' field without metadata"
            assert "provider" not in response_data, "v1 should not expose 'provider' field directly"
            assert "model" not in response_data, "v1 should not expose 'model' field directly"
    
    @pytest.mark.asyncio
    async def test_v1_streaming_support(self, gateway_url, headers):
        """Test that v1 supports streaming responses."""
        # Note: This is a placeholder for streaming test
        # Full streaming test would require SSE parsing
        streaming_request = {
            "message": "Count to three",
            "stream": True
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Just verify streaming endpoint responds
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json=streaming_request
            )
            
            # Should at least respond (even if we don't parse the stream)
            assert response.status_code == 200, "v1 streaming should respond"
            assert "text/event-stream" in response.headers.get("content-type", ""), "Should return SSE content type"
            
            logger.info("v1 streaming endpoint responds correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])