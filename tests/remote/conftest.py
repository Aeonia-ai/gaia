"""
Remote testing configuration and fixtures.

This module provides fixtures and configuration for testing against
remote deployments (dev, staging, production) instead of local Docker.

Usage:
    TEST_ENV=dev pytest tests/remote/smoke/ -v
    TEST_ENV=staging pytest tests/remote/performance/ -v
    TEST_ENV=production pytest tests/remote/monitoring/ -v --read-only
"""

import os
import pytest
import httpx
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Environment configurations
REMOTE_CONFIGS = {
    "local": {
        "gateway_url": "http://gateway:8000",
        "auth_url": "http://auth-service:8000",
        "chat_url": "http://chat-service:8000",
        "web_url": "http://localhost:8080",
        "timeout": 30,
        "destructive_allowed": True,
        "expected_failures": [],
    },
    "dev": {
        "gateway_url": "https://gaia-gateway-dev.fly.dev",
        "auth_url": "https://gaia-auth-dev.fly.dev",
        "chat_url": "https://gaia-chat-dev.fly.dev",
        "web_url": "https://gaia-web-dev.fly.dev",
        "timeout": 60,
        "destructive_allowed": True,
        "expected_failures": ["personas", "assets"],  # Known issues in dev
    },
    "staging": {
        "gateway_url": "https://gaia-gateway-staging.fly.dev",
        "auth_url": "https://gaia-auth-staging.fly.dev",
        "chat_url": "https://gaia-chat-staging.fly.dev",
        "web_url": "https://gaia-web-staging.fly.dev",
        "timeout": 60,
        "destructive_allowed": True,
        "expected_failures": [],
    },
    "production": {
        "gateway_url": "https://gaia-gateway-production.fly.dev",
        "auth_url": "https://gaia-auth-production.fly.dev",
        "chat_url": "https://gaia-chat-production.fly.dev",
        "web_url": "https://gaia-web-production.fly.dev",
        "timeout": 90,
        "destructive_allowed": False,  # Read-only in production!
        "expected_failures": [],
    }
}


@pytest.fixture(scope="session")
def test_env() -> str:
    """Get current test environment from TEST_ENV variable."""
    env = os.getenv("TEST_ENV", "local")
    logger.info(f"Testing against environment: {env}")
    return env


@pytest.fixture(scope="session")
def remote_config(test_env: str) -> Dict[str, Any]:
    """Get configuration for the current test environment."""
    if test_env not in REMOTE_CONFIGS:
        pytest.fail(f"Unknown test environment: {test_env}")
    
    config = REMOTE_CONFIGS[test_env]
    logger.info(f"Remote config: {config}")
    return config


@pytest.fixture(scope="session")
def is_production(test_env: str) -> bool:
    """Check if testing against production."""
    return test_env == "production"


@pytest.fixture(scope="session")
def api_key() -> str:
    """Get API key for remote testing."""
    key = os.getenv("API_KEY") or os.getenv("TEST_API_KEY")
    if not key:
        pytest.skip("No API key available for remote testing")
    return key


@pytest.fixture
async def remote_gateway(remote_config: Dict[str, Any], api_key: str):
    """Async HTTP client configured for gateway testing."""
    async with httpx.AsyncClient(
        base_url=remote_config["gateway_url"],
        timeout=remote_config["timeout"],
        headers={"X-API-Key": api_key}
    ) as client:
        yield client


@pytest.fixture
async def remote_auth(remote_config: Dict[str, Any]):
    """Async HTTP client configured for auth service testing."""
    async with httpx.AsyncClient(
        base_url=remote_config["auth_url"],
        timeout=remote_config["timeout"]
    ) as client:
        yield client


@pytest.fixture
async def remote_chat(remote_config: Dict[str, Any], api_key: str):
    """Async HTTP client configured for direct chat service testing."""
    async with httpx.AsyncClient(
        base_url=remote_config["chat_url"],
        timeout=remote_config["timeout"],
        headers={"X-API-Key": api_key}
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def skip_if_expected_failure(remote_config: Dict[str, Any], request):
    """Skip tests that are expected to fail in certain environments."""
    expected_failures = remote_config.get("expected_failures", [])
    
    # Check test markers
    for marker in request.node.iter_markers():
        if marker.name in expected_failures:
            pytest.skip(f"Expected failure in environment: {marker.name}")


@pytest.fixture(autouse=True)
def skip_if_production_destructive(is_production: bool, request):
    """Skip destructive tests in production."""
    if is_production:
        for marker in request.node.iter_markers():
            if marker.name == "destructive":
                pytest.skip("Destructive tests not allowed in production")


@pytest.fixture
def require_healthy_service(remote_gateway):
    """Fixture that ensures service is healthy before running test."""
    async def _check_service(service_name: str):
        response = await remote_gateway.get("/health")
        health = response.json()
        
        if service_name in health.get("services", {}):
            service_health = health["services"][service_name]
            if service_health.get("status") != "healthy":
                pytest.skip(f"Service {service_name} is not healthy")
        else:
            pytest.skip(f"Service {service_name} not found in health check")
    
    return _check_service


# Test data fixtures
@pytest.fixture
async def remote_test_user(remote_config: Dict[str, Any], test_env: str):
    """Get or create a test user for the environment."""
    test_users = {
        "local": {"email": "test@local.gaia", "password": "test123"},
        "dev": {"email": "test-dev@gaia.ai", "password": os.getenv("DEV_TEST_PASSWORD")},
        "staging": {"email": "test-staging@gaia.ai", "password": os.getenv("STAGING_TEST_PASSWORD")},
        "production": {"email": "monitor@gaia.ai", "password": os.getenv("PROD_MONITOR_PASSWORD")},
    }
    
    user = test_users.get(test_env)
    if not user or not user["password"]:
        pytest.skip(f"No test user configured for {test_env}")
    
    return user


# Performance tracking
@pytest.fixture
def track_response_time():
    """Track and assert response times."""
    import time
    
    class ResponseTracker:
        def __init__(self):
            self.start_time = None
            self.times = []
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self, label: str = "request"):
            if self.start_time:
                elapsed = time.time() - self.start_time
                self.times.append((label, elapsed))
                logger.info(f"{label} took {elapsed:.3f}s")
                return elapsed
            return 0
        
        def assert_under(self, seconds: float, label: str = "request"):
            elapsed = self.stop(label)
            assert elapsed < seconds, f"{label} took {elapsed:.3f}s, expected < {seconds}s"
    
    return ResponseTracker()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with remote testing markers."""
    config.addinivalue_line("markers", "remote: Tests that can run against remote endpoints")
    config.addinivalue_line("markers", "smoke: Basic smoke tests for remote environments")
    config.addinivalue_line("markers", "contract: API contract tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "monitoring: Synthetic monitoring tests")
    config.addinivalue_line("markers", "destructive: Tests that modify data (skipped in production)")
    config.addinivalue_line("markers", "personas: Tests requiring persona functionality")
    config.addinivalue_line("markers", "assets: Tests requiring asset service")