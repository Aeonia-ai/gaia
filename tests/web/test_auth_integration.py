"""Integration tests for web authentication flow"""
import pytest
import os
from starlette.testclient import TestClient
from app.services.web.main import app
from app.services.web.config import settings


# Mark as integration tests
pytestmark = pytest.mark.integration


class TestAuthIntegration:
    """Integration tests for authentication flow"""
    
    # Remove client fixture - using the one from conftest.py
    
    @pytest.mark.skip(reason="Dev user login requires DEBUG mode configuration")
    def test_full_auth_flow_dev_user(self, client):
        """Test complete auth flow for dev user"""
        # NOTE: This test requires DEBUG=true in environment
        # Could be updated to use a real test user instead
        
        # 1. Access protected route - should redirect
        response = client.get("/chat", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        
        # 2. Login with dev credentials
        response = client.post("/auth/login", data={
            "email": "dev@gaia.local",
            "password": "test"  # Corrected password
        }, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/chat"
        
        # 3. Access protected route - should work now
        response = client.get("/chat")
        assert response.status_code == 200
        # assert "Welcome back" in response.text  # TODO: Add welcome message
        
        # 4. Logout
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        
        # 5. Protected route should redirect again
        response = client.get("/chat", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
    
    def test_real_user_registration_and_login_flow(self, client, test_user_factory):
        """Test real user registration and login using service key"""
        # Create a pre-verified test user
        test_user = test_user_factory.create_verified_test_user()
        
        # 1. Try to login with the created user
        response = client.post("/auth/login", data={
            "email": test_user["email"],
            "password": test_user["password"]
        }, follow_redirects=False)
        
        # Should redirect to chat on successful login
        assert response.status_code == 303
        assert response.headers["location"] == "/chat"
        
        # 2. Access protected route - should work
        response = client.get("/chat")
        assert response.status_code == 200
        
        # 3. Logout
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
    
    def test_error_display_formatting(self, client):
        """Test that errors are displayed properly"""
        # Test with definitely invalid email
        response = client.post("/auth/register", data={
            "email": "notanemail",
            "password": "password123"
        })
        
        assert response.status_code == 200
        # Should show error div with proper styling (updated to match current CSS)
        assert "bg-red-500/10" in response.text
        assert "border-red-500/30" in response.text
        assert "text-red-200" in response.text
    
    def test_session_persistence(self, client, test_user_factory):
        """Test session persists across requests"""
        # Create and login with test user
        test_user = test_user_factory.create_verified_test_user()
        
        response = client.post("/auth/login", data={
            "email": test_user["email"],
            "password": test_user["password"]
        }, follow_redirects=False)
        assert response.status_code == 303
        
        # Make multiple requests
        for _ in range(3):
            response = client.get("/chat")
            assert response.status_code == 200
            # TODO: Add welcome message assertion when implemented
            # assert f"Welcome back" in response.text
    
    def test_concurrent_sessions(self, test_user_factory):
        """Test multiple clients can have independent sessions"""
        # Create separate clients
        client1 = TestClient(app)
        client2 = TestClient(app)
        
        # Create test user
        test_user = test_user_factory.create_verified_test_user()
        
        # Login with client1
        response1 = client1.post("/auth/login", data={
            "email": test_user["email"],
            "password": test_user["password"]
        }, follow_redirects=False)
        assert response1.status_code == 303
        
        # Client2 should still be unauthenticated
        response2 = client2.get("/chat", follow_redirects=False)
        assert response2.status_code == 303
        assert response2.headers["location"] == "/login"
        
        # Client1 should be authenticated
        response1 = client1.get("/chat")
        assert response1.status_code == 200