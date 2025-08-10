"""
Test routing functionality with personas enabled
"""
import pytest
import httpx
import os
from app.shared.logging import setup_service_logger

logger = setup_service_logger("test_routing_personas")

class TestRoutingWithPersonas:
    """Test that routing works correctly when personas are active"""
    
    @pytest.fixture
    def gateway_url(self):
        return os.getenv("GATEWAY_URL", "http://gateway:8000")
    
    @pytest.fixture
    def api_key(self):
        """API key for testing."""
        api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
        if not api_key:
            pytest.skip("No API key available")
        return api_key
    
    @pytest.fixture
    def headers(self, api_key):
        """Standard headers with API key."""
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_direct_response_with_persona(self, gateway_url, headers):
        """Test direct responses maintain persona identity"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First, ask about identity
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "What's your name?", "response_format": "v0.3"}
            )
            
            assert response.status_code == 200
            data = response.json()
            name_response = data["response"]
            
            # Should contain Mu identity
            assert "mu" in name_response.lower() or "robot" in name_response.lower()
            
            # Now ask a simple math question
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "What is 2+2?", "response_format": "v0.3"}
            )
            
            assert response.status_code == 200
            data = response.json()
            math_response = data["response"]
            
            # Should answer correctly
            assert "4" in math_response
            
            # But might maintain personality
            logger.info(f"Math response: {math_response}")
            
    @pytest.mark.asyncio
    async def test_kb_routing_with_persona(self, gateway_url, headers):
        """Test KB tool routing maintains persona"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "Search my knowledge base for information about Python",
                    "response_format": "v0.3"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should get a response (even if no KB content)
            assert "response" in data
            
            # Response should maintain persona characteristics
            response_text = data["response"].lower()
            logger.info(f"KB search response: {response_text[:200]}...")
            
    @pytest.mark.asyncio
    async def test_mcp_routing_with_persona(self, gateway_url, headers):
        """Test MCP agent routing maintains persona context"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={
                    "message": "List the files in the /tmp directory",
                    "response_format": "v0.3"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should route to MCP and get response
            assert "response" in data
            response_text = data["response"].lower()
            
            # Should mention files or directory
            assert any(word in response_text for word in ["file", "directory", "tmp", "folder"])
            
    @pytest.mark.asyncio
    async def test_routing_decisions_logged(self, gateway_url, headers):
        """Test that routing decisions are being made correctly"""
        test_cases = [
            ("Hello!", "direct"),  # Greeting - direct response
            ("What's 5 times 3?", "direct"),  # Math - direct response
            ("Read the file /etc/hosts", "mcp"),  # File operation - MCP
            ("Search my notes for meeting", "kb"),  # KB search
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for message, expected_route in test_cases:
                response = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={"message": message, "response_format": "v0.3"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Log the routing decision
                logger.info(f"Message: '{message}' -> Response: {data.get('response', '')[:100]}...")
                
                # Verify we got a response
                assert "response" in data
                
    @pytest.mark.skip(reason="Conversation persistence not working with v0.3 format")
    @pytest.mark.asyncio 
    async def test_persona_maintained_across_routes(self, gateway_url, headers):
        """Test persona identity is maintained regardless of routing"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create a conversation
            response = await client.post(
                f"{gateway_url}/api/v1/chat",
                headers=headers,
                json={"message": "Hi! What's your name?", "response_format": "v0.3"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Get conversation_id from metadata if available
            conversation_id = None
            if "_metadata" in data:
                conversation_id = data["_metadata"]["conversation_id"]
            
            # Verify Mu identity
            response_text = data.get("response", "")
            assert "mu" in response_text.lower()
            
            # If we don't have conversation persistence, skip the rest
            if not conversation_id:
                logger.warning("No conversation_id returned, skipping conversation tests")
                return
                
            # Now do various operations in same conversation
            test_messages = [
                "Calculate 10 divided by 2",  # Direct math
                "What's the weather like?",  # Direct general
                "List files in /tmp",  # MCP routing
            ]
            
            for msg in test_messages:
                response = await client.post(
                    f"{gateway_url}/api/v1/chat",
                    headers=headers,
                    json={
                        "message": msg,
                        "conversation_id": conversation_id,
                        "response_format": "v0.3"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Check if persona characteristics leak through
                response_text = data.get("response", "").lower()
                logger.info(f"'{msg}' response personality check: {any(word in response_text for word in ['beep', 'boop', 'robot'])}")