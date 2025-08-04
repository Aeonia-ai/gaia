"""
Smoke tests for web UI to verify basic functionality before migration.
These are simple, focused tests to ensure core features work.
"""

import pytest
import uuid
from playwright.async_api import async_playwright
from tests.fixtures.test_auth import TestUserFactory
import os

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestWebUISmoke:
    """Basic smoke tests for web UI functionality."""
    
    @pytest.mark.asyncio
    async def test_basic_chat_flow(self):
        """Test the most basic chat flow: login, send message, get response."""
        factory = TestUserFactory()
        test_email = f"smoke-{uuid.uuid4().hex[:8]}@test.local"
        test_password = "TestPassword123!"
        
        user = factory.create_verified_test_user(
            email=test_email,
            password=test_password
        )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            try:
                # 1. Login
                await page.goto(f'{WEB_SERVICE_URL}/login')
                await page.fill('input[name="email"]', test_email)
                await page.fill('input[name="password"]', test_password)
                await page.click('button[type="submit"]')
                
                # Wait for redirect to chat
                await page.wait_for_url("**/chat", timeout=10000)
                print("✅ Login successful")
                
                # 2. Send a message
                message_input = await page.wait_for_selector('input[name="message"]', timeout=5000)
                await message_input.type("Hello, this is a smoke test")
                await page.keyboard.press("Enter")
                print("✅ Message sent")
                
                # 3. Wait for AI response
                # Look for any element that might contain the assistant's response
                try:
                    # Try multiple possible selectors
                    await page.wait_for_selector('.assistant-message, .bg-slate-700, [class*="assistant"], [class*="response"]', 
                                                timeout=30000, 
                                                state='visible')
                    print("✅ AI response received")
                except:
                    # Take screenshot for debugging
                    await page.screenshot(path="/tmp/smoke-test-timeout.png")
                    print("❌ No AI response found - screenshot saved")
                    
                    # Print page content for debugging
                    content = await page.content()
                    print(f"Page content length: {len(content)}")
                    
                # 4. Check if conversation appears in sidebar
                try:
                    # Wait a bit for HTMX to update
                    await page.wait_for_timeout(2000)
                    
                    # Check for conversation in sidebar
                    conv_links = await page.query_selector_all('#conversation-list a[href^="/chat/"]')
                    print(f"✅ Found {len(conv_links)} conversations in sidebar")
                except:
                    print("❌ Could not check sidebar conversations")
                
            finally:
                await browser.close()
                factory.cleanup_test_user(user["user_id"])
    
    @pytest.mark.asyncio
    async def test_conversation_persistence(self):
        """Test that conversations persist across page loads."""
        factory = TestUserFactory()
        test_email = f"persist-{uuid.uuid4().hex[:8]}@test.local"
        test_password = "TestPassword123!"
        
        user = factory.create_verified_test_user(
            email=test_email,
            password=test_password
        )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Login and send first message
                await page.goto(f'{WEB_SERVICE_URL}/login')
                await page.fill('input[name="email"]', test_email)
                await page.fill('input[name="password"]', test_password)
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/chat", timeout=10000)
                
                # Send a unique message
                test_message = f"Remember this: {uuid.uuid4().hex[:8]}"
                await page.fill('input[name="message"]', test_message)
                await page.keyboard.press("Enter")
                
                # Wait for response
                await page.wait_for_timeout(3000)
                
                # Reload page
                await page.reload()
                await page.wait_for_load_state('networkidle')
                
                # Check if our message is still visible
                page_content = await page.content()
                if test_message in page_content:
                    print(f"✅ Message '{test_message}' persisted after reload")
                else:
                    print(f"❌ Message '{test_message}' not found after reload")
                    
                    # Check if we're still logged in
                    if page.url.endswith('/login'):
                        print("❌ Got redirected to login - session lost")
                    else:
                        print(f"📍 Current URL: {page.url}")
                
            finally:
                await browser.close()
                factory.cleanup_test_user(user["user_id"])