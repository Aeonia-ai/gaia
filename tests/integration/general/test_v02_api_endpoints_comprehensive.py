"""
Comprehensive v0.2 API endpoint tests for Gaia Platform.
Migrated from manual test scripts for automated testing.
Tests v0.2 API endpoints specifically.
"""

import pytest
import httpx
import os
import asyncio
from typing import Dict, Any, List, Tuple
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestAuthManager

logger = setup_service_logger("test_v02_api_comprehensive")


class TestV02ComprehensiveAPIEndpoints:
    """Test all major v0.2 API endpoints."""
    
    pytestmark = pytest.mark.xdist_group("v02_comprehensive")
    
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
    def v02_endpoints(self, gateway_url) -> List[Tuple[str, str, Dict[str, Any], str]]:
        """List of v0.2 endpoints to test with method, URL, data, and description."""
        return [
            # Health checks and version info
            ("GET", f"{gateway_url}/health", None, "Gateway health"),
            ("GET", f"{gateway_url}/", None, "Root endpoint (version info)"),
            
            # v0.2 API tests
            ("POST", f"{gateway_url}/api/v0.2/chat", {"message": "Hello v0.2! Test message"}, "v0.2 chat completion"),
            ("GET", f"{gateway_url}/api/v0.2/chat/status", None, "v0.2 chat status"),
            ("DELETE", f"{gateway_url}/api/v0.2/chat/history", None, "v0.2 clear chat history"),
            ("GET", f"{gateway_url}/api/v0.2/providers", None, "v0.2 providers list"),
            ("GET", f"{gateway_url}/api/v0.2/models", None, "v0.2 models list"),
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
    async def test_v02_all_endpoints_respond(self, v02_endpoints, headers):
        """Test that all v0.2 endpoints respond (not necessarily successfully, but respond)."""
        results = []
        
        for method, url, data, description in v02_endpoints:
            logger.info(f"Testing: {description}")
            success, status_code, response_data = await self.make_request(method, url, headers, data)
            
            # Service should respond (not connection error)
            assert status_code != 0, f"Connection failed for {description}: {response_data.get('error')}"
            
            results.append((description, success, status_code, response_data))
            logger.info(f"  {description}: {status_code} - {'✅ Success' if success else '❌ Failed'}")
        
        # Log summary
        total_tests = len(results)
        passed_tests = sum(1 for _, success, _, _ in results if success)
        logger.info(f"v0.2 Summary: {passed_tests}/{total_tests} endpoints successful")
        
        # At least some core endpoints should work
        assert passed_tests > 0, "No v0.2 endpoints responded successfully"
    
    @pytest.mark.asyncio
    async def test_v02_chat_endpoint_functional(self, gateway_url, headers):
        """Test that v0.2 chat endpoint works and returns v0.2 response format."""
        success, status_code, response_data = await self.make_request(
            "POST", f"{gateway_url}/api/v0.2/chat", headers, 
            {"message": "Hello! How are you? Please respond briefly."}
        )
        
        assert success, f"v0.2 chat endpoint failed: {status_code} - {response_data}"
        
        # v0.2 should have a "response" field
        assert "response" in response_data, f"No response field in v0.2 chat response: {response_data}"
        assert isinstance(response_data["response"], str), "v0.2 response should be a string"
        assert len(response_data["response"]) > 0, "v0.2 response should not be empty"
        
        # v0.2 should expose provider/model details
        assert "provider" in response_data, "v0.2 should expose provider details"
        assert "model" in response_data, "v0.2 should expose model details"
        
        logger.info(f"v0.2 chat response preview: {response_data['response'][:100]}...")
    
    @pytest.mark.asyncio
    async def test_v02_provider_and_model_endpoints(self, gateway_url, headers):
        """Test v0.2 provider and model listing endpoints."""
        endpoint_tests = [
            ("GET", f"{gateway_url}/api/v0.2/providers", "providers"),
            ("GET", f"{gateway_url}/api/v0.2/models", "models"),
        ]
        
        for method, url, expected_field in endpoint_tests:
            success, status_code, response_data = await self.make_request(method, url, headers)
            
            if success:
                # Should have data
                if isinstance(response_data, dict):
                    assert len(response_data) > 0, f"Empty response from {url}"
                elif isinstance(response_data, list):
                    assert len(response_data) > 0, f"Empty list from {url}"
                
                logger.info(f"v0.2 Endpoint {url}: returned {len(response_data)} items")
            else:
                logger.warning(f"v0.2 Endpoint failed: {url} - {status_code}: {response_data}")
    
    @pytest.mark.asyncio
    async def test_v02_chat_history_management(self, gateway_url, headers):
        """Test v0.2 chat history creation and clearing."""
        # Send a message to create history
        success, status_code, response_data = await self.make_request(
            "POST", f"{gateway_url}/api/v0.2/chat", headers, 
            {"message": "Remember my name is TestUser v0.2"}
        )
        
        assert success, f"Failed to create v0.2 chat history: {status_code} - {response_data}"
        logger.info("Created v0.2 chat history successfully")
        
        # Check status shows history
        success, status_code, status_data = await self.make_request(
            "GET", f"{gateway_url}/api/v0.2/chat/status", headers
        )
        
        if success and "has_history" in status_data:
            logger.info(f"v0.2 Chat status: {status_data}")
        
        # Clear history
        success, status_code, clear_data = await self.make_request(
            "DELETE", f"{gateway_url}/api/v0.2/chat/history", headers
        )
        
        if success:
            logger.info("Cleared v0.2 chat history successfully")
            assert "status" in clear_data or "cleared" in str(clear_data).lower()

    @pytest.mark.asyncio
    async def test_v02_response_format_consistency(self, gateway_url, headers):
        """Test that v0.2 responses are consistent across requests."""
        test_messages = [
            "What is 2+2?",
            "Tell me a joke",
            "What's the weather like?"
        ]
        
        for message in test_messages:
            success, status_code, response_data = await self.make_request(
                "POST", f"{gateway_url}/api/v0.2/chat", headers, 
                {"message": message}
            )
            
            assert success, f"v0.2 request failed for '{message}': {status_code}"
            
            # Check consistent v0.2 format
            assert "response" in response_data, f"Missing 'response' field for message: {message}"
            assert "provider" in response_data, f"Missing 'provider' field for message: {message}"
            assert "model" in response_data, f"Missing 'model' field for message: {message}"
            
            # Should NOT have v1/OpenAI format fields
            assert "choices" not in response_data, "v0.2 should not have 'choices' field"
            assert "object" not in response_data, "v0.2 should not have 'object' field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])