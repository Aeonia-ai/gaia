"""
Integration tests for KB tool execution through chat.

Tests the complete flow of KB tool usage:
1. User sends message requiring KB search
2. Chat service classifies and routes to KB tools
3. KB service executes search/read operations
4. Results are formatted and returned to user

Requires all services running (gateway, chat, kb, auth).
"""

import pytest
import httpx
import asyncio
import json
from typing import Dict, Any, List

from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_kb_tool_integration")


@pytest.mark.integration
class TestKBToolIntegration:
    """Test KB tool execution through the chat service."""
    
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
    async def test_kb_search_through_chat(self, gateway_url, api_key):
        """Test that KB search is triggered and executed correctly."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Send message that should trigger KB search
            messages = [
                {"role": "user", "content": "Search the knowledge base for information about consciousness"}
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
            
            # Verify response structure
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]
            
            content = data["choices"][0]["message"]["content"]
            
            # Should contain KB search results or indication of search
            assert any(keyword in content.lower() for keyword in [
                "knowledge base", "kb", "search", "found", "results", "consciousness"
            ])
            
            logger.info(f"KB search response: {content[:200]}...")
    
    @pytest.mark.asyncio
    async def test_kb_file_read_through_chat(self, gateway_url, api_key):
        """Test that KB file reading is triggered correctly."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Request to read a specific file
            messages = [
                {"role": "user", "content": "Load the content from README.md in the knowledge base"}
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
            
            # Should indicate file reading attempt
            assert any(keyword in content.lower() for keyword in [
                "readme", "file", "content", "loaded", "found", "knowledge base"
            ])
    
    @pytest.mark.asyncio
    async def test_kb_list_files_through_chat(self, gateway_url, api_key):
        """Test that KB directory listing works through chat."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Request to list files
            messages = [
                {"role": "user", "content": "List the files available in the knowledge base docs directory"}
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
            
            # Should show file listing
            assert any(keyword in content.lower() for keyword in [
                "files", "directory", "list", "docs", ".md", "folder"
            ])
    
    @pytest.mark.asyncio
    async def test_kb_tool_error_handling(self, gateway_url, api_key):
        """Test error handling when KB operations fail."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Request non-existent file
            messages = [
                {"role": "user", "content": "Read the file /nonexistent/path/file.txt from the knowledge base"}
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
            
            # Should handle error gracefully
            assert any(keyword in content.lower() for keyword in [
                "not found", "doesn't exist", "unable", "error", "cannot"
            ])
    
    @pytest.mark.asyncio
    async def test_kb_synthesis_through_chat(self, gateway_url, api_key):
        """Test KB information synthesis capabilities."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Request synthesis of information
            messages = [
                {"role": "user", "content": "Synthesize information about AI and consciousness from the knowledge base"}
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
            
            # Should attempt synthesis
            assert len(content) > 100  # Non-trivial response
            assert any(keyword in content.lower() for keyword in [
                "ai", "consciousness", "knowledge", "information"
            ])
    
    @pytest.mark.asyncio
    async def test_multiple_kb_tools_in_conversation(self, gateway_url, api_key):
        """Test using multiple KB tools in a single conversation."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Skip conversation creation for now
            conversation_id = None
            
            # First: Search
            messages = [
                {"role": "user", "content": "Search the knowledge base for 'quantum'"}
            ]
            
            response1 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[-1]["content"],
                    "stream": False,
                    "conversation_id": conversation_id
                }
            )
            assert response1.status_code == 200
            
            # Second: List files
            messages.append({"role": "assistant", "content": response1.json()["choices"][0]["message"]["content"]})
            messages.append({"role": "user", "content": "Now list the files in the docs folder"})
            
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
            
            # Third: Read specific file
            messages.append({"role": "assistant", "content": response2.json()["choices"][0]["message"]["content"]})
            messages.append({"role": "user", "content": "Read the first markdown file you find"})
            
            response3 = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[-1]["content"],
                    "stream": False,
                    "conversation_id": conversation_id
                }
            )
            assert response3.status_code == 200
            
            # Verify all responses succeeded
            assert all(r.json()["choices"][0]["message"]["content"] for r in [response1, response2, response3])
    
    @pytest.mark.asyncio
    async def test_kb_tool_performance(self, gateway_url, api_key):
        """Test that KB tool execution meets performance requirements."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Time KB search operation
            import time
            start_time = time.time()
            
            messages = [
                {"role": "user", "content": "Search knowledge base for 'test'"}
            ]
            
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": messages[0]["content"],
                    "stream": False
                }
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            assert response.status_code == 200
            
            # KB operations should complete within reasonable time
            assert response_time < 10.0, f"KB search took {response_time:.2f}s, expected < 10s"
            logger.info(f"KB tool response time: {response_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_kb_tool_concurrent_requests(self, gateway_url, api_key):
        """Test concurrent KB tool requests."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Create multiple concurrent KB requests
            async def make_kb_request(query: str):
                messages = [{"role": "user", "content": f"Search knowledge base for '{query}'"}]
                return await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={
                        "messages": messages,
                        "model": "claude-3-sonnet",
                        "stream": False
                    }
                )
            
            # Send 5 concurrent requests
            queries = ["consciousness", "AI", "quantum", "philosophy", "science"]
            responses = await asyncio.gather(*[make_kb_request(q) for q in queries])
            
            # All should succeed
            assert all(r.status_code == 200 for r in responses)
            assert all(r.json()["choices"][0]["message"]["content"] for r in responses)
            
            logger.info(f"Successfully processed {len(responses)} concurrent KB requests")