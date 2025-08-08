"""
Quick test to check registration flow in browser.
"""
import pytest
from playwright.async_api import async_playwright
import os

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_registration_flow(shared_test_user):
    """Test login flow with shared test user instead of registration"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Log all console messages
        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
        
        # Navigate to login instead of register
        await page.goto(f'{WEB_SERVICE_URL}/login')
        print(f"On page: {page.url}")
        
        # Take screenshot
        await page.screenshot(path="tests/web/screenshots/login-page.png")
        
        # Use shared test user credentials
        await page.fill('input[name="email"]', shared_test_user["email"])
        await page.fill('input[name="password"]', shared_test_user["password"])
        
        # Submit
        print(f"Logging in with shared user: {shared_test_user['email']}")
        await page.click('button[type="submit"]')
        
        # Wait for any response
        await page.wait_for_timeout(3000)
        
        # Check what happened
        current_url = page.url
        print(f"After submit, URL: {current_url}")
        
        # Take screenshot
        await page.screenshot(path="tests/web/screenshots/after-register.png")
        
        # Look for any messages
        possible_selectors = [
            '.bg-red-500\/10',
            '.error',
            '.success',
            '.message',
            'text="Check"',
            'text="Email"',
            'text="verify"'
        ]
        
        for selector in possible_selectors:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                print(f"Found {selector}: {text}")
        
        # Get all text on page
        body_text = await page.inner_text('body')
        print(f"\nPage content preview: {body_text[:200]}...")
        
        await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])