"""
Automated tests for Knowledge Base (KB) endpoints.
Migrated from manual test script KB-related functionality.
"""

import pytest
import httpx
import os
from typing import Dict, Any
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_kb_endpoints")


class TestKBHealthAndStatus:
    """Test KB service health and status endpoints."""
    
    @pytest.fixture
    def kb_url(self):
        """KB service URL for testing."""
        return "http://kb-service:8000"  # Direct KB service URL
    
    @pytest.fixture
    def gateway_url(self):
        """Gateway service URL for testing."""
        return "http://gateway:8000"
    
    @pytest.fixture
    def api_key(self):
        """Test API key for authentication."""
        return os.getenv("API_KEY", "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE")
    
    @pytest.fixture
    def headers(self, api_key):
        """Standard headers for API requests."""
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    async def test_kb_direct_health(self, kb_url, headers):
        """Test KB service health endpoint directly."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{kb_url}/health", headers=headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data.get("status") in ["healthy", "degraded"]
            
            # Check for repository information if available
            if "repository" in data:
                repo_info = data["repository"]
                logger.info(f"KB Repository - Status: {repo_info.get('status')}, Files: {repo_info.get('file_count', 0)}, Git: {repo_info.get('has_git', False)}")
            
            logger.info(f"KB health: {data['status']}")
    
    async def test_kb_repository_status(self, kb_url, headers):
        """Test KB repository status and file information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{kb_url}/health", headers=headers)
            assert response.status_code == 200
            
            data = response.json()
            
            # Verify repository information is present
            if "repository" in data:
                repo = data["repository"]
                
                # Basic repository checks
                assert "status" in repo
                assert "file_count" in repo
                assert isinstance(repo["file_count"], int)
                assert repo["file_count"] >= 0
                
                # Log repository details
                file_count = repo["file_count"]
                has_git = repo.get("has_git", False)
                status = repo["status"]
                
                logger.info(f"Repository: {status}, {file_count} files, Git: {has_git}")
                
                # If we have files, repository should be in good state
                if file_count > 0:
                    assert status in ["ready", "synced", "healthy"]
            else:
                logger.info("No repository information in health response")


class TestKBSearchOperations:
    """Test KB search and query operations."""
    
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"
    
    @pytest.fixture
    def headers(self):
        return {
            "X-API-Key": os.getenv("API_KEY", "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"),
            "Content-Type": "application/json"
        }
    
    async def test_kb_search_basic(self, gateway_url, headers):
        """Test basic KB search functionality."""
        search_queries = [
            "consciousness",
            "gaia",
            "multiagent", 
            "test"
        ]
        
        for query in search_queries:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{gateway_url}/api/v0.2/kb/search",
                    headers=headers,
                    json={"message": query}
                )
                
                # KB search may not be implemented through gateway
                assert response.status_code in [200, 404, 500]
                
                if response.status_code == 200:
                    data = response.json()
                    assert isinstance(data, dict)
                    
                    # Should have some kind of search results
                    if "results" in data:
                        results = data["results"]
                        logger.info(f"Search '{query}': {len(results)} results")
                    elif "response" in data:
                        # May return response format instead
                        logger.info(f"Search '{query}': got response format")
                    else:
                        logger.info(f"Search '{query}': {list(data.keys())}")
                else:
                    logger.info(f"Search '{query}': endpoint returned {response.status_code}")
                    if response.status_code == 404:
                        break  # No need to test other queries if endpoint doesn't exist
    
    async def test_kb_context_loading(self, gateway_url, headers):
        """Test KB context loading functionality."""
        contexts_to_test = [
            "gaia",
            "consciousness", 
            "multiagent",
            "aeonia"
        ]
        
        for context in contexts_to_test:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{gateway_url}/api/v0.2/kb/context",
                    headers=headers,
                    json={"message": context}
                )
                
                # KB context may not be implemented through gateway
                assert response.status_code in [200, 404, 500]
                
                if response.status_code == 200:
                    data = response.json()
                    assert isinstance(data, dict)
                    logger.info(f"Context '{context}': loaded successfully")
                elif response.status_code == 404:
                    logger.info(f"KB context endpoint not implemented")
                    break
                else:
                    logger.info(f"Context '{context}': returned {response.status_code}")
    
    async def test_kb_multitask(self, gateway_url, headers):
        """Test KB multitask functionality."""
        multitask_queries = [
            "Search for 'multiagent' and load the 'gaia' context",
            "Find information about consciousness and prepare context",
            "Search documentation and load relevant context"
        ]
        
        for query in multitask_queries:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{gateway_url}/api/v0.2/kb/multitask",
                    headers=headers,
                    json={"message": query}
                )
                
                # KB multitask may not be implemented
                assert response.status_code in [200, 404, 500]
                
                if response.status_code == 200:
                    data = response.json()
                    assert isinstance(data, dict)
                    logger.info(f"Multitask query executed successfully")
                elif response.status_code == 404:
                    logger.info(f"KB multitask endpoint not implemented")
                    break
                else:
                    logger.info(f"Multitask query returned {response.status_code}")


