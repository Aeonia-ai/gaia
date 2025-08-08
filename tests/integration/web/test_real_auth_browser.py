"""
Browser tests using real authentication to verify the auth flow works.
"""
import pytest
from playwright.async_api import async_playwright
import os
import sys

# Add integration helpers to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers.browser_auth import BrowserAuthHelper

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_real_login_and_navigation(test_user_credentials):
    """Test real login flow and navigation to chat"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # Navigate to login page
            await page.goto(f"{WEB_SERVICE_URL}/login")
            
            # Verify we're on login page
            login_form = await page.query_selector('form')
            assert login_form is not None, "Login form should be present"
            
            # Fill in credentials
            email = test_user_credentials["email"]
            password = test_user_credentials["password"]
            
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            
            # Submit form
            await page.click('button[type="submit"]')
            
            # Wait for navigation with increased timeout
            await page.wait_for_url("**/chat", timeout=30000)
            
            # Verify we're on chat page
            assert "/chat" in page.url, "Should be on chat page"
            
            # Verify chat interface loaded
            chat_form = await page.wait_for_selector('#chat-form', timeout=10000)
            assert chat_form is not None, "Chat form should be present"
            
            # Check for message input
            message_input = await page.query_selector('textarea[name="message"], input[name="message"]')
            assert message_input is not None, "Message input should be present"
            
        finally:
            await browser.close()


@pytest.mark.asyncio 
async def test_send_message_with_real_auth(test_user_credentials):
    """Test sending a message after real login"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # Use helper for login
            success = await BrowserAuthHelper.login_with_real_user(page, test_user_credentials)
            assert success, "Login should succeed"
            
            # Wait a bit for page to stabilize
            await page.wait_for_timeout(2000)
            
            # Find message input
            message_input = await page.query_selector('textarea[name="message"], input[name="message"]')
            assert message_input is not None, "Message input should exist"
            
            # Send a test message
            test_message = "Hello from integration test!"
            await message_input.fill(test_message)
            
            # Find and click send button
            send_button = await page.query_selector('button[type="submit"], button:has-text("Send")')
            assert send_button is not None, "Send button should exist"
            
            await send_button.click()
            
            # Wait for message to be sent (input clears)
            await page.wait_for_function(
                """() => {
                    const input = document.querySelector('textarea[name="message"], input[name="message"]');
                    return input && input.value === '';
                }""",
                timeout=10000
            )
            
            # Check that message appears in chat
            await page.wait_for_timeout(2000)  # Give time for message to appear
            
            messages_area = await page.query_selector('#messages')
            assert messages_area is not None, "Messages area should exist"
            
            # Look for our message
            message_elements = await page.query_selector_all(f'text="{test_message}"')
            assert len(message_elements) > 0, "Our message should appear in chat"
            
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_session_persistence(test_user_credentials):
    """Test that session persists across page reloads"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # Login
            success = await BrowserAuthHelper.login_with_real_user(page, test_user_credentials)
            assert success, "Login should succeed"
            
            # Get cookies
            cookies = await context.cookies()
            session_cookie = next((c for c in cookies if c["name"] == "session"), None)
            assert session_cookie is not None, "Session cookie should be set"
            
            # Reload page
            await page.reload()
            
            # Should still be on chat page
            await page.wait_for_url("**/chat", timeout=10000)
            assert "/chat" in page.url, "Should remain on chat page after reload"
            
            # Chat interface should still be available
            chat_form = await page.query_selector('#chat-form')
            assert chat_form is not None, "Chat form should still be present after reload"
            
        finally:
            await browser.close()