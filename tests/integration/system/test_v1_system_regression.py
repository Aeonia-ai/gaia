"""
v1 API system regression test suite for Gaia Platform.
Based on successful manual test script functionality.
Tests v1 OpenAI-compatible API endpoints for regression prevention.
"""

import pytest
import httpx
import os
from typing import Dict, Any
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestAuthManager

logger = setup_service_logger("test_v1_system_regression")


class TestV1WorkingEndpoints:
    """Test v1 endpoints that are known to work from manual testing."""
    
    pytestmark = pytest.mark.xdist_group("v1_regression")
    
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
    
    @pytest.mark.asyncio
    async def test_v1_chat_completion_regression(self, gateway_url, headers):
        """Test v1 chat completion - OpenAI compatibility regression."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Hello v1! This is a regression test. Please respond briefly."}
            )
            assert response.status_code == 200
            data = response.json()
            
            # Check v1 OpenAI-compatible response structure
            assert "choices" in data, "v1 should have 'choices' field"
            assert len(data["choices"]) > 0, "v1 should have at least one choice"
            assert "message" in data["choices"][0], "v1 choice should have 'message'"
            assert "content" in data["choices"][0]["message"], "v1 message should have 'content'"
            
            # Check OpenAI-compatible metadata
            assert "id" in data, "v1 should have 'id' field"
            assert "_metadata" in data, "v1 should have '_metadata' field"
            assert "conversation_id" in data["_metadata"], "v1 metadata should have conversation_id"
            
            content = data["choices"][0]["message"]["content"]
            assert isinstance(content, str), "v1 content should be string"
            assert len(content) > 0, "v1 content should not be empty"
            assert content != "Hello v1! This is a regression test. Please respond briefly."
            logger.info(f"v1 chat response length: {len(content)} chars")
    
    @pytest.mark.asyncio
    async def test_v1_openai_format_regression(self, gateway_url, headers):
        """Test v1 OpenAI-compatible format regression."""
        # Test with OpenAI-style request format
        openai_request = {
            "messages": [{"role": "user", "content": "OpenAI format regression test"}],
            "model": "claude-3-5-sonnet-20241022"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json=openai_request
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check OpenAI compatibility
            assert "choices" in data, "Missing 'choices' field"
            assert "id" in data, "Missing 'id' field"
            assert data.get("object") == "chat.completion", "Wrong 'object' field"
            
            # Check choice structure
            choice = data["choices"][0]
            assert "message" in choice, "Missing 'message' in choice"
            assert "role" in choice["message"], "Missing 'role' in message"
            assert "content" in choice["message"], "Missing 'content' in message"
            assert choice["message"]["role"] == "assistant", "Wrong role in response"
            
            logger.info("v1 OpenAI compatibility regression passed")
    
    @pytest.mark.asyncio
    async def test_v1_conversation_persistence_regression(self, gateway_url, headers):
        """Test v1 conversation persistence with explicit conversation_id."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message - create conversation
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "My lucky number is 777. Remember this for v1 testing."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            
            # Extract conversation_id
            conversation_id = data1["_metadata"]["conversation_id"]
            assert conversation_id, "v1 should return conversation_id"
            
            # Second message with explicit conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "What is my lucky number?",
                    "conversation_id": conversation_id
                }
            )
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should remember the number
            content = data2["choices"][0]["message"]["content"]
            assert "777" in content, f"v1 should remember context: {content}"
            assert data2["_metadata"]["conversation_id"] == conversation_id
            
            logger.info(f"v1 conversation persistence regression passed")
    
    @pytest.mark.asyncio
    async def test_v1_without_conversation_id_no_context_regression(self, gateway_url, headers):
        """Test that v1 without conversation_id doesn't maintain context."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "My code word is 'elephant'. Remember this."}
            )
            assert response1.status_code == 200
            
            # Second message without conversation_id
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "What is my code word?"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should NOT remember without conversation_id
            content = data2["choices"][0]["message"]["content"].lower()
            assert "elephant" not in content or "don't know" in content or "didn't mention" in content
            
            logger.info("v1 context isolation regression passed")
    
    @pytest.mark.asyncio
    async def test_v1_response_format_consistency_regression(self, gateway_url, headers):
        """Test that v1 response format remains consistently OpenAI-compatible."""
        test_cases = [
            "What is 3+3?",
            "Tell me a short joke",
            "Explain gravity briefly"
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, message in enumerate(test_cases):
                response = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={"message": message}
                )
                
                assert response.status_code == 200, f"v1 request {i+1} failed"
                data = response.json()
                
                # Consistent OpenAI format requirements
                assert "choices" in data, f"Request {i+1}: Missing 'choices' field"
                assert "id" in data, f"Request {i+1}: Missing 'id' field"
                assert "_metadata" in data, f"Request {i+1}: Missing '_metadata' field"
                
                # Check choice structure
                choice = data["choices"][0]
                assert "message" in choice, f"Request {i+1}: Missing 'message' in choice"
                assert "content" in choice["message"], f"Request {i+1}: Missing 'content'"
                
                # Should NOT have v0.2 format fields
                assert "response" not in data or "_metadata" in data, f"Request {i+1}: v1 format inconsistent"
                assert "provider" not in data, f"Request {i+1}: Should not expose 'provider' directly"
                
                logger.info(f"v1 consistency test {i+1}: ✅ OpenAI format consistent")
    
    @pytest.mark.skip(reason="Chat status endpoint deprecated - system uses conversation-based storage")
    @pytest.mark.asyncio
    async def test_v1_chat_status_regression(self, gateway_url, headers):
        """Test v1 chat status endpoint if it exists."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v1/chat/status", headers=headers)
            if response.status_code == 200:
                data = response.json()
                assert "message_count" in data or "status" in data
                logger.info(f"v1 chat status: {data}")
    
    @pytest.mark.skip(reason="Clear history endpoint deprecated - was scaffolding for persona development")
    @pytest.mark.asyncio
    async def test_v1_clear_chat_history_regression(self, gateway_url, headers):
        """Test v1 clear chat history endpoint if it exists."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{gateway_url}/api/v1/chat/history", headers=headers)
            if response.status_code == 200:
                data = response.json()
                assert data.get("status") == "success" or "cleared" in str(data).lower()
                logger.info("v1 clear history works")


class TestV1AuthenticationRegression:
    """Test v1 authentication methods for regression."""
    
    pytestmark = pytest.mark.xdist_group("v1_auth_regression")
    
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"
    
    @pytest.mark.asyncio
    async def test_v1_no_auth_rejected_regression(self, gateway_url):
        """Test that v1 requests without auth are still rejected."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                json={"message": "This should fail"}
            )
            assert response.status_code in [401, 403], "v1 should require authentication"
    
    @pytest.mark.asyncio
    async def test_v1_api_key_fallback_regression(self, gateway_url):
        """Test that v1 API key fallback ('dev-token-12345') still works."""
        headers = {
            "Authorization": "Bearer dev-token-12345",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "API key fallback test for v1"}
            )
            # Should work with dev token fallback
            assert response.status_code not in [401, 403], f"v1 API key fallback failed: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                assert "choices" in data, "v1 should return OpenAI format with API key fallback"
                logger.info("v1 API key fallback authentication works")
    
    @pytest.mark.asyncio
    async def test_v1_jwt_auth_regression(self, gateway_url):
        """Test that v1 JWT auth still works."""
        auth_manager = TestAuthManager(test_type="unit")
        auth_headers = auth_manager.get_auth_headers(
            email="test@test.local",
            role="authenticated"
        )
        headers = {
            **auth_headers,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "JWT auth test for v1"}
            )
            assert response.status_code not in [401, 403], f"v1 JWT auth failed: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                assert "choices" in data, "v1 should return OpenAI format with JWT"
                logger.info("v1 JWT authentication works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])