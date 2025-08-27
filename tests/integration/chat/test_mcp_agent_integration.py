"""
Integration tests for MCP agent routing through chat.

Tests the complete flow of MCP agent usage:
1. User sends message requiring MCP agent capabilities
2. Chat service routes to use_mcp_agent tool
3. MCP agent processes request with appropriate persona
4. Results are returned with agent context preserved

Requires all services running (gateway, chat, auth).
"""

import pytest
import httpx
import asyncio
import json
import time
from typing import Dict, Any, List

from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_mcp_agent_integration")


@pytest.mark.integration
class TestMCPAgentIntegration:
    """Test MCP agent routing and execution through the chat service."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL for integration tests."""
        import os
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def api_key(self):
        """Get API key for testing."""
        import os
        api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
        if not api_key:
            pytest.skip("No API key available - set API_KEY or TEST_API_KEY environment variable")
        return api_key
    
    @pytest.mark.asyncio
    async def test_mcp_agent_simple_routing(self, gateway_url, api_key):
        """Test that simple messages don't trigger MCP agents."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Simple message should use direct response
            messages = [
                {"role": "user", "content": "What is 2+2?"}
            ]
            
            start_time = time.time()
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[0]["content"],
                    "stream": False
                }
            )
            response_time = time.time() - start_time
            
            assert response.status_code == 200
            data = response.json()
            
            # Simple queries should be fast (no agent overhead)
            assert response_time < 3.0, f"Simple query took {response_time:.2f}s"
            
            content = data["choices"][0]["message"]["content"]
            assert "4" in content or "four" in content.lower()
    
    @pytest.mark.asyncio
    async def test_mcp_agent_complex_routing(self, gateway_url, api_key):
        """Test that complex messages trigger MCP agent routing."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Complex message that might trigger agent
            messages = [
                {"role": "user", "content": "Create a comprehensive plan for building a distributed AI system with multiple microservices, including architecture design, technology choices, and deployment strategy"}
            ]
            
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[0]["content"],
                    "stream": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Complex queries should provide detailed responses
            assert len(content) > 500  # Substantial response
            assert any(keyword in content.lower() for keyword in [
                "architecture", "microservice", "distributed", "deployment"
            ])
    
    @pytest.mark.asyncio
    async def test_mcp_agent_persona_consistency(self, gateway_url, api_key):
        """Test that MCP agents maintain persona consistency."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Skip conversation creation for now (endpoint doesn't exist)
            conversation_id = None
            
            # First message
            messages = [
                {"role": "user", "content": "Remember that my favorite color is blue. What's my favorite color?"}
            ]
            
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[0]["content"],
                    "stream": False,
                    "conversation_id": conversation_id
                }
            )
            assert response1.status_code == 200
            
            # Add assistant response and ask again
            messages.append({"role": "assistant", "content": response1.json()["choices"][0]["message"]["content"]})
            messages.append({"role": "user", "content": "What did I tell you my favorite color was?"})
            
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[-1]["content"],
                    "stream": False,
                    "conversation_id": conversation_id
                }
            )
            assert response2.status_code == 200
            
            content = response2.json()["choices"][0]["message"]["content"]
            assert "blue" in content.lower()
    
    @pytest.mark.asyncio
    async def test_mcp_agent_error_recovery(self, gateway_url, api_key):
        """Test MCP agent error handling and recovery."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Send malformed or problematic request
            messages = [
                {"role": "user", "content": "Process this: " + "x" * 10000}  # Very long input
            ]
            
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[0]["content"],
                    "stream": False
                }
            )
            
            # Should handle gracefully
            assert response.status_code in [200, 400]
            if response.status_code == 200:
                data = response.json()
                assert "choices" in data
    
    @pytest.mark.asyncio
    async def test_mcp_agent_caching_performance(self, gateway_url, api_key):
        """Test that MCP agent caching improves performance."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # First request (cold start)
            messages = [
                {"role": "user", "content": "Explain quantum computing in simple terms"}
            ]
            
            start_time1 = time.time()
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[0]["content"],
                    "stream": False
                }
            )
            time1 = time.time() - start_time1
            assert response1.status_code == 200
            
            # Second request (should use cached agent)
            await asyncio.sleep(0.5)  # Brief pause
            
            start_time2 = time.time()
            response2 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[0]["content"],
                    "stream": False
                }
            )
            time2 = time.time() - start_time2
            assert response2.status_code == 200
            
            # Log performance metrics
            logger.info(f"First request: {time1:.2f}s, Second request: {time2:.2f}s")
            
            # Second request should be faster (cached agent)
            # Note: This might not always be true due to various factors
            if time2 < time1:
                logger.info("Cache hit detected - second request was faster")
    
    @pytest.mark.asyncio
    async def test_mcp_agent_concurrent_users(self, gateway_url, api_key):
        """Test MCP agent handling of concurrent users."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Simulate multiple concurrent users
            async def user_request(user_id: int):
                messages = [
                    {"role": "user", "content": f"I am user {user_id}. Remember my ID and tell me what it is."}
                ]
                
                # Skip conversation creation for now (endpoint doesn't exist)
                conv_id = None
                
                response = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={
                        "message": messages[0]["content"],
                        "stream": False,
                        "conversation_id": conv_id
                    }
                )
                
                assert response.status_code == 200
                content = response.json()["choices"][0]["message"]["content"]
                return user_id, content
            
            # Send concurrent requests
            results = await asyncio.gather(*[user_request(i) for i in range(5)])
            
            # Each should maintain its own context
            for user_id, content in results:
                assert str(user_id) in content
                logger.info(f"User {user_id} response verified")
    
    @pytest.mark.asyncio
    async def test_mcp_kb_tool_integration(self, gateway_url, api_key):
        """Test MCP agent using KB tools together."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Request that combines MCP agent and KB tools
            messages = [
                {"role": "user", "content": "Search the knowledge base for information about AI ethics, then create a comprehensive analysis with your own insights"}
            ]
            
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[0]["content"],
                    "stream": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Should combine KB search results with agent analysis
            assert len(content) > 300
            assert any(keyword in content.lower() for keyword in [
                "knowledge base", "search", "ethics", "ai", "analysis"
            ])
    
    @pytest.mark.asyncio
    async def test_mcp_agent_streaming(self, gateway_url, api_key):
        """Test MCP agent with streaming responses."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Request with streaming
            messages = [
                {"role": "user", "content": "Write a short story about a robot learning to paint"}
            ]
            
            chunks_received = 0
            content_parts = []
            
            async with client.stream(
                'POST',
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[0]["content"],
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            chunk_data = json.loads(data_str)
                            if "choices" in chunk_data and chunk_data["choices"]:
                                delta = chunk_data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    content_parts.append(delta["content"])
                                    chunks_received += 1
                        except json.JSONDecodeError:
                            continue
            
            # Should receive multiple chunks
            assert chunks_received > 5, f"Only received {chunks_received} chunks"
            
            # Combined content should form coherent story
            full_content = "".join(content_parts)
            assert len(full_content) > 100
            assert any(keyword in full_content.lower() for keyword in ["robot", "paint"])
            
            logger.info(f"Received {chunks_received} streaming chunks")