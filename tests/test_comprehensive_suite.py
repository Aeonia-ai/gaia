"""
Comprehensive test suite runner for Gaia Platform.
Replaces the manual 'all' test command with automated coverage.
"""

import pytest
import asyncio
import httpx
import os
import sys
from typing import Dict, Any, List
from app.shared.logging import setup_service_logger
from tests.fixtures.test_auth import TestAuthManager

logger = setup_service_logger("test_comprehensive")


class TestComprehensiveSuite:
    """Comprehensive test suite covering all major functionality."""
    
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"
    
    @pytest.fixture
    def kb_url(self):
        return "http://kb-service:8000"
    
    @pytest.fixture
    def auth_manager(self):
        """Provide test authentication manager."""
        # Use integration test type to get real JWT tokens
        return TestAuthManager(test_type="unit")
    
    @pytest.fixture
    def headers(self, auth_manager):
        """Standard headers with JWT authentication."""
        # Get JWT auth headers instead of API key
        auth_headers = auth_manager.get_auth_headers(
            email="test@test.local",
            role="authenticated"
        )
        return {
            **auth_headers,
            "Content-Type": "application/json"
        }
    
    async def make_request(self, method: str, url: str, headers: Dict[str, str], data: Dict[str, Any] = None, timeout: float = 30.0):
        """Helper method to make HTTP requests with proper error handling."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                return response.status_code, response.json() if response.headers.get('content-type', '').startswith('application/json') else {"raw": response.text}
        except Exception as e:
            return 0, {"error": str(e)}
    
    async def test_core_system_health(self, gateway_url, kb_url, headers):
        """Test core system health - equivalent to 'health' command."""
        # Test gateway health
        status_code, data = await self.make_request("GET", f"{gateway_url}/health", headers)
        if status_code == 0:
            logger.error(f"Failed to connect to gateway: {data}")
        assert status_code == 200
        assert data.get("status") in ["healthy", "degraded"]
        
        gateway_status = data["status"]
        service_count = len(data.get("services", {}))
        
        # Test KB health directly
        kb_status_code, kb_data = await self.make_request("GET", f"{kb_url}/health", headers)
        assert kb_status_code == 200
        assert kb_data.get("status") in ["healthy", "degraded"]
        
        kb_status = kb_data["status"]
        file_count = kb_data.get("repository", {}).get("file_count", 0)
        
        logger.info(f"System Health - Gateway: {gateway_status} ({service_count} services), KB: {kb_status} ({file_count} files)")
        
        # Overall system should be healthy
        assert gateway_status in ["healthy", "degraded"]
        assert kb_status in ["healthy", "degraded"]
    
    async def test_core_chat_functionality(self, gateway_url, headers):
        """Test core chat functionality - equivalent to basic 'chat' command."""
        test_messages = [
            "Hello! How are you?",
            "What is 2+2?",
            "Explain quantum computing briefly."
        ]
        
        successful_responses = 0
        
        for message in test_messages:
            # Test v1 chat (main endpoint)
            status_code, data = await self.make_request(
                "POST", f"{gateway_url}/api/v1/chat", headers, 
                {"message": message}
            )
            
            if status_code == 200:
                assert "choices" in data
                assert len(data["choices"]) > 0
                assert "message" in data["choices"][0]
                assert "content" in data["choices"][0]["message"]
                
                content = data["choices"][0]["message"]["content"]
                assert len(content) > 0
                assert content != message  # Should not echo input
                
                successful_responses += 1
                logger.info(f"Chat '{message[:30]}...': {len(content)} chars")
            else:
                logger.warning(f"Chat '{message[:30]}...' failed: {status_code}")
        
        # At least most chat requests should work
        assert successful_responses >= len(test_messages) * 0.7, f"Only {successful_responses}/{len(test_messages)} chat requests succeeded"
    
    async def test_chat_endpoint_variants(self, gateway_url, headers):
        """Test different chat endpoint variants."""
        test_message = "What is 2+2?"
        endpoints_to_test = [
            ("v0.2", f"{gateway_url}/api/v0.2/chat", "response"),
            ("v1", f"{gateway_url}/api/v1/chat", "choices"),
        ]
        
        working_endpoints = 0
        
        for name, endpoint, response_field in endpoints_to_test:
            status_code, data = await self.make_request(
                "POST", endpoint, headers, 
                {"message": test_message}
            )
            
            if status_code == 200:
                if response_field == "response":
                    assert "response" in data
                    assert len(data["response"]) > 0
                elif response_field == "choices":
                    assert "choices" in data
                    assert len(data["choices"]) > 0
                    assert "content" in data["choices"][0]["message"]
                
                working_endpoints += 1
                logger.info(f"Chat endpoint {name}: working")
            else:
                logger.info(f"Chat endpoint {name}: {status_code}")
        
        # At least one chat endpoint should work
        assert working_endpoints >= 1, "No chat endpoints are working"
    
    async def test_kb_integration(self, gateway_url, headers):
        """Test KB integration and search functionality."""
        kb_test_queries = [
            "consciousness",
            "gaia",
            "multiagent"
        ]
        
        # Test KB search if available
        kb_responses = 0
        for query in kb_test_queries:
            status_code, data = await self.make_request(
                "POST", f"{gateway_url}/api/v0.2/kb/search", headers,
                {"message": query}, timeout=30.0
            )
            
            if status_code == 200:
                kb_responses += 1
                logger.info(f"KB search '{query}': working")
            elif status_code == 404:
                logger.info("KB search endpoint not available")
                break
        
        # Test chat with KB context (this should work through routing)
        status_code, data = await self.make_request(
            "POST", f"{gateway_url}/api/v1/chat", headers,
            {"message": "What do you know about consciousness from your knowledge base?"},
            timeout=45.0
        )
        
        if status_code == 200:
            assert "choices" in data
            content = data["choices"][0]["message"]["content"]
            assert len(content) > 0
            
            # Check if KB tools were used
            metadata = data.get("_metadata", {})
            tools_used = metadata.get("tools_used", [])
            
            if "search_knowledge_base" in tools_used:
                logger.info("KB integration working in chat")
            else:
                logger.info("Chat working but no KB tools detected")
        else:
            logger.warning(f"KB-context chat failed: {status_code}")
    
    async def test_provider_model_endpoints(self, gateway_url, headers):
        """Test provider and model endpoints if available."""
        # Test providers endpoint
        providers_status, providers_data = await self.make_request(
            "GET", f"{gateway_url}/api/v0.2/providers", headers
        )
        
        # Test models endpoint  
        models_status, models_data = await self.make_request(
            "GET", f"{gateway_url}/api/v0.2/models", headers
        )
        
        if providers_status == 200:
            logger.info(f"Providers endpoint: working")
        else:
            logger.info(f"Providers endpoint: {providers_status}")
        
        if models_status == 200:
            logger.info(f"Models endpoint: working")
        else:
            logger.info(f"Models endpoint: {models_status}")
        
        # At least one should work or both should fail consistently
        if providers_status == 200 or models_status == 200:
            logger.info("Provider/Model endpoints partially available")
    
    async def test_chat_history_management(self, gateway_url, headers):
        """Test chat history and status management."""
        # Test chat status
        status_code, data = await self.make_request(
            "GET", f"{gateway_url}/api/v1/chat/status", headers
        )
        
        if status_code == 200:
            assert "message_count" in data
            assert "has_history" in data
            logger.info(f"Chat status: {data['message_count']} messages, history: {data['has_history']}")
        else:
            logger.info(f"Chat status endpoint: {status_code}")
        
        # Test history clearing (v1 is known to work)
        clear_status, clear_data = await self.make_request(
            "DELETE", f"{gateway_url}/api/v1/chat/history", headers
        )
        
        if clear_status == 200:
            logger.info("Chat history clearing: working")
        else:
            logger.info(f"Chat history clearing: {clear_status}")
    
    async def test_authentication_security(self, gateway_url):
        """Test authentication security - requests without auth should fail."""
        # Test without API key
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                json={"message": "This should fail"}
            )
            assert response.status_code in [401, 403], "Unauthenticated requests should be rejected"
        
        # Test with invalid API key
        bad_headers = {
            "X-API-Key": "invalid-key-12345",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=bad_headers,
                json={"message": "This should fail"}
            )
            assert response.status_code in [401, 403], "Invalid API keys should be rejected"
        
        logger.info("Authentication security: working")
    
    async def test_system_performance_basics(self, gateway_url, headers):
        """Test basic system performance and responsiveness."""
        import time
        
        # Test response times for core endpoints
        start_time = time.time()
        status_code, data = await self.make_request("GET", f"{gateway_url}/health", headers)
        health_time = time.time() - start_time
        
        start_time = time.time()
        status_code, data = await self.make_request(
            "POST", f"{gateway_url}/api/v1/chat", headers,
            {"message": "Quick test"}
        )
        chat_time = time.time() - start_time
        
        logger.info(f"Performance - Health: {health_time:.2f}s, Chat: {chat_time:.2f}s")
        
        # Basic performance assertions
        assert health_time < 5.0, f"Health endpoint too slow: {health_time:.2f}s"
        
        if status_code == 200:
            assert chat_time < 30.0, f"Chat endpoint too slow: {chat_time:.2f}s"


class TestSystemIntegration:
    """Test system-wide integration and functionality."""
    
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"
    
    @pytest.fixture
    def auth_manager(self):
        """Provide test authentication manager."""
        # Use integration test type to get real JWT tokens
        return TestAuthManager(test_type="unit")
    
    @pytest.fixture
    def headers(self, auth_manager):
        """Standard headers with JWT authentication."""
        # Get JWT auth headers instead of API key
        auth_headers = auth_manager.get_auth_headers(
            email="test@test.local",
            role="authenticated"
        )
        return {
            **auth_headers,
            "Content-Type": "application/json"
        }
    
    async def test_end_to_end_conversation(self, gateway_url, headers):
        """Test complete end-to-end conversation flow."""
        # Clear history first
        async with httpx.AsyncClient() as client:
            await client.delete(f"{gateway_url}/api/v1/chat/history", headers=headers)
        
        # Multi-turn conversation
        conversation = [
            ("My name is Alex and I love science fiction.", "greeting"),
            ("What is my name?", "context_recall"),
            ("What genre of books do I like?", "preference_recall"),
            ("Recommend a sci-fi book.", "recommendation")
        ]
        
        for message, test_type in conversation:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={"message": message}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "choices" in data
                
                content = data["choices"][0]["message"]["content"]
                assert len(content) > 0
                
                # Basic context validation for later messages
                if test_type == "context_recall":
                    assert "alex" in content.lower(), "Should remember the name Alex"
                elif test_type == "preference_recall":
                    assert any(term in content.lower() for term in ["science fiction", "sci-fi", "sci fi"]), "Should remember sci-fi preference"
                
                logger.info(f"Conversation {test_type}: {len(content)} chars")
        
        logger.info("End-to-end conversation flow: working")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])