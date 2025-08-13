"""
Simplified browser auth fixtures that avoid async/sync conflicts.
These replace the complex fixtures for reliable testing.
"""
import pytest
import os
from playwright.async_api import Page

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")

@pytest.fixture
async def simple_auth_page(page: Page) -> Page:
    """Simple authenticated page without complex auth classes"""
    
    # Mock auth endpoints
    await page.route("**/auth/login", lambda route: route.fulfill(
        status=303,
        headers={"Location": f"{WEB_SERVICE_URL}/chat"}
    ))
    
    # Mock API responses
    await page.route("**/api/conversations", lambda route: route.fulfill(
        json={"conversations": [], "has_more": False}
    ))
    
    # Do simple login with env credentials
    await page.goto(f"{WEB_SERVICE_URL}/login")
    test_email = os.getenv("GAIA_TEST_EMAIL", "test@example.com")
    test_password = os.getenv("GAIA_TEST_PASSWORD", "default-test-password")
    await page.fill('input[name="email"]', test_email)
    await page.fill('input[name="password"]', test_password)
    await page.click('button[type="submit"]')
    
    # Wait for redirect with timeout
    try:
        await page.wait_for_url("**/chat", timeout=5000)
    except:
        # If redirect fails, just navigate directly
        await page.goto(f"{WEB_SERVICE_URL}/chat")
    
    return page

@pytest.fixture
async def error_test_page(page: Page) -> Page:
    """Simple page for testing error scenarios"""
    await page.goto(f"{WEB_SERVICE_URL}/login")
    return page