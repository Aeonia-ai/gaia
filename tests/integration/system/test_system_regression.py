"""
Test suite for known working Gaia Platform endpoints.
Based on successful manual test script functionality.
"""

import pytest
import httpx
import os
from typing import Dict, Any
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestAuthManager

logger = setup_service_logger("test_system_regression")


class TestWorkingEndpoints:
    """Test endpoints that are known to work from manual testing."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway service URL for testing."""
        return "http://gateway:8000"  # Docker internal URL
    
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
    
    async def test_gateway_health(self, gateway_url, headers):
        """Test main gateway health endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") in ["healthy", "degraded"]
            assert "services" in data
            assert "timestamp" in data
            logger.info(f"Gateway health: {data['status']}")
    
    async def test_root_endpoint(self, gateway_url):
        """Test root endpoint returns version info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data or "version" in data
            logger.info(f"Root endpoint response: {data}")
    
    
    async def test_v1_chat_completion(self, gateway_url, headers):
        """Test v1 chat completion - legacy support."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Hello v1! Please respond briefly."}
            )
            assert response.status_code == 200
            data = response.json()
            
            # Check response structure (OpenAI-compatible format)
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]
            assert "content" in data["choices"][0]["message"]
            
            content = data["choices"][0]["message"]["content"]
            assert isinstance(content, str)
            assert len(content) > 0
            assert content != "Hello v1! Please respond briefly."
            logger.info(f"v1 chat response length: {len(content)} chars")
    
    @pytest.mark.skip(reason="Chat status endpoint deprecated - system uses conversation-based storage")
    async def test_v1_chat_status(self, gateway_url, headers):
        """Test v1 chat status endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/api/v1/chat/status", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "message_count" in data
            assert "has_history" in data
            logger.info(f"v1 chat status: {data['message_count']} messages, history: {data['has_history']}")
    
    @pytest.mark.skip(reason="Clear history endpoint deprecated - was scaffolding for persona development")
    async def test_clear_v1_chat_history(self, gateway_url, headers):
        """Test clearing v1 chat history (known to work)."""
        async with httpx.AsyncClient() as client:
            # Test v1 clear (this works)
            response_v1 = await client.delete(f"{gateway_url}/api/v1/chat/history", headers=headers)
            assert response_v1.status_code == 200
            data_v1 = response_v1.json()
            assert data_v1.get("status") == "success"
            
            logger.info("Successfully cleared v1 chat history")
    
    async def test_conversation_flow(self, gateway_url, headers):
        """Test complete conversation flow with context preservation."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Clear history first
            await client.delete(f"{gateway_url}/api/v1/chat/history", headers=headers)
            
            # Send first message with context
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "My favorite color is blue. Please remember this."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            # Extract conversation_id from metadata if available
            conversation_id = None
            if "_metadata" in data1 and "conversation_id" in data1["_metadata"]:
                conversation_id = data1["_metadata"]["conversation_id"]
            
            # Send follow-up that requires context
            request_data = {"message": "What is my favorite color?"}
            if conversation_id:
                request_data["conversation_id"] = conversation_id
                
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json=request_data
            )
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Extract response text from v1 format
            if "choices" in data2:
                response_text = data2["choices"][0]["message"]["content"].lower()
            else:
                response_text = data2.get("response", "").lower()
            
            # Response should reference blue (context preserved)
            assert "blue" in response_text
            
            logger.info(f"Context preservation test passed: {response_text[:100]}...")


class TestAuthenticationMethods:
    """Test different authentication methods."""
    
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"
    
    async def test_no_auth_rejected(self, gateway_url):
        """Test that requests without auth are rejected."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                json={"message": "This should fail"}
            )
            assert response.status_code == 401
    
    async def test_invalid_api_key_rejected(self, gateway_url):
        """Test that invalid API keys are rejected."""
        headers = {
            "X-API-Key": "invalid-key-12345",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "This should fail"}
            )
            assert response.status_code == 401
    
    async def test_valid_api_key_accepted(self, gateway_url):
        """Test that valid API key is accepted."""
        headers = {
            "X-API-Key": os.getenv("API_KEY"),
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "This should work"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "choices" in data or "response" in data


class TestAPICompatibility:
    """Test API compatibility between versions."""
    
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"
    
    @pytest.fixture
    def headers(self):
        return {
            "X-API-Key": os.getenv("API_KEY"),
            "Content-Type": "application/json"
        }
    
    async def test_v1_v03_response_formats(self, gateway_url, headers):
        """Test that v1 and v0.3 return expected response formats."""
        test_message = "What is 2+2? Answer briefly."
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test v1 format  
            v1_response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": test_message}
            )
            
            # Test v0.3 format
            v03_response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={"message": test_message}
            )
        
        # Both should succeed
        assert v1_response.status_code == 200
        assert v03_response.status_code == 200
        
        # Check v1 format (OpenAI-compatible)
        v1_data = v1_response.json()
        assert "choices" in v1_data
        assert "message" in v1_data["choices"][0]
        assert "content" in v1_data["choices"][0]["message"]
        
        # Check v0.3 format (clean)
        v03_data = v03_response.json()
        assert "response" in v03_data
        assert isinstance(v03_data["response"], str)
        assert "provider" not in v03_data  # v0.3 hides internals
        
        logger.info("Both v1 and v0.3 APIs return correct response formats")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])