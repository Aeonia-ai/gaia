"""Mock fixtures for MCP (Model Context Protocol) components.

Provides reusable mocks for MCPApp, agents, and related components
used across MCP-related unit tests.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import json
from typing import Dict, Any, Optional, List


class MockMCPApp:
    """Mock MCPApp with realistic behavior patterns."""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.agent_counter = 0
        self.call_log = []
        
    async def get_agent(self, agent_key: str, user_id: str = None, persona: str = None):
        """Mock get_agent with agent creation simulation."""
        self.call_log.append(("get_agent", agent_key, user_id, persona))
        
        if agent_key not in self.agents:
            self.agents[agent_key] = MockAgent(
                agent_id=f"agent-{self.agent_counter}",
                user_id=user_id,
                persona=persona
            )
            self.agent_counter += 1
            
        return self.agents[agent_key]
    
    async def create_agent(self, agent_key: str, config: Dict[str, Any] = None):
        """Mock create_agent method."""
        self.call_log.append(("create_agent", agent_key, config))
        
        agent = MockAgent(
            agent_id=f"agent-{self.agent_counter}",
            config=config or {}
        )
        self.agent_counter += 1
        self.agents[agent_key] = agent
        return agent
    
    async def cleanup_agent(self, agent_key: str = None, agent=None):
        """Mock cleanup_agent method."""
        if agent_key and agent_key in self.agents:
            self.call_log.append(("cleanup_agent", agent_key))
            del self.agents[agent_key]
        elif agent:
            # Find and remove by agent instance
            for key, cached_agent in list(self.agents.items()):
                if cached_agent is agent:
                    self.call_log.append(("cleanup_agent", key))
                    del self.agents[key]
                    break
    
    async def get_agent_stats(self, agent_key: str):
        """Mock get_agent_stats method."""
        if agent_key in self.agents:
            agent = self.agents[agent_key]
            return {
                "agent_id": agent.id,
                "memory_usage": agent.get_memory_usage(),
                "active": True,
                "created_at": agent.created_at.isoformat(),
                "request_count": agent.request_count
            }
        return {"active": False}
    
    def reset(self):
        """Reset mock state for clean tests."""
        self.agents.clear()
        self.agent_counter = 0
        self.call_log.clear()


class MockAgent:
    """Mock agent with context manager support and realistic behavior."""
    
    def __init__(self, agent_id: str, user_id: str = None, persona: str = None, config: Dict[str, Any] = None):
        self.id = agent_id
        self.user_id = user_id
        self.persona = persona or "default"
        self.config = config or {}
        self.created_at = datetime.utcnow()
        self.last_used = datetime.utcnow()
        self.request_count = 0
        self.chat_history = []
        self.memory_usage_mb = 2  # Default 2MB
        self.is_healthy = True
        self.cleanup_called = False
        
    async def __aenter__(self):
        """Context manager entry."""
        self.last_used = datetime.utcnow()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup_called = True
        return False  # Don't suppress exceptions
    
    async def process_message(self, message: str, context: Dict[str, Any] = None) -> str:
        """Mock message processing."""
        self.request_count += 1
        self.last_used = datetime.utcnow()
        
        # Add to history
        self.chat_history.append({
            "role": "user",
            "content": message,
            "timestamp": self.last_used.isoformat()
        })
        
        # Generate mock response
        response = f"Mock response to: {message}"
        if context:
            response += f" (with context: {len(context)} items)"
            
        self.chat_history.append({
            "role": "assistant", 
            "content": response,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return response
    
    def add_to_history(self, message: Dict[str, Any]):
        """Add message to chat history."""
        self.chat_history.append({
            **message,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def clear_history(self):
        """Clear chat history."""
        self.chat_history.clear()
    
    def get_memory_usage(self) -> int:
        """Get memory usage in bytes."""
        # Simulate memory usage based on history length
        base_usage = self.memory_usage_mb * 1024 * 1024
        history_usage = len(self.chat_history) * 1024  # 1KB per message
        return base_usage + history_usage
    
    async def health_check(self) -> bool:
        """Mock health check."""
        return self.is_healthy
    
    def set_unhealthy(self):
        """Mark agent as unhealthy for testing."""
        self.is_healthy = False
        
    def set_memory_usage(self, mb: int):
        """Set memory usage for testing."""
        self.memory_usage_mb = mb


class MockAnthropicAugmentedLLM:
    """Mock for AnthropicAugmentedLLM used in agents."""
    
    def __init__(self, model: str = "claude-3-sonnet", api_key: str = None):
        self.model = model
        self.api_key = api_key
        self.call_count = 0
        self.responses = []
        self.default_response = "Mock LLM response"
        
    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Mock response generation."""
        self.call_count += 1
        
        if self.responses:
            return self.responses.pop(0)
        return self.default_response
    
    def set_responses(self, responses: List[str]):
        """Set predetermined responses for testing."""
        self.responses = responses.copy()
    
    def set_default_response(self, response: str):
        """Set default response for testing."""
        self.default_response = response


@pytest.fixture
def mock_mcp_app():
    """Pytest fixture for MockMCPApp."""
    app = MockMCPApp()
    yield app
    app.reset()


@pytest.fixture
def mock_agent():
    """Pytest fixture for MockAgent."""
    return MockAgent(
        agent_id="test-agent-123",
        user_id="test-user-456",
        persona="assistant"
    )


@pytest.fixture
def mock_agent_with_history(mock_agent):
    """Pytest fixture for MockAgent with pre-populated history."""
    mock_agent.add_to_history({
        "role": "user",
        "content": "Hello, how are you?"
    })
    mock_agent.add_to_history({
        "role": "assistant",
        "content": "I'm doing well, thank you for asking!"
    })
    return mock_agent


