
"""
Test organization:
- tests/unit/: Fast, isolated unit tests
- tests/integration/: Service interaction tests
- tests/e2e/: End-to-end browser and API tests
"""

"""
Pytest configuration for Gaia Platform tests.
"""

import pytest
import asyncio
import os
from tests.fixtures.screenshot_cleanup import (
    screenshot_manager,
    screenshot_cleanup,
    screenshot_on_failure
)

# Configure pytest for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Test environment configuration
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    # API_KEY is optional when using JWT authentication
    # Tests should use TestAuthManager for authentication
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@db:5432/llm_platform")
    os.environ.setdefault("NATS_URL", "nats://nats:4222")

# Shared test user for integration tests
@pytest.fixture(scope="session")
def shared_test_user():
    """
    Create a single test user for the entire test session.
    This reduces Supabase API calls and prevents resource exhaustion.
    """
    try:
        from tests.fixtures.test_auth import TestUserFactory
        factory = TestUserFactory()
        
        test_email = os.getenv("GAIA_TEST_EMAIL", "test@example.com")
        test_password = os.getenv("GAIA_TEST_PASSWORD", "default-test-password")
        
        # First, delete any existing user with this email to ensure clean state
        print(f"Ensuring clean state for test user: {test_email}")
        factory.cleanup_user_by_email(test_email)
        
        # Now create a fresh test user
        user = factory.create_verified_test_user(
            email=test_email,
            password=test_password
        )
        print(f"Created fresh test user: {user['email']}")
        
        yield user
        
        # Always cleanup at end of session
        try:
            factory.cleanup_test_user(user["user_id"])
            print(f"Cleaned up test user: {user['email']}")
        except Exception as e:
            print(f"Warning: Failed to cleanup test user: {e}")
    except Exception as e:
        print(f"Warning: Could not create shared test user (Supabase not configured?): {e}")
        # Provide a mock user for tests that don't need real Supabase
        yield {
            "user_id": "mock-user-id",
            "email": "mock@test.local", 
            "password": "mock-password"
        }

# Markers for test categorization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "compatibility: mark test as LLM Platform compatibility test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "screenshot: mark test as taking screenshots"
    )
    config.addinivalue_line(
        "markers", "keep_screenshots: mark test to preserve its screenshots"
    )
