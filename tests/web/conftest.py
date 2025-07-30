"""Shared fixtures for web service tests"""
import os
import pytest
from unittest.mock import Mock, AsyncMock, patch
from starlette.testclient import TestClient
from app.services.web.main import app

# Import test auth utilities
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fixtures.test_auth import TestAuthManager, JWTTestAuth, TestUserFactory
from fixtures.auth_helpers import create_authenticated_session


@pytest.fixture
def client():
    """Test client for FastHTML app"""
    return TestClient(app)


@pytest.fixture
def mock_gateway_client():
    """Mock gateway client for isolated testing"""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_session():
    """Mock session object"""
    session = Mock()
    session.get = Mock(return_value=None)
    session.set = Mock()
    session.clear = Mock()
    return session


@pytest.fixture
def mock_auth_response():
    """Sample successful auth response"""
    return {
        "session": {
            "access_token": "test-jwt-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "token_type": "bearer"
        },
        "user": {
            "id": "test-user-id",
            "email": "test@example.com",
            "created_at": "2024-01-01T00:00:00Z"
        }
    }


@pytest.fixture
def dev_user_response():
    """Dev user auth response"""
    return {
        "session": {
            "access_token": "dev-jwt-token",
            "refresh_token": "dev-refresh-token",
            "expires_in": 3600,
            "token_type": "bearer"
        },
        "user": {
            "id": "dev-user-id",
            "email": "dev@gaia.local",
            "created_at": "2024-01-01T00:00:00Z"
        }
    }


# New auth fixtures for improved testing
@pytest.fixture
def jwt_auth():
    """JWT auth helper for unit tests"""
    return JWTTestAuth()


@pytest.fixture
def auth_headers(jwt_auth):
    """Default auth headers for unit tests"""
    return jwt_auth.create_auth_headers()


@pytest.fixture
def authenticated_client(client):
    """Client with authenticated session"""
    # Create a client with an authenticated session
    return create_authenticated_session(client)


@pytest.fixture(scope="session")
def test_user_factory():
    """Factory for creating real Supabase test users (integration tests only)"""
    if os.getenv("RUN_INTEGRATION_TESTS") != "true":
        pytest.skip("Integration tests require RUN_INTEGRATION_TESTS=true")
    
    factory = TestUserFactory()
    yield factory
    # Cleanup all created users after test session
    factory.cleanup_all()


@pytest.fixture
def integration_test_user(test_user_factory):
    """Create a real test user for integration tests"""
    user = test_user_factory.create_verified_test_user()
    yield user
    # Individual cleanup happens in factory


@pytest.fixture
def test_auth_manager(request):
    """
    Provides appropriate auth manager based on test type.
    Use @pytest.mark.integration to get real Supabase users.
    """
    if request.node.get_closest_marker("integration"):
        manager = TestAuthManager("integration")
    else:
        manager = TestAuthManager("unit")
    
    yield manager
    manager.cleanup()


@pytest.fixture
def auth_client(client, test_auth_manager):
    """Client with appropriate auth for test type"""
    headers = test_auth_manager.get_auth_headers()
    for key, value in headers.items():
        client.headers[key] = value
    return client