@pytest.fixture
def mock_anthropic_llm():
    """Pytest fixture for MockAnthropicAugmentedLLM."""
    return MockAnthropicAugmentedLLM()


@pytest.fixture
def mock_llm_with_responses():
    """Pytest fixture for LLM with predetermined responses."""
    llm = MockAnthropicAugmentedLLM()
    llm.set_responses([
        "First response",
        "Second response", 
        "Third response"
    ])
    return llm


class MockHttpClient:
    """Mock HTTP client for KB service interactions."""
    
    def __init__(self):
        self.requests = []
        self.responses = []
        self.default_response = {
            "status_code": 200,
            "json_data": {"results": [], "total_results": 0},
            "headers": {"Content-Type": "application/json"}
        }
        
    async def post(self, url: str, json: Dict[str, Any] = None, headers: Dict[str, str] = None, **kwargs):
        """Mock POST request."""
        request = {
            "method": "POST",
            "url": url,
            "json": json,
            "headers": headers,
            "kwargs": kwargs
        }
        self.requests.append(request)
        
        if self.responses:
            response_data = self.responses.pop(0)
        else:
            response_data = self.default_response
            
        return MockHttpResponse(**response_data)
    
    async def get(self, url: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None, **kwargs):
        """Mock GET request."""
        request = {
            "method": "GET",
            "url": url,
            "params": params,
            "headers": headers,
            "kwargs": kwargs
        }
        self.requests.append(request)
        
        if self.responses:
            response_data = self.responses.pop(0)
        else:
            response_data = self.default_response
            
        return MockHttpResponse(**response_data)
    
    def set_responses(self, responses: List[Dict[str, Any]]):
        """Set predetermined responses."""
        self.responses = responses.copy()
        
    def get_last_request(self) -> Optional[Dict[str, Any]]:
        """Get the last request made."""
        return self.requests[-1] if self.requests else None
    
    def reset(self):
        """Reset mock state."""
        self.requests.clear()
        self.responses.clear()


class MockHttpResponse:
    """Mock HTTP response object."""
    
    def __init__(self, status_code: int = 200, json_data: Dict[str, Any] = None, 
                 headers: Dict[str, str] = None, text: str = None, elapsed_seconds: float = 0.1):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {}
        self.text = text or json.dumps(self._json_data)
        self._elapsed_seconds = elapsed_seconds
        
    def json(self):
        """Return JSON data."""
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data
    
    @property
    def elapsed(self):
        """Mock elapsed time."""
        mock_elapsed = Mock()
        mock_elapsed.total_seconds.return_value = self._elapsed_seconds
        return mock_elapsed


@pytest.fixture
def mock_http_client():
    """Pytest fixture for MockHttpClient."""
    client = MockHttpClient()
    yield client
    client.reset()


@pytest.fixture  
def mock_kb_search_response():
    """Pytest fixture for mock KB search response."""
    return {
        "status_code": 200,
        "json_data": {
            "results": [
                {
                    "content": "This is test content about AI",
                    "metadata": {
                        "file_path": "docs/ai-basics.md",
                        "score": 0.92,
                        "chunk_index": 0,
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                },
                {
                    "content": "Advanced AI concepts and applications",
                    "metadata": {
                        "file_path": "docs/ai-advanced.md",
                        "score": 0.87, 
                        "chunk_index": 1,
                        "created_at": "2024-01-14T15:45:00Z"
                    }
                }
            ],
            "total_results": 2,
            "query": "AI concepts",
            "processing_time": 0.045
        }
    }


@pytest.fixture
def mock_kb_error_response():
    """Pytest fixture for mock KB error response."""
    return {
        "status_code": 500,
        "json_data": {
            "error": "Internal Server Error",
            "message": "KB service temporarily unavailable",
            "error_code": "KB_SERVICE_ERROR"
        }
    }


@pytest.fixture
def mock_agent_cache_data():
    """Pytest fixture for mock agent cache data."""
    now = datetime.utcnow()
    return {
        "user-1:assistant": {
            "agent": MockAgent("agent-1", "user-1", "assistant"),
            "created_at": now - timedelta(minutes=10),
            "last_used": now - timedelta(minutes=2),
            "use_count": 3
        },
        "user-2:researcher": {
            "agent": MockAgent("agent-2", "user-2", "researcher"),
            "created_at": now - timedelta(minutes=5),
            "last_used": now - timedelta(minutes=1), 
            "use_count": 1
        },
        "user-3:default": {
            "agent": MockAgent("agent-3", "user-3", "default"),
            "created_at": now - timedelta(minutes=15),
            "last_used": now - timedelta(minutes=10),
            "use_count": 7
        }
    }


def create_mock_mcp_request(user_id: str = "test-user", message: str = "test message", 
                           persona: str = "assistant", kb_query: str = None) -> Dict[str, Any]:
    """Helper function to create mock MCP request data."""
    request = {
        "user_id": user_id,
        "message": message,
        "persona": persona,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": f"req-{datetime.utcnow().timestamp()}"
    }
    
    if kb_query:
        request["kb_query"] = kb_query
        
    return request


def create_mock_mcp_response(content: str = "Mock response", agent_id: str = "test-agent",
                           processing_time: float = 0.1, kb_results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Helper function to create mock MCP response data."""
    response = {
        "content": content,
        "agent_id": agent_id,
        "processing_time": processing_time,
        "timestamp": datetime.utcnow().isoformat(),
        "response_id": f"resp-{datetime.utcnow().timestamp()}"
    }
    
    if kb_results:
        response["kb_results"] = kb_results
        response["kb_result_count"] = len(kb_results)
        
    return response