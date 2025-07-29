"""
Simple browser test to verify Playwright setup works.
"""
import pytest
from playwright.async_api import async_playwright
import os

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_browser_can_load_login_page():
    """Simple test to verify browser tests work"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Just try to load the login page
        await page.goto(f'{WEB_SERVICE_URL}/login')
        
        # Check title
        title = await page.title()
        assert title == "Gaia Platform"
        
        # Check login form exists
        login_form = await page.query_selector('form[hx-post="/auth/login"]')
        assert login_form is not None
        
        await browser.close()


@pytest.mark.asyncio
async def test_browser_can_navigate_to_register():
    """Test navigation between pages"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Go to login
        await page.goto(f'{WEB_SERVICE_URL}/login')
        
        # Find and click register link
        register_link = await page.query_selector('a[href="/register"]')
        if register_link:
            await register_link.click()
            await page.wait_for_url('**/register')
            
            # Verify we're on register page
            assert page.url.endswith('/register')
            
            # Check register form exists
            register_form = await page.query_selector('form[hx-post="/auth/register"]')
            assert register_form is not None
        
        await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])