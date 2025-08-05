
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
