"""
Playwright-specific test configuration for browser tests.
"""
import os
import pytest
import asyncio
from playwright.async_api import async_playwright
import httpx
import logging

logger = logging.getLogger(__name__)


def get_base_url():
    """Get the correct base URL based on test environment."""
    # Check if we're running inside Docker
    if os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
        return "http://web-service:8000"
    
    # Check for explicit test URL
    test_url = os.getenv("TEST_BASE_URL")
    if test_url:
        return test_url
    
    # Default to Docker service name (we're in test container)
    return "http://web-service:8000"


async def wait_for_service(url: str, timeout: int = 30):
    """Wait for web service to be ready."""
    async with httpx.AsyncClient() as client:
        for _ in range(timeout):
            try:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    logger.info(f"Service ready at {url}")
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
    
    raise TimeoutError(f"Service not ready at {url} after {timeout} seconds")


@pytest.fixture
async def browser_context():
    """Provide a browser context with proper configuration."""
    base_url = get_base_url()
    
    # Wait for service to be ready
    await wait_for_service(base_url)
    
    async with async_playwright() as p:
        # Use headless mode in containers
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']  # Required in Docker
        )
        
        context = await browser.new_context(
            base_url=base_url,
            viewport={'width': 1280, 'height': 720},
            ignore_https_errors=True  # For local development
        )
        
        yield context
        
        await context.close()
        await browser.close()


@pytest.fixture
async def page(browser_context):
    """Provide a page with base URL configured."""
    page = await browser_context.new_page()
    yield page
    await page.close()


@pytest.fixture
async def authenticated_page(page):
    """Provide a page with authenticated session."""
    # Mock the login to set session
    await page.goto("/login")
    
    # Intercept the login request and return success
    await page.route("**/auth/login", lambda route: route.fulfill(
        status=303,
        headers={"Location": "/chat"},
        body=""
    ))
    
    # Fill and submit login form
    await page.fill('input[name="email"]', 'test@test.local')
    await page.fill('input[name="password"]', 'test-password')
    await page.click('button[type="submit"]')
    
    # Wait for navigation
    await page.wait_for_url("**/chat")
    
    return page


# Pytest configuration for async tests
def pytest_configure(config):
    """Configure pytest for playwright async tests."""
    # Set asyncio mode
    config.option.asyncio_mode = "auto"