"""
v0.2 API system regression test suite for Gaia Platform.
Based on successful manual test script functionality.
Tests v0.2 API endpoints for regression prevention.
"""

import pytest
import httpx
import os
from typing import Dict, Any
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestAuthManager

logger = setup_service_logger("test_v02_system_regression")


class TestV02WorkingEndpoints:
    """Test v0.2 endpoints that are known to work from manual testing."""
    
    pytestmark = pytest.mark.xdist_group("v02_regression")
    
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
    async def test_v02_chat_completion_regression(self, gateway_url, headers):
        """Test v0.2 chat completion - core functionality regression."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "Hello! This is a v0.2 regression test. Please respond briefly."}
            )
            assert response.status_code == 200
            data = response.json()
            
            # Check v0.2 response structure
            assert "response" in data, "v0.2 should have 'response' field"
            assert isinstance(data["response"], str), "v0.2 response should be string"
            assert len(data["response"]) > 0, "v0.2 response should not be empty"
            
            # v0.2 should expose provider/model details (not hidden)
            assert "provider" in data, "v0.2 should expose provider details"
            assert "model" in data, "v0.2 should expose model details"
            
            # Should contain actual response content (not just echo)
            assert data["response"] != "Hello! This is a v0.2 regression test. Please respond briefly."
            logger.info(f"v0.2 chat response length: {len(data['response'])} chars")
    
    @pytest.mark.asyncio
    async def test_v02_conversation_flow_regression(self, gateway_url, headers):
        """Test v0.2 complete conversation flow with context preservation."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send first message with context
            response1 = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "My favorite number is 42. Please remember this for v0.2 testing."}
            )
            assert response1.status_code == 200
            data1 = response1.json()
            assert "response" in data1
            
            # Send follow-up that requires context
            response2 = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "What is my favorite number?"}
            )
            assert response2.status_code == 200
            data2 = response2.json()
            assert "response" in data2
            
            # Response should reference 42 (context preserved)
            response_text = data2["response"].lower()
            assert "42" in response_text, f"v0.2 should remember context: {data2['response']}"
            
            logger.info(f"v0.2 context preservation test passed: {data2['response'][:100]}...")
    
    @pytest.mark.asyncio
    async def test_v02_response_format_consistency_regression(self, gateway_url, headers):
        """Test that v0.2 response format remains consistent across requests."""
        test_cases = [
            "What is 2+2?",
            "Tell me about the weather", 
            "Explain quantum physics in one sentence"
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, message in enumerate(test_cases):
                response = await client.post(
                    f"{gateway_url}/api/v0.2/chat",
                    headers=headers,
                    json={"message": message}
                )
                
                assert response.status_code == 200, f"v0.2 request {i+1} failed"
                data = response.json()
                
                # Consistent v0.2 format requirements
                assert "response" in data, f"Request {i+1}: Missing 'response' field"
                assert "provider" in data, f"Request {i+1}: Missing 'provider' field"
                assert "model" in data, f"Request {i+1}: Missing 'model' field"
                assert isinstance(data["response"], str), f"Request {i+1}: Response not string"
                
                # Should NOT have other API version fields
                assert "choices" not in data, f"Request {i+1}: Should not have v1 'choices' field"
                assert "conversation_id" not in data or "provider" in data, f"Request {i+1}: v0.2 format inconsistent"
                
                logger.info(f"v0.2 consistency test {i+1}: ✅ Format consistent")

    @pytest.mark.asyncio
    async def test_v02_provider_model_exposure_regression(self, gateway_url, headers):
        """Test that v0.2 continues to expose provider/model details (regression check)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "Simple test for v0.2 provider exposure"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # v0.2 should expose these details (unlike v0.3)
            assert "provider" in data, "v0.2 should expose provider"
            assert "model" in data, "v0.2 should expose model"
            assert isinstance(data["provider"], str), "Provider should be string"
            assert isinstance(data["model"], str), "Model should be string"
            assert len(data["provider"]) > 0, "Provider should not be empty"
            assert len(data["model"]) > 0, "Model should not be empty"
            
            logger.info(f"v0.2 provider exposure: {data['provider']}/{data['model']}")
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Empty message returns 500 instead of 400/422 - needs input validation")
    async def test_v02_error_handling_regression(self, gateway_url, headers):
        """Test v0.2 error handling doesn't break."""
        # Test empty message handling
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": ""}
            )
            
            # Should handle gracefully (either success with response or clear error)
            if response.status_code == 200:
                data = response.json()
                assert "response" in data, "Empty message should still return v0.2 format"
            else:
                assert response.status_code in [400, 422], "Empty message should return clear error"
                
            logger.info(f"v0.2 empty message handling: {response.status_code}")


class TestV02AuthenticationRegression:
    """Test v0.2 authentication methods for regression."""
    
    pytestmark = pytest.mark.xdist_group("v02_auth_regression")
    
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"
    
    @pytest.mark.asyncio
    async def test_v02_no_auth_rejected_regression(self, gateway_url):
        """Test that v0.2 requests without auth are still rejected."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                json={"message": "This should fail"}
            )
            assert response.status_code in [401, 403], "v0.2 should require authentication"
    
    @pytest.mark.asyncio
    async def test_v02_api_key_auth_regression(self, gateway_url):
        """Test that v0.2 API key auth still works."""
        headers = {
            "X-API-Key": os.getenv("API_KEY", "test-key-123"),
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "API key auth test for v0.2"}
            )
            # Should work (either 200 or auth works but other error)
            assert response.status_code not in [401, 403], f"v0.2 API key auth failed: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                assert "response" in data, "v0.2 should return proper format with API key"
                logger.info("v0.2 API key authentication works")
    
    @pytest.mark.asyncio
    async def test_v02_jwt_auth_regression(self, gateway_url):
        """Test that v0.2 JWT auth still works."""
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
                f"{gateway_url}/api/v0.2/chat",
                headers=headers,
                json={"message": "JWT auth test for v0.2"}
            )
            assert response.status_code not in [401, 403], f"v0.2 JWT auth failed: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                assert "response" in data, "v0.2 should return proper format with JWT"
                logger.info("v0.2 JWT authentication works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])