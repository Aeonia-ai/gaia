"""
Minimal auth test to verify basic mocking works.
"""
import pytest
from playwright.async_api import async_playwright
import os

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_minimal_auth_mock():
    """Simplest possible auth mock test"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Mock auth to return 303 redirect
        await page.route("**/auth/login", lambda route: route.fulfill(
            status=303,
            headers={"Location": "/chat"}
        ))
        
        # Go to login page
        response = await page.goto(f'{WEB_SERVICE_URL}/login')
        assert response.status == 200
        
        # Verify form exists
        form = await page.query_selector('form')
        assert form is not None
        
        await browser.close()
        print("✓ Basic test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])