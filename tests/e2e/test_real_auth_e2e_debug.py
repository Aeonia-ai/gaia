"""
Debug version of real E2E test to see what's happening
"""
import pytest
import uuid
import os
from playwright.async_api import async_playwright
from tests.fixtures.test_auth import TestUserFactory

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_debug_real_auth():
    """Debug test to see what's happening on the chat page"""
    factory = TestUserFactory()
    test_email = f"e2e-debug-{uuid.uuid4().hex[:8]}@test.local"
    test_password = "TestPassword123!"
    
    user = factory.create_verified_test_user(
        email=test_email,
        password=test_password
    )
    
    async with async_playwright() as p:
        # Launch with headful mode for debugging
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        
        try:
            print(f"1. Going to login page...")
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            print(f"2. Filling credentials...")
            await page.fill('input[name="email"]', test_email)
            await page.fill('input[name="password"]', test_password)
            
            print(f"3. Clicking submit...")
            await page.click('button[type="submit"]')
            
            print(f"4. Waiting for navigation...")
            await page.wait_for_url("**/chat", timeout=10000)
            
            print(f"5. Current URL: {page.url}")
            
            # Take screenshot
            await page.screenshot(path="chat-page-debug.png")
            print("6. Screenshot saved as chat-page-debug.png")
            
            # Get page content
            print("7. Page title:", await page.title())
            
            # Check for error messages
            error_elements = await page.query_selector_all('[role="alert"], .error, .alert')
            if error_elements:
                print("8. Found error elements:")
                for elem in error_elements:
                    text = await elem.inner_text()
                    print(f"   - {text}")
            
            # Check what's actually on the page
            print("9. Looking for chat elements...")
            
            # Try different selectors
            selectors_to_try = [
                'textarea[name="message"]',
                'textarea',
                'input[type="text"]',
                '#message-input',
                '.message-input',
                '[data-testid="message-input"]'
            ]
            
            for selector in selectors_to_try:
                element = await page.query_selector(selector)
                if element:
                    print(f"   ✅ Found: {selector}")
                else:
                    print(f"   ❌ Not found: {selector}")
            
            # Get page HTML structure
            print("10. Page structure (first 500 chars):")
            content = await page.content()
            print(content[:500])
            
        finally:
            await browser.close()
            factory.cleanup_test_user(user["user_id"])
            print(f"11. Cleaned up user: {user['user_id']}")