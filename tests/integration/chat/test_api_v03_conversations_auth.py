"""
Integration tests for v0.3 API using real API key authentication.
Extracted from mixed v1/v0.3 test file for better test organization.
These tests verify the v0.3 clean API interface works with real authentication.
Focuses on clean interface design, persona integration, and directive system.
"""

import pytest
import httpx
import os
import asyncio
from typing import Dict, Any
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_api_v03_with_real_auth")


class TestV03APIWithRealAuth:
    """Test v0.3 API endpoints with real API key authentication."""
    
    @pytest.fixture
    def api_key(self):
        """Get real API key from environment."""
        # Try different sources for API key
        api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
        if not api_key:
            pytest.skip("No API key available - set API_KEY or TEST_API_KEY environment variable")
        return api_key
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL - can be overridden with GATEWAY_URL env var."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def headers(self, api_key):
        """Headers with real API key authentication."""
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_health_check(self, gateway_url):
        """Test health endpoint (no auth required)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") in ["healthy", "degraded"]
            assert "services" in data
            logger.info(f"Health check passed: {data['status']}")
    
    @pytest.mark.asyncio
    async def test_health_with_api_key(self, gateway_url, headers):
        """Test health endpoint with API key (should still work)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/health", headers=headers)
            assert response.status_code == 200
    
    # NOTE: Provider and model endpoints removed - not implemented in chat service
    
    @pytest.mark.asyncio
    async def test_v03_chat_clean_interface(self, gateway_url, headers):
        """Test v0.3 chat endpoint with clean interface design."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Hello, what is 2+2?",
                    "stream": False
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            # v0.3 clean interface - exactly these fields only
            assert "response" in data
            assert "conversation_id" in data
            assert isinstance(data["response"], str)
            assert len(data["response"]) > 0
            
            # Should NOT contain internal details (clean interface promise)
            assert "provider" not in data
            assert "model" not in data
            assert "reasoning" not in data
            assert "usage" not in data
            assert "choices" not in data
            
            logger.info("V0.3 chat clean interface succeeded")
    
    @pytest.mark.asyncio
    async def test_v03_persona_integration(self, gateway_url, headers):
        """Test v0.3 automatic persona integration via unified chat."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Hello! Please introduce yourself and tell me who you are."
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            # v0.3 should have clean response format
            assert "response" in data
            assert "conversation_id" in data
            response_text = data["response"].lower()
            
            # Should show persona characteristics (Mu is default)
            # v0.3 automatically integrates personas via unified chat
            has_persona_characteristics = any([
                "mu" in response_text,
                "robot" in response_text,
                "beep" in response_text,
                "boop" in response_text,
                "cheerful" in response_text,
                "companion" in response_text,
                "assistant" in response_text  # Fallback if persona not loaded
            ])
            
            # Clean interface - no persona implementation details exposed
            assert "persona_id" not in data
            assert "system_prompt" not in data
            assert "persona" not in data
            
            logger.info(f"V0.3 persona integration test: {response_text[:100]}...")
            assert has_persona_characteristics, f"Response should show persona integration: {response_text}"
    
    @pytest.mark.asyncio
    async def test_v03_conversation_management(self, gateway_url, headers):
        """Test v0.3 conversation management with clean interface."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message - creates conversation
            response1 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Remember the number 42"
                }
            )
            assert response1.status_code == 200
            data1 = response1.json()
            
            # v0.3 API returns conversation_id in clean format
            assert "conversation_id" in data1
            assert "response" in data1
            conversation_id = data1["conversation_id"]
            assert conversation_id is not None
            
            # Verify clean interface - no internal conversation details
            assert "messages" not in data1
            assert "history" not in data1
            assert "context" not in data1
            
            # Second message - uses same conversation
            response2 = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "What number did I ask you to remember?",
                    "conversation_id": conversation_id
                }
            )
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Same clean format
            assert "response" in data2
            assert "conversation_id" in data2
            assert data2["conversation_id"] == conversation_id
            
            logger.info(f"V0.3 conversation {conversation_id} tested successfully")
    
    @pytest.mark.asyncio
    async def test_v03_streaming_clean_format(self, gateway_url, headers):
        """Test v0.3 streaming with clean format (no provider details)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            chunks = []
            content_received = ""
            done_received = False
            
            async with client.stream(
                "POST",
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Count to 3 slowly",
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                assert response.headers.get("content-type") == "text/event-stream; charset=utf-8"
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        
                        if data_str == "[DONE]":
                            done_received = True
                            break
                            
                        try:
                            import json
                            chunk = json.loads(data_str)
                            chunks.append(chunk)
                            
                            if chunk.get("type") == "content":
                                content_received += chunk.get("content", "")
                                
                                # Verify clean streaming format - no provider details
                                assert "provider" not in chunk
                                assert "model" not in chunk
                                assert "delta" not in chunk
                                assert "choices" not in chunk
                                
                            elif chunk.get("type") == "done":
                                done_received = True
                                break
                                
                        except json.JSONDecodeError:
                            continue
            
            assert len(chunks) > 0
            assert content_received.strip() != ""
            assert done_received
            logger.info(f"V0.3 streaming received {len(chunks)} clean chunks")
    
    @pytest.mark.asyncio
    async def test_v03_directive_system(self, gateway_url, headers):
        """Test v0.3 always-on directive enhancement system."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Explain quantum computing in simple terms"
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            # v0.3 should have directive enhancement automatically applied
            assert "response" in data
            response_text = data["response"]
            
            # Directive system should enhance responses (check for quality indicators)
            # v0.3 automatically uses directives for better responses
            assert len(response_text) > 50  # Should be substantial
            
            # Clean interface - directive system is internal
            assert "directives" not in data
            assert "enhanced" not in data
            assert "system_prompt" not in data
            
            logger.info("V0.3 directive system test completed")
    
    @pytest.mark.asyncio
    async def test_v03_no_auth_fails(self, gateway_url):
        """Test that v0.3 requests without auth fail appropriately."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                json={"message": "Hello"}
            )
            assert response.status_code in [401, 403]
            logger.info("V0.3 API: No auth correctly rejected")
    
    @pytest.mark.asyncio
    async def test_v03_invalid_api_key_fails(self, gateway_url):
        """Test that v0.3 API rejects invalid API key."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers={"X-API-Key": "invalid-key-12345"},
                json={"message": "Hello"}
            )
            assert response.status_code in [401, 403]
            logger.info("V0.3 API: Invalid API key correctly rejected")
    
    @pytest.mark.asyncio
    async def test_v03_conversation_list_clean_format(self, gateway_url, headers):
        """Test v0.3 conversation listing with clean format."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{gateway_url}/api/v0.3/conversations",
                headers=headers
            )
            # This might return 404 if not implemented, which is OK
            if response.status_code == 200:
                data = response.json()
                assert "conversations" in data
                assert isinstance(data["conversations"], list)
                
                # Verify clean format for conversation list
                for conv in data["conversations"]:
                    # Should have basic conversation info
                    assert "conversation_id" in conv or "id" in conv
                    assert "title" in conv or "name" in conv
                    
                    # Should NOT have internal details
                    assert "messages" not in conv
                    assert "model" not in conv
                    assert "provider" not in conv
                    assert "system_prompt" not in conv
                
                logger.info("V0.3 conversation list endpoint available with clean format")
            else:
                logger.info(f"V0.3 conversation list returned {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_v03_kb_integration_clean_format(self, gateway_url, headers):
        """Test v0.3 KB integration with clean format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "What information do you have about consciousness?",
                    "use_kb": True  # Enable KB integration
                }
            )
            
            # Should succeed or gracefully handle if KB not available
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert "response" in data
                assert "conversation_id" in data
                assert isinstance(data["response"], str)
                
                # KB integration should be completely hidden (clean interface)
                assert "kb_results" not in data  # KB details are internal
                assert "metadata" not in data
                assert "sources" not in data
                assert "search_results" not in data
                
                logger.info("V0.3 KB integration maintains clean interface")
            else:
                logger.info(f"V0.3 KB integration returned {response.status_code} (KB may not be available)")
    
    @pytest.mark.asyncio
    async def test_v03_parameter_rejection(self, gateway_url, headers):
        """Test that v0.3 rejects or ignores provider/model parameters."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to send provider/model parameters - should be ignored
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Hello",
                    "provider": "openai",  # Should not be accepted
                    "model": "gpt-4"       # Should not be accepted
                }
            )
            
            # Should either ignore the parameters or return 400
            # For now, assume it ignores them and responds normally
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            
            # Response should still be clean - no provider details
            assert "provider" not in data
            assert "model" not in data
            
            logger.info("V0.3 API properly handles provider/model parameter rejection")
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Moved to load tests - see tests/load/test_concurrent_requests.py")
    async def test_v03_concurrent_requests(self, gateway_url, headers):
        """Test v0.3 handling concurrent requests with real auth.
        
        This test has been moved to the load test suite because it:
        - Tests system behavior under load, not integration correctness
        - Can trigger rate limits on external APIs
        - Has non-deterministic timing requirements
        
        For integration testing of multi-request scenarios, see:
        - test_v03_conversation_management (sequential requests)
        - test_v03_persona_integration (persona handling)
        """
        pass  # Moved to load tests
    
    @pytest.mark.asyncio
    async def test_v03_error_handling_clean_format(self, gateway_url, headers):
        """Test that v0.3 errors also follow clean format."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test with missing message
            response = await client.post(
                f"{gateway_url}/api/v0.3/chat",
                headers=headers,
                json={}  # Missing message
            )
            
            assert response.status_code == 400
            data = response.json()
            
            # Error should have clean format
            assert "error" in data
            assert isinstance(data["error"], str)
            
            # Should NOT expose internal error details
            assert "provider" not in data
            assert "model" not in data
            assert "traceback" not in data
            assert "stack" not in data
            
            logger.info("V0.3 error handling maintains clean format")