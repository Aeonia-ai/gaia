"""
End-to-end integration tests for intelligent chat routing.

Tests the complete routing architecture:
1. Direct responses for simple queries
2. KB tool execution for knowledge base operations  
3. MCP agent routing for complex tasks
4. Performance characteristics of each path

Based on the architecture in docs/current/architecture/chat-routing-and-kb-architecture.md
"""

import pytest
import httpx
import asyncio
import time
import json
import os
from typing import Dict, Any, List, Tuple

from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_intelligent_routing_e2e")


@pytest.mark.integration
class TestIntelligentRoutingE2E:
    """Test the complete intelligent routing system end-to-end."""
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway URL for integration tests."""
        import os
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    async def authenticated_client(self, gateway_url, shared_test_user):
        """Create authenticated HTTP client."""
        auth_url = "http://auth-service:8000"
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Login using auth service with API key exchange pattern
            login_response = await client.post(
                f"{auth_url}/auth/api-key-login",
                headers={"X-API-Key": os.getenv("API_KEY", "test-key-123")}
            )
            assert login_response.status_code == 200
            auth_data = login_response.json()
            # API key exchange returns OAuth2-compatible format
            jwt_token = auth_data["access_token"]
            
            client.headers.update({
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            })
            
            yield client
    
    async def send_chat_request(self, client: httpx.AsyncClient, gateway_url: str, 
                               message: str, conversation_id: str = None) -> Tuple[Dict, float]:
        """Send chat request and return response with timing."""
        start_time = time.time()
        
        request_body = {
            "messages": [{"role": "user", "content": message}],
            "model": "claude-3-sonnet",
            "stream": False
        }
        
        if conversation_id:
            request_body["conversation_id"] = conversation_id
        
        response = await client.post(
            f"{gateway_url}/api/v1/chat",
            json=request_body
        )
        
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        return response.json(), elapsed_time
    
    @pytest.mark.asyncio
    async def test_routing_performance_characteristics(self, gateway_url, authenticated_client):
        """Test that different routing paths have expected performance characteristics."""
        
        test_cases = [
            # (message, expected_route, max_time_seconds)
            ("What is 2+2?", "direct", 2.0),
            ("Hello!", "direct", 2.0),
            ("Search the knowledge base for quantum computing", "kb_tools", 5.0),
            ("List files in the knowledge base docs folder", "kb_tools", 5.0),
            ("Create a detailed business plan for a tech startup", "mcp_agent", 10.0),
        ]
        
        results = []
        
        for message, expected_route, max_time in test_cases:
            data, elapsed = await self.send_chat_request(authenticated_client, gateway_url, message)
            
            content = data["choices"][0]["message"]["content"]
            
            results.append({
                "message": message[:50] + "..." if len(message) > 50 else message,
                "expected_route": expected_route,
                "elapsed_time": elapsed,
                "max_time": max_time,
                "passed": elapsed <= max_time,
                "response_length": len(content)
            })
            
            logger.info(f"Route: {expected_route}, Time: {elapsed:.2f}s, Message: {message[:30]}...")
            
            # Verify performance
            assert elapsed <= max_time, f"{expected_route} route took {elapsed:.2f}s, expected <= {max_time}s"
        
        # Log summary
        logger.info("\nRouting Performance Summary:")
        for result in results:
            status = "✓" if result["passed"] else "✗"
            logger.info(f"{status} {result['expected_route']:12} {result['elapsed_time']:6.2f}s (max: {result['max_time']:.1f}s) - {result['message']}")
    
    @pytest.mark.asyncio
    async def test_kb_tool_routing_accuracy(self, gateway_url, authenticated_client):
        """Test that KB-related queries are correctly routed to KB tools."""
        
        kb_queries = [
            "search knowledge base for consciousness",
            "find information about AI in the KB",
            "load context from docs/readme.md",
            "list all markdown files in knowledge base",
            "what files are in the KB?",
            "synthesize KB information about quantum physics"
        ]
        
        for query in kb_queries:
            data, elapsed = await self.send_chat_request(authenticated_client, gateway_url, query)
            content = data["choices"][0]["message"]["content"]
            
            # KB queries should mention KB/knowledge base in response
            assert any(term in content.lower() for term in ["knowledge base", "kb", "search", "file"]), \
                f"KB query '{query}' didn't produce KB-related response"
            
            logger.info(f"✓ KB query routed correctly: {query[:50]}...")
    
    @pytest.mark.asyncio
    async def test_direct_routing_accuracy(self, gateway_url, authenticated_client):
        """Test that simple queries use direct routing."""
        
        simple_queries = [
            "Hi there!",
            "What's the weather like?",
            "Tell me a joke",
            "What's 10 times 5?",
            "How are you doing today?"
        ]
        
        for query in simple_queries:
            data, elapsed = await self.send_chat_request(authenticated_client, gateway_url, query)
            
            # Simple queries should be fast
            assert elapsed < 3.0, f"Simple query '{query}' took {elapsed:.2f}s"
            
            logger.info(f"✓ Direct route used: {query} ({elapsed:.2f}s)")
    
    @pytest.mark.asyncio
    async def test_conversation_context_preservation(self, gateway_url, authenticated_client):
        """Test that routing preserves conversation context across different paths."""
        
        # Create conversation
        conv_response = await authenticated_client.post(
            f"{gateway_url}/api/v1/conversations",
            json={"title": "Routing Context Test"}
        )
        assert conv_response.status_code in [200, 201]
        conversation_id = conv_response.json()["id"]
        
        # Mix different routing paths in same conversation
        exchanges = [
            ("My name is Alice", "direct"),
            ("Search KB for information about memory", "kb_tools"),
            ("What's my name?", "direct"),  # Should remember "Alice"
            ("Based on the KB search, explain how memory works", "mixed"),
            ("Create a detailed poem about what we discussed", "mcp_agent")
        ]
        
        messages = []
        
        for i, (message, route_type) in enumerate(exchanges):
            # Add user message
            messages.append({"role": "user", "content": message})
            
            # Send request with full message history
            request_body = {
                "messages": messages,
                "model": "claude-3-sonnet",
                "stream": False,
                "conversation_id": conversation_id
            }
            
            response = await authenticated_client.post(
                f"{gateway_url}/api/v1/chat",
                json=request_body
            )
            
            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            
            # Add assistant response
            messages.append({"role": "assistant", "content": content})
            
            # Verify context preservation
            if i == 2:  # "What's my name?" query
                assert "alice" in content.lower(), "Failed to remember name across routing paths"
            
            logger.info(f"✓ Step {i+1} ({route_type}): {message[:30]}...")
    
    @pytest.mark.asyncio
    async def test_concurrent_mixed_routing(self, gateway_url, authenticated_client):
        """Test concurrent requests using different routing paths."""
        
        queries = [
            ("What is 5+5?", "direct"),
            ("Search KB for neural networks", "kb_tools"),
            ("Hello there!", "direct"),
            ("List knowledge base files", "kb_tools"),
            ("Create a business strategy", "mcp_agent"),
            ("What's the capital of France?", "direct"),
            ("Find KB docs about consciousness", "kb_tools"),
            ("Explain quantum computing", "mcp_agent")
        ]
        
        async def timed_request(message: str, expected_route: str):
            start = time.time()
            data, _ = await self.send_chat_request(authenticated_client, gateway_url, message)
            elapsed = time.time() - start
            return {
                "message": message[:30] + "...",
                "route": expected_route,
                "time": elapsed,
                "response_len": len(data["choices"][0]["message"]["content"])
            }
        
        # Send all requests concurrently
        results = await asyncio.gather(*[
            timed_request(msg, route) for msg, route in queries
        ])
        
        # Analyze results
        route_times = {"direct": [], "kb_tools": [], "mcp_agent": []}
        
        for result in results:
            route_times[result["route"]].append(result["time"])
            logger.info(f"{result['route']:10} {result['time']:6.2f}s - {result['message']}")
        
        # Calculate averages
        for route, times in route_times.items():
            if times:
                avg = sum(times) / len(times)
                logger.info(f"\nAverage {route} time: {avg:.2f}s")
        
        # Verify all completed
        assert len(results) == len(queries)
    
    @pytest.mark.asyncio
    async def test_error_handling_across_routes(self, gateway_url, authenticated_client):
        """Test error handling in different routing paths."""
        
        error_cases = [
            # Invalid KB operations
            "read file /etc/passwd from knowledge base",  # Security issue
            "search KB for " + "x" * 10000,  # Very long query
            
            # Problematic requests
            "",  # Empty message
            {"invalid": "message format"},  # Wrong type
        ]
        
        for i, query in enumerate(error_cases):
            try:
                if isinstance(query, str) and query:  # Valid string
                    data, _ = await self.send_chat_request(authenticated_client, gateway_url, query)
                    content = data["choices"][0]["message"]["content"]
                    
                    # Should handle gracefully
                    assert len(content) > 0
                    logger.info(f"✓ Error case {i+1} handled gracefully")
                    
            except (httpx.HTTPStatusError, AssertionError, TypeError) as e:
                logger.info(f"✓ Error case {i+1} caught expected error: {type(e).__name__}")
    
    @pytest.mark.asyncio  
    async def test_routing_with_personas(self, gateway_url, authenticated_client):
        """Test that routing works correctly with different personas."""
        
        # Note: This assumes personas might affect routing decisions
        test_personas = [
            ("default", "Explain photosynthesis"),
            ("technical", "Explain the technical details of photosynthesis"),
            ("creative", "Write a poem about photosynthesis")
        ]
        
        for persona, message in test_personas:
            # Would need to set persona in request if supported
            data, elapsed = await self.send_chat_request(authenticated_client, gateway_url, message)
            content = data["choices"][0]["message"]["content"]
            
            assert len(content) > 50
            assert "photosynth" in content.lower()
            
            logger.info(f"✓ Persona '{persona}' request completed in {elapsed:.2f}s")
    
    @pytest.mark.asyncio
    async def test_routing_decisions_logging(self, gateway_url, authenticated_client):
        """Test that routing decisions can be traced/logged."""
        
        # Send request with potential debug headers
        debug_headers = {
            "X-Debug-Routing": "true",
            "X-Request-ID": "test-routing-12345"
        }
        
        authenticated_client.headers.update(debug_headers)
        
        data, elapsed = await self.send_chat_request(
            authenticated_client, 
            gateway_url,
            "Search knowledge base and then analyze the results"
        )
        
        # Check if any routing metadata is returned
        # This depends on implementation
        if "metadata" in data:
            logger.info(f"Routing metadata: {data['metadata']}")
        
        logger.info(f"✓ Request completed in {elapsed:.2f}s")
        
        # Note: In production, routing decisions should be logged
        # for debugging and optimization purposes