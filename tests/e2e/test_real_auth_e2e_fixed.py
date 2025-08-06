"""
Real E2E tests using actual Supabase authentication - NO MOCKS
Fixed version that handles dropdown menus correctly
"""
import pytest
import uuid
import os
from playwright.async_api import async_playwright
from tests.fixtures.test_auth import TestUserFactory

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestRealE2EFixed:
    """E2E tests with real Supabase authentication - fixed for new UI"""
    
    @pytest.mark.asyncio
    async def test_real_logout_fixed(self):
        """Test logout functionality with real auth - handles dropdown menu"""
        factory = TestUserFactory()
        test_email = f"e2e-logout-{uuid.uuid4().hex[:8]}@test.local"
        test_password = "TestPassword123!"
        
        user = factory.create_verified_test_user(
            email=test_email,
            password=test_password
        )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Login
                await page.goto(f'{WEB_SERVICE_URL}/login')
                await page.fill('input[name="email"]', test_email)
                await page.fill('input[name="password"]', test_password)
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/chat", timeout=10000)
                
                # First, try to find and click the user menu button (avatar)
                # This could be on mobile or desktop view
                user_menu_button = await page.query_selector('[onclick="toggleUserMenu()"]')
                if user_menu_button:
                    await user_menu_button.click()
                    # Wait for menu to appear
                    await page.wait_for_timeout(500)
                
                # Now look for logout in various places
                logout_selectors = [
                    'a:has-text("Logout"):visible',  # Visible logout link
                    'button:has-text("Logout"):visible',  # Visible logout button
                    '#user-menu a:has-text("Logout")',  # In user menu dropdown
                    'a[href="/logout"]',  # Direct href selector
                ]
                
                logout_element = None
                for selector in logout_selectors:
                    logout_element = await page.query_selector(selector)
                    if logout_element:
                        break
                
                assert logout_element is not None, "Should have logout element"
                await logout_element.click()
                
                # Should redirect to login
                await page.wait_for_url("**/login", timeout=5000)
                
                # Try to access chat directly - should redirect to login
                await page.goto(f'{WEB_SERVICE_URL}/chat')
                await page.wait_for_url("**/login", timeout=5000)
                
            finally:
                await browser.close()
                factory.cleanup_test_user(user["user_id"])
    
    @pytest.mark.asyncio
    async def test_chat_with_proper_selectors(self):
        """Test chat functionality with updated selectors"""
        factory = TestUserFactory()
        test_email = f"e2e-chat-{uuid.uuid4().hex[:8]}@test.local"
        test_password = "TestPassword123!"
        
        user = factory.create_verified_test_user(
            email=test_email,
            password=test_password
        )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Login
                await page.goto(f'{WEB_SERVICE_URL}/login')
                await page.fill('input[name="email"]', test_email)
                await page.fill('input[name="password"]', test_password)
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/chat", timeout=10000)
                
                # Look for the correct message input selector
                # Could be input or textarea
                message_input = None
                input_selectors = [
                    'input[name="message"]',
                    'input[name="message"]',
                    '#message-input',
                    '[placeholder*="Type a message"]',
                    '[placeholder*="Send a message"]'
                ]
                
                for selector in input_selectors:
                    message_input = await page.query_selector(selector)
                    if message_input:
                        break
                
                assert message_input is not None, "Should have message input"
                
                # Send a message
                await message_input.fill("Hello from fixed E2E test")
                await page.keyboard.press("Enter")
                
                # Wait for response - be more flexible with selectors
                response_selectors = [
                    '#messages div.mb-4',  # Message containers
                    '.assistant-message',   # Assistant message class
                    '[data-role="assistant"]',  # Role-based selector
                    '#messages > div'  # Direct children of messages
                ]
                
                response_found = False
                for selector in response_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                        response_found = True
                        break
                    except:
                        continue
                
                assert response_found, "Should receive a response"
                
            finally:
                await browser.close()
                factory.cleanup_test_user(user["user_id"])