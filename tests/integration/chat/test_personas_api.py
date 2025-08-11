"""Integration tests for persona API endpoints"""
import pytest
import httpx
from tests.fixtures.test_auth import JWTTestAuth
from tests.fixtures.shared_test_user import shared_test_user

BASE_URL = "http://chat-service:8000"
GATEWAY_URL = "http://gateway:8000"


@pytest.mark.skip(reason="Persona endpoints not exposed through gateway - needs architecture decision")
class TestPersonasAPI:
    """Test persona API endpoints"""
    
    @pytest.fixture
    async def auth_headers(self, shared_test_user):
        """Get auth headers using real JWT from shared test user"""
        # Login through gateway to get real JWT
        gateway_url = "http://gateway:8000"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/api/v1/auth/login",
                json={
                    "email": shared_test_user["email"],
                    "password": shared_test_user["password"]
                }
            )
            assert response.status_code == 200
            jwt_token = response.json()["session"]["access_token"]
            return {"Authorization": f"Bearer {jwt_token}"}
    
    @pytest.mark.asyncio
    async def test_list_personas_requires_auth(self):
        """Test that listing personas requires authentication"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/")
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_list_personas_with_auth(self, auth_headers):
        """Test listing personas with valid authentication"""
        headers = auth_headers
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "personas" in data
            assert "total" in data
            # Should have at least the default Mu persona
            assert data["total"] >= 1
            assert any(p["name"] == "Mu" for p in data["personas"])
    
    @pytest.mark.asyncio
    async def test_get_current_persona_defaults_to_mu(self, auth_headers):
        """Test that users get Mu as default persona"""
        headers = auth_headers
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/current", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["persona"]["name"] == "Mu"
            assert "cheerful robot companion" in data["persona"]["description"].lower()
    
    @pytest.mark.asyncio
    async def test_set_user_persona(self, auth_headers):
        """Test setting a user's active persona"""
        headers = auth_headers
        
        async with httpx.AsyncClient() as client:
            # First get list of personas
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/", headers=headers)
            personas = response.json()["personas"]
            mu_persona = next(p for p in personas if p["name"] == "Mu")
            
            # Set Mu as active persona
            response = await client.post(
                f"{BASE_URL}/api/v0.2/personas/set",
                headers=headers,
                json={"persona_id": mu_persona["id"]}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["persona_id"] == mu_persona["id"]
            
            # Verify it's now the current persona
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/current", headers=headers)
            assert response.json()["persona"]["id"] == mu_persona["id"]
    
    @pytest.mark.asyncio
    async def test_get_specific_persona(self, auth_headers):
        """Test getting a specific persona by ID"""
        headers = auth_headers
        
        async with httpx.AsyncClient() as client:
            # Get list to find Mu's ID
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/", headers=headers)
            mu_persona = next(p for p in response.json()["personas"] if p["name"] == "Mu")
            
            # Get specific persona
            response = await client.get(f"{BASE_URL}/api/v0.2/personas/{mu_persona['id']}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["persona"]["id"] == mu_persona["id"]
            assert data["persona"]["name"] == "Mu"
    
    @pytest.mark.asyncio
    async def test_persona_affects_chat_response(self, shared_test_user):
        """Test that persona selection affects chat responses"""
        # Use the shared test user that exists in the database
        from tests.fixtures.test_auth import JWTTestAuth
        jwt_auth = JWTTestAuth()
        headers = jwt_auth.create_auth_headers(
            user_id=shared_test_user["user_id"],
            email=shared_test_user["email"]
        )
        
        async with httpx.AsyncClient() as client:
            # Send a chat message directly to chat service's unified endpoint
            response = await client.post(
                f"{BASE_URL}/chat/unified",
                headers=headers,
                json={
                    "message": "Hello! Please introduce yourself and tell me who you are.",
                    "response_format": "v0.3"
                }
            )
            print(f"DEBUG: Status code: {response.status_code}")
            print(f"DEBUG: Response text: {response.text}")
            assert response.status_code == 200
            response_data = response.json()
            print(f"DEBUG: Response data: {response_data}")
            response_text = response_data["response"]
            
            # Check for Mu persona characteristics
            # The persona might not always say "Mu" as its name, but should show robot characteristics
            response_lower = response_text.lower()
            
            # Check for any of these Mu characteristics:
            # - Name "mu"
            # - Robot/robotic references
            # - Beep boop expressions
            # - Cheerful/upbeat tone
            has_mu_characteristics = any([
                "mu" in response_lower,
                "robot" in response_lower,
                "beep" in response_lower,
                "boop" in response_lower,
                "cheerful" in response_lower,
                "companion" in response_lower
            ])
            
            assert has_mu_characteristics, f"Response doesn't show Mu persona characteristics: {response_text}"