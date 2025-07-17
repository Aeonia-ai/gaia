"""Integration tests for web authentication flow"""
import pytest
import os
from starlette.testclient import TestClient
from app.services.web.main import app
from app.services.web.config import settings


# Mark as integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "true",
        reason="Integration tests require RUN_INTEGRATION_TESTS=true"
    )
]


class TestAuthIntegration:
    """Integration tests for authentication flow"""
    
    @pytest.fixture
    def client(self):
        """Create test client for web service"""
        return TestClient(app)
    
    def test_full_auth_flow_dev_user(self, client):
        """Test complete auth flow for dev user"""
        # 1. Access protected route - should redirect
        response = client.get("/chat", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        
        # 2. Login with dev credentials
        response = client.post("/auth/login", data={
            "email": "dev@gaia.local",
            "password": "testtest"
        }, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/chat"
        
        # 3. Access protected route - should work now
        response = client.get("/chat")
        assert response.status_code == 200
        assert "Welcome back" in response.text
        
        # 4. Logout
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        
        # 5. Protected route should redirect again
        response = client.get("/chat", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
    
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_URL"),
        reason="Requires Supabase configuration"
    )
    def test_real_user_registration_flow(self, client):
        """Test real user registration (requires Supabase)"""
        import uuid
        test_email = f"test-{uuid.uuid4()}@example.com"
        
        # 1. Register new user
        response = client.post("/auth/register", data={
            "email": test_email,
            "password": "testpass123"
        })
        
        # Check response based on Supabase config
        if "successful" in response.text:
            assert response.status_code == 200
            assert "Registration successful" in response.text
        else:
            # May fail due to email domain restrictions
            assert "email" in response.text.lower()
    
    def test_error_display_formatting(self, client):
        """Test that errors are displayed properly"""
        # Test with definitely invalid email
        response = client.post("/auth/register", data={
            "email": "notanemail",
            "password": "password123"
        })
        
        assert response.status_code == 200
        # Should show error div with proper styling
        assert "bg-red-900/20" in response.text
        assert "border-red-600" in response.text
        assert "text-red-300" in response.text
    
    def test_session_persistence(self, client):
        """Test session persists across requests"""
        # Login
        client.post("/auth/login", data={
            "email": "dev@gaia.local",
            "password": "test"
        })
        
        # Make multiple requests
        for _ in range(3):
            response = client.get("/chat")
            assert response.status_code == 200
            assert "Welcome back, Local Development User" in response.text
    
    def test_concurrent_sessions(self):
        """Test multiple clients can have independent sessions"""
        client1 = TestClient(app)
        client2 = TestClient(app)
        
        # Login with client1
        response1 = client1.post("/auth/login", data={
            "email": "dev@gaia.local",
            "password": "test"
        })
        assert response1.status_code == 303
        
        # Client2 should still be unauthenticated
        response2 = client2.get("/chat", follow_redirects=False)
        assert response2.status_code == 303
        assert response2.headers["location"] == "/login"
        
        # Client1 should be authenticated
        response1 = client1.get("/chat")
        assert response1.status_code == 200