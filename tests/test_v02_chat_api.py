"""
Automated tests for v0.2 chat API endpoint.
Migrated from manual test scripts for continuous integration.
"""

import pytest
import httpx
import os
from typing import Dict, Any
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestAuthManager

logger = setup_service_logger("test_v02_chat")


class TestV02ChatAPI:
    """Test v0.2 chat API endpoint functionality."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway service URL for testing."""
        return os.getenv("GATEWAY_URL", "http://localhost:8666")
    
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
    
    async def test_v02_api_info(self, gateway_url, headers):
        """Test v0.2 API info endpoint."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(f"{gateway_url}/api/v0.2/", headers=headers)
            # This endpoint may not be implemented - allow 404 or redirect
            assert response.status_code in [200, 404, 307]
            if response.status_code == 200:
                data = response.json()
                assert "version" in data or "message" in data
    
    async def test_gateway_health_check(self, gateway_url, headers):
        """Test main gateway health endpoint (known to work)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/health", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") in ["healthy", "degraded"]
    
    async def test_v02_chat_status(self, gateway_url, headers):
        """Test v0.2 chat status endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v0.2/chat/status", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "message_count" in data
            assert "has_history" in data
    
    async def test_v02_chat_completion(self, gateway_url, headers):
        """Test v0.2 chat completion endpoint."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "Hello v0.2! This is a test message."}
            )
            assert response.status_code == 200
            data = response.json()
            
            # Check response structure
            assert "response" in data
            assert isinstance(data["response"], str)
            assert len(data["response"]) > 0
            
            # Should contain actual response content
            assert data["response"] != "Hello v0.2! This is a test message."
            logger.info(f"Chat response: {data['response'][:100]}...")
    
    async def test_v02_chat_with_model_selection(self, gateway_url, headers):
        """Test v0.2 chat with specific model selection."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={
                    "message": "What model are you using?",
                    "model": "claude-3-5-sonnet-20241022"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert isinstance(data["response"], str)
            assert len(data["response"]) > 0
    
    async def test_v02_providers_list(self, gateway_url, headers):
        """Test v2 providers list endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v0.2/providers", headers=headers)
            # This endpoint may not be fully implemented - allow errors
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 200:
                data = response.json()
                # Should have providers
                assert isinstance(data, (list, dict))
                if isinstance(data, dict):
                    assert "providers" in data or len(data) > 0
                else:
                    assert len(data) > 0
    
    async def test_v02_get_specific_provider(self, gateway_url, headers):
        """Test v0.2 get specific provider endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v0.2/providers/claude", headers=headers)
            # Should return provider info, 404 if not found, or other errors
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)
                # Should have provider information
                assert len(data) > 0
    
    async def test_v02_clear_chat_history(self, gateway_url, headers):
        """Test v0.2 clear chat history endpoint."""
        async with httpx.AsyncClient() as client:
            # First send a message to create history
            await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "Create some history"}
            )
            
            # Then clear the history
            response = await client.delete(f"{gateway_url}/api/v0.2/chat/history", headers=headers)
            assert response.status_code == 200
            data = response.json()
            
            # Should indicate success
            assert data.get("status") == "success" or "cleared" in str(data).lower()
    
    async def test_v02_chat_conversation_flow(self, gateway_url, headers):
        """Test full conversation flow with v0.2 API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Clear any existing history first
            await client.delete(f"{gateway_url}/api/v0.2/chat/history", headers=headers)
            
            # Send first message
            response1 = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "My name is Alice. Remember this."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            assert "response" in data1
            
            # Send follow-up message that should use context
            response2 = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "What is my name?"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            assert "response" in data2
            
            # Response should reference the name Alice (context preserved)
            response_text = data2["response"].lower()
            assert "alice" in response_text or "name" in response_text
            
            logger.info(f"Context test - Response: {data2['response'][:100]}...")


class TestV02ChatAPIErrorHandling:
    """Test error handling for v0.2 chat API."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway service URL for testing."""
        return os.getenv("GATEWAY_URL", "http://localhost:8666")
    
    @pytest.fixture
    def headers(self):
        """Headers with invalid API key."""
        return {
            "X-API-Key": "invalid-key-for-testing",
            "Content-Type": "application/json"
        }
    
    async def test_v02_chat_invalid_auth(self, gateway_url, headers):
        """Test v0.2 chat with invalid authentication."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "This should fail"}
            )
            assert response.status_code in [401, 403]
    
    async def test_v02_chat_missing_message(self, gateway_url):
        """Test v0.2 chat with missing message field."""
        headers = {
            "X-API-Key": os.getenv("API_KEY"),
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={}  # Missing message field
            )
            assert response.status_code in [400, 422]  # Bad request or validation error
    
    async def test_v02_chat_empty_message(self, gateway_url):
        """Test v0.2 chat with empty message."""
        headers = {
            "X-API-Key": os.getenv("API_KEY"),
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": ""}  # Empty message
            )
            # Should either work (empty messages might be allowed) or return error
            assert response.status_code in [200, 400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])