"""
Integration tests for v0.3 automatic persona integration.
Tests how v0.3 clean interface automatically integrates personas.
"""
import pytest
import httpx
from tests.fixtures.test_auth import JWTTestAuth
from tests.fixtures.shared_test_user import shared_test_user

BASE_URL = "http://chat-service:8000"
GATEWAY_URL = "http://gateway:8000"


class TestV03PersonasIntegration:
    """Test v0.3 automatic persona integration through clean interface"""
    
    @pytest.fixture
    async def auth_headers(self, shared_test_user):
        """Get auth headers using real JWT from shared test user"""
        # Login through gateway to get real JWT
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GATEWAY_URL}/api/v1/auth/login",
                json={
                    "email": shared_test_user["email"],
                    "password": shared_test_user["password"]
                }
            )
            assert response.status_code == 200
            jwt_token = response.json()["session"]["access_token"]
            return {"Authorization": f"Bearer {jwt_token}"}
    
    @pytest.mark.asyncio
    async def test_v03_automatic_persona_integration(self, shared_test_user):
        """Test that v0.3 automatically integrates user's persona"""
        # Use JWT auth directly for chat service testing
        jwt_auth = JWTTestAuth()
        headers = jwt_auth.create_auth_headers(
            user_id=shared_test_user["user_id"],
            email=shared_test_user["email"]
        )
        
        async with httpx.AsyncClient() as client:
            # Send a chat message through v0.3 unified endpoint
            response = await client.post(
                f"{BASE_URL}/chat/unified",
                headers=headers,
                json={
                    "message": "Hello! Please introduce yourself and tell me who you are.",
                    "response_format": "v0.3"
                }
            )
            assert response.status_code == 200
            response_data = response.json()
            
            # v0.3 clean interface - only these fields
            assert "response" in response_data
            assert "conversation_id" in response_data
            
            # Should NOT expose internal details
            assert "provider" not in response_data
            assert "model" not in response_data
            assert "persona_id" not in response_data
            
            response_text = response_data["response"]
            
            # Check for Mu persona characteristics
            # v0.3 automatically integrates personas via unified_chat
            response_lower = response_text.lower()
            
            has_mu_characteristics = any([
                "mu" in response_lower,
                "robot" in response_lower,
                "beep" in response_lower,
                "boop" in response_lower,
                "cheerful" in response_lower,
                "companion" in response_lower
            ])
            
            assert has_mu_characteristics, f"Response doesn't show Mu persona characteristics: {response_text}"
    
    @pytest.mark.asyncio
    async def test_v03_persona_through_gateway(self, auth_headers):
        """Test v0.3 persona integration through gateway"""
        headers = auth_headers
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send through gateway v0.3 endpoint
            response = await client.post(
                f"{GATEWAY_URL}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "What kind of entity are you? Describe yourself.",
                    "stream": False
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            # Clean v0.3 interface
            assert "response" in data
            assert "conversation_id" in data
            assert len(data) == 2  # Only these two fields
            
            # Check persona influence in response
            response_lower = data["response"].lower()
            
            # Mu persona should influence the response
            # but v0.3 doesn't expose which persona is active
            persona_hints = [
                "robot" in response_lower,
                "companion" in response_lower,
                "helpful" in response_lower,
                "assist" in response_lower
            ]
            
            assert any(persona_hints), "Response should show persona influence"
    
    @pytest.mark.asyncio
    async def test_v03_conversation_maintains_persona_context(self, auth_headers):
        """Test that v0.3 maintains persona context across conversation"""
        headers = auth_headers
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{GATEWAY_URL}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Hello! What's your name?",
                    "stream": False
                }
            )
            assert response1.status_code == 200
            data1 = response1.json()
            conversation_id = data1["conversation_id"]
            
            # Second message in same conversation
            response2 = await client.post(
                f"{GATEWAY_URL}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Are you a robot or a human?",
                    "conversation_id": conversation_id,
                    "stream": False
                }
            )
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Persona should be consistent across conversation
            response_text = data2["response"].lower()
            
            # Should maintain robot persona context
            robot_indicators = [
                "robot" in response_text,
                "ai" in response_text,
                "artificial" in response_text,
                "digital" in response_text,
                "not human" in response_text
            ]
            
            assert any(robot_indicators), "Should maintain consistent persona across conversation"
    
    @pytest.mark.asyncio
    async def test_v03_clean_interface_hides_persona_details(self, auth_headers):
        """Test that v0.3 doesn't expose persona implementation details"""
        headers = auth_headers
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/api/v0.3/chat",
                headers=headers,
                json={
                    "message": "Tell me about your persona settings.",
                    "stream": False
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            # Verify clean interface
            assert set(data.keys()) == {"response", "conversation_id"}
            
            # Response shouldn't expose technical persona details
            response_lower = data["response"].lower()
            
            # Should not mention technical terms
            technical_terms = [
                "persona_id",
                "system_prompt",
                "prompt_template",
                "persona configuration",
                "database"
            ]
            
            for term in technical_terms:
                assert term not in response_lower, f"Should not expose technical term: {term}"