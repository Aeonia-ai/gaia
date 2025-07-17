"""Shared fixtures for web service tests"""
import pytest
from unittest.mock import Mock, AsyncMock
from starlette.testclient import TestClient
from app.services.web.main import app


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