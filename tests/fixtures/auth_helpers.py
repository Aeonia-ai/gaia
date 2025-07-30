"""
Helper functions for authentication in tests
"""
from starlette.testclient import TestClient
from unittest.mock import patch, Mock
import asyncio


def create_authenticated_session(client: TestClient, email: str = "test@test.local", 
                               user_id: str = "test-user-id") -> TestClient:
    """
    Create an authenticated session by mocking the login flow.
    
    The web service stores auth info in the session after successful login.
    """
    # Create a mock session
    session_data = {
        "access_token": "test-jwt-token",
        "refresh_token": "test-refresh-token", 
        "user": {
            "id": user_id,
            "email": email,
            "email_confirmed_at": "2024-01-01T00:00:00Z"
        }
    }
    
    # Patch the session for this client
    # Note: Starlette TestClient manages sessions internally
    # We need to simulate a successful login
    
    # Mock the gateway client to return success
    from unittest.mock import AsyncMock
    
    with patch('app.services.web.routes.auth.GaiaAPIClient') as mock_gateway:
        # Create an async mock instance
        mock_instance = AsyncMock()
        
        # Mock successful login
        mock_instance.login.return_value = {
            "session": {
                "access_token": "test-jwt-token",
                "refresh_token": "test-refresh-token",
                "expires_in": 3600,
                "token_type": "bearer"
            },
            "user": {
                "id": user_id,
                "email": email,
                "email_confirmed_at": "2024-01-01T00:00:00Z"
            }
        }
        
        # Set up async context manager
        mock_gateway.return_value.__aenter__.return_value = mock_instance
        
        # Perform login to set session
        response = client.post("/auth/login", data={
            "email": email,
            "password": "test-password"
        }, follow_redirects=False)
        
        # Should redirect to chat on success
        if response.status_code != 303:
            raise ValueError(f"Login failed with status {response.status_code}")
            
    return client