"""
Simple chat browser test for debugging.
"""
import pytest
from playwright.async_api import async_playwright
import os

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_chat_page_loads():
    """Test that chat page loads after mock login"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        print("Setting up mocks...")
        
        # Mock authentication - simple redirect
        await page.route("**/auth/login", lambda route: route.fulfill(
            status=303,
            headers={"Location": "/chat"},
            body=""
        ))
        
        # Mock conversations API
        await page.route("**/api/conversations", lambda route: route.fulfill(
            status=200,
            json={"conversations": [], "has_more": False}
        ))
        
        print(f"Navigating to {WEB_SERVICE_URL}/login")
        await page.goto(f'{WEB_SERVICE_URL}/login')
        
        print("Filling login form...")
        await page.fill('input[name="email"]', 'test@test.local')
        await page.fill('input[name="password"]', 'test123')
        
        print("Clicking submit...")
        await page.click('button[type="submit"]')
        
        print("Waiting for navigation to chat...")
        try:
            await page.wait_for_url('**/chat', timeout=5000)
            print(f"✓ Successfully navigated to: {page.url}")
        except Exception as e:
            print(f"✗ Navigation failed: {e}")
            print(f"Current URL: {page.url}")
            # Take screenshot for debugging
            await page.screenshot(path="tests/web/screenshots/chat-nav-failed.png")
            raise
        
        # Check if chat form exists
        print("Looking for chat form...")
        chat_form = await page.query_selector('#chat-form')
        if chat_form:
            print("✓ Chat form found")
        else:
            print("✗ Chat form not found")
            # Get page content for debugging
            content = await page.content()
            print(f"Page content preview: {content[:500]}")
        
        await browser.close()


@pytest.mark.asyncio
async def test_chat_message_input():
    """Test that we can interact with message input"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Setup mocks
        await page.route("**/auth/login", lambda route: route.fulfill(
            status=303,
            headers={"Location": "/chat"},
            body=""
        ))
        
        await page.route("**/api/conversations", lambda route: route.fulfill(
            json={"conversations": [], "has_more": False}
        ))
        
        # Login
        await page.goto(f'{WEB_SERVICE_URL}/login')
        await page.fill('input[name="email"]', 'test@test.local')
        await page.fill('input[name="password"]', 'test123')
        await page.click('button[type="submit"]')
        
        # Wait for chat page
        await page.wait_for_url('**/chat', timeout=5000)
        
        # Find message input
        print("Looking for message input...")
        message_input = await page.query_selector('textarea[name="message"]')
        if not message_input:
            # Try other selectors
            message_input = await page.query_selector('#message-input')
            if not message_input:
                message_input = await page.query_selector('textarea[placeholder*="message"]')
        
        if message_input:
            print("✓ Message input found")
            
            # Type in it
            await message_input.fill("Test message")
            value = await message_input.input_value()
            assert value == "Test message", "Should be able to type in message input"
            print("✓ Can type in message input")
        else:
            print("✗ Message input not found")
            # List all textareas for debugging
            textareas = await page.query_selector_all('textarea')
            print(f"Found {len(textareas)} textareas on page")
            for i, ta in enumerate(textareas):
                name = await ta.get_attribute('name')
                placeholder = await ta.get_attribute('placeholder')
                print(f"  Textarea {i}: name='{name}', placeholder='{placeholder}'")
        
        await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])