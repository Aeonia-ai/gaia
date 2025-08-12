"""
Load test specific fixtures and configuration.
"""
import pytest
import os
import logging

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def load_test_config():
    """Configuration for load tests."""
    return {
        "max_concurrent_requests": int(os.getenv("LOAD_TEST_CONCURRENT_REQUESTS", "5")),
        "max_concurrent_users": int(os.getenv("LOAD_TEST_CONCURRENT_USERS", "3")),
        "burst_size": int(os.getenv("LOAD_TEST_BURST_SIZE", "10")),
        "burst_delay": float(os.getenv("LOAD_TEST_BURST_DELAY", "0.1")),
        "max_rps": int(os.getenv("LOAD_TEST_MAX_RPS", "10")),
        "timeout": float(os.getenv("LOAD_TEST_TIMEOUT", "30.0")),
    }


@pytest.fixture
def gateway_url():
    """Gateway URL for load tests."""
    return os.getenv("GATEWAY_URL", "http://gateway:8000")


@pytest.fixture
def auth_url():
    """Auth service URL for load tests."""
    return os.getenv("AUTH_URL", "http://auth-service:8000")


@pytest.fixture
def headers(api_key):
    """Headers with API key for load tests."""
    api_key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
    if not api_key:
        pytest.skip("No API key available for load tests")
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }


# Import shared fixtures from main conftest
from tests.conftest import shared_test_user


@pytest.fixture
def test_user_factory():
    """Factory for creating test users in load tests."""
    from tests.fixtures.test_auth import TestUserFactory
    return TestUserFactory()


def pytest_configure(config):
    """Configure pytest for load tests."""
    # Add load test specific markers
    config.addinivalue_line(
        "markers", "load: Load tests that test system under concurrent load"
    )
    
    # Log load test configuration
    if config.getoption("-m") and "load" in config.getoption("-m"):
        logger.info("Running load tests")