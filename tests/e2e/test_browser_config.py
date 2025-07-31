"""
Browser test configuration and utilities.
"""
import os
import pytest
import asyncio
import httpx
from playwright.async_api import async_playwright


def get_web_service_url():
    """Get the correct web service URL for browser tests."""
    # In Docker test container
    if os.path.exists("/.dockerenv"):
        return "http://web-service:8000"
    # Explicit override
    if os.getenv("WEB_SERVICE_URL"):
        return os.getenv("WEB_SERVICE_URL")
    # Default to Docker service name
    return "http://web-service:8000"


async def check_service_health(url: str, timeout: int = 10):
    """Check if web service is healthy."""
    async with httpx.AsyncClient() as client:
        for _ in range(timeout):
            try:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
    return False


# Skip browser tests if not in proper environment
browser_test = pytest.mark.skipif(
    os.getenv("SKIP_BROWSER_TESTS", "false").lower() == "true",
    reason="Browser tests skipped (set SKIP_BROWSER_TESTS=false to run)"
)


# Mark tests that require real browser
requires_browser = pytest.mark.skipif(
    not os.getenv("RUN_BROWSER_TESTS", "false").lower() == "true",
    reason="Browser tests require RUN_BROWSER_TESTS=true"
)