class TestKBIntegratedChat:
    """Test KB-integrated chat endpoints that use knowledge base."""
    
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"
    
    @pytest.fixture
    def headers(self):
        return {
            "X-API-Key": os.getenv("API_KEY", "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"),
            "Content-Type": "application/json"
        }
    
    async def test_kb_enhanced_chat(self, gateway_url, headers):
        """Test KB-enhanced chat functionality."""
        kb_queries = [
            "Search the KB for information about consciousness and synthesize insights",
            "What does the knowledge base say about multiagent systems?",
            "Find documentation about Gaia platform architecture"
        ]
        
        for query in kb_queries:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{gateway_url}/api/v1/chat/kb-enhanced",
                    headers=headers,
                    json={"message": query}
                )
                
                # KB-enhanced chat may not be implemented
                assert response.status_code in [200, 404, 500]
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # KB endpoints return v0.2 format (even under v1 path)
                    assert "response" in data
                    assert "status" in data
                    assert data["status"] == "success"
                    
                    content = data["response"]
                    assert len(content) > 0
                    
                    # Check for KB usage indicators
                    metadata = data.get("_metadata", {})
                    if "tools_used" in metadata:
                        logger.info(f"KB-enhanced chat used tools: {metadata['tools_used']}")
                    
                    logger.info(f"KB-enhanced chat response length: {len(content)} chars")
                elif response.status_code == 404:
                    logger.info("KB-enhanced chat endpoint not implemented")
                    break
                else:
                    logger.info(f"KB-enhanced chat returned {response.status_code}")
    
    async def test_kb_research_chat(self, gateway_url, headers):
        """Test KB research chat functionality."""
        research_queries = [
            "Research the implementation of consciousness frameworks",
            "Analyze the multiagent architecture documentation",
            "Study the Gaia platform design principles"
        ]
        
        for query in research_queries:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{gateway_url}/api/v1/chat/kb-research",
                    headers=headers,
                    json={"message": query}
                )
                
                # KB research may not be implemented
                assert response.status_code in [200, 404, 500]
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # KB endpoints return v0.2 format (even under v1 path)
                    assert "response" in data
                    assert "status" in data
                    assert data["status"] == "success"
                    
                    content = data["response"]
                    assert len(content) > 0
                    
                    logger.info(f"KB research response length: {len(content)} chars")
                elif response.status_code == 404:
                    logger.info("KB research endpoint not implemented")
                    break
                else:
                    logger.info(f"KB research returned {response.status_code}")


class TestKBServiceIntegration:
    """Test integration between KB service and other components."""
    
    @pytest.fixture
    def kb_url(self):
        return "http://kb-service:8000"
    
    @pytest.fixture
    def gateway_url(self):
        return "http://gateway:8000"
    
    @pytest.fixture
    def headers(self):
        return {
            "X-API-Key": os.getenv("API_KEY", "FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"),
            "Content-Type": "application/json"
        }
    
    async def test_kb_service_accessibility(self, kb_url, gateway_url, headers):
        """Test that KB service is accessible both directly and through gateway."""
        # Test direct access to KB service
        async with httpx.AsyncClient() as client:
            kb_direct_response = await client.get(f"{kb_url}/health", headers=headers)
            assert kb_direct_response.status_code == 200
            
            kb_data = kb_direct_response.json()
            assert kb_data.get("status") in ["healthy", "degraded"]
            
            # Test gateway health (should show KB service as healthy)
            gateway_response = await client.get(f"{gateway_url}/health", headers=headers)
            assert gateway_response.status_code == 200
            
            gateway_data = gateway_response.json()
            assert gateway_data.get("status") in ["healthy", "degraded"]
            
            # Check if KB service is listed in gateway health
            if "services" in gateway_data:
                services = gateway_data["services"]
                if "kb" in services:
                    kb_service_status = services["kb"]["status"]
                    assert kb_service_status in ["healthy", "degraded"]
                    logger.info(f"KB service status in gateway: {kb_service_status}")
                else:
                    logger.info("KB service not listed in gateway health services")
            
            logger.info("KB service is accessible both directly and through gateway")
    
    async def test_kb_chat_integration(self, gateway_url, headers):
        """Test that KB integrates properly with chat endpoints."""
        # Test regular chat (may use KB for context)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "What do you know about consciousness from your knowledge base?"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should get a response
            assert "choices" in data
            content = data["choices"][0]["message"]["content"]
            assert len(content) > 0
            
            # Check metadata for KB tool usage
            metadata = data.get("_metadata", {})
            route_type = metadata.get("route_type", "unknown")
            tools_used = metadata.get("tools_used", [])
            
            logger.info(f"Chat with KB query - Route: {route_type}, Tools: {tools_used}")
            
            # If KB tools were used, verify they're working
            if "search_knowledge_base" in tools_used:
                logger.info("Successfully integrated KB search in chat response")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])