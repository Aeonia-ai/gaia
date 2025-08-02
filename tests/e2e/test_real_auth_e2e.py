"""
Real E2E tests using actual Supabase authentication - NO MOCKS
"""
import pytest
import uuid
import os
from playwright.async_api import async_playwright
from tests.fixtures.test_auth import TestUserFactory

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestRealE2E:
    """E2E tests with real Supabase authentication"""
    
    @pytest.mark.asyncio
    async def test_real_login_and_chat(self):
        """Test complete flow: create user, login, send chat message"""
        # Create real Supabase user
        factory = TestUserFactory()
        test_email = f"e2e-{uuid.uuid4().hex[:8]}@test.local"
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
                # Real login - no mocks!
                await page.goto(f'{WEB_SERVICE_URL}/login')
                await page.fill('input[name="email"]', test_email)
                await page.fill('input[name="password"]', test_password)
                await page.click('button[type="submit"]')
                
                # Wait for redirect to chat
                await page.wait_for_url("**/chat", timeout=10000)
                
                # Verify we're on chat page
                assert page.url.endswith('/chat'), "Should be on chat page"
                
                # Send a real message
                message_input = await page.wait_for_selector('input[name="message"]', timeout=5000)
                await message_input.fill("Hello, this is a real E2E test!")
                await page.keyboard.press("Enter")
                
                # Wait for AI response - look for any text that indicates a response
                # The AI might say various things, so we wait for the message to appear after ours
                await page.wait_for_timeout(1000)  # Brief wait for message to be sent
                
                # Wait for new content in the messages container
                messages_container = await page.wait_for_selector('#messages', timeout=5000)
                
                # Get all message bubbles
                all_messages = await messages_container.query_selector_all('div.mb-4 > div')
                
                # Should have at least 2 messages (user + assistant)
                assert len(all_messages) >= 2, f"Expected at least 2 messages, found {len(all_messages)}"
                
                # The last message should be from the assistant
                last_message = all_messages[-1]
                message_text = await last_message.inner_text()
                assert len(message_text) > 0, "Assistant response should not be empty"
                
            finally:
                # Cleanup
                await browser.close()
                factory.cleanup_test_user(user["user_id"])
    
    @pytest.mark.asyncio
    async def test_real_conversation_flow(self):
        """Test creating and managing conversations with real auth"""
        factory = TestUserFactory()
        test_email = f"e2e-conv-{uuid.uuid4().hex[:8]}@test.local"
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
                
                # Send first message
                await page.fill('input[name="message"]', "What is Python?")
                await page.keyboard.press("Enter")
                
                # Wait for first response
                await page.wait_for_timeout(2000)
                messages_container = await page.query_selector('#messages')
                first_count = len(await messages_container.query_selector_all('div.mb-4 > div'))
                assert first_count >= 2, "Should have user message and first response"
                
                # Send follow-up message in same conversation
                await page.fill('input[name="message"]', "Can you give an example?")
                await page.keyboard.press("Enter")
                
                # Wait for second response
                await page.wait_for_timeout(2000)
                second_count = len(await messages_container.query_selector_all('div.mb-4 > div'))
                assert second_count >= 4, "Should have at least 4 messages total"
                
                # Check conversation list (if visible)
                conversations = await page.query_selector_all('[data-conversation-id]')
                assert len(conversations) > 0, "Should have at least one conversation"
                
            finally:
                await browser.close()
                factory.cleanup_test_user(user["user_id"])
    
    @pytest.mark.asyncio
    async def test_real_auth_persistence(self):
        """Test that authentication persists across page refreshes"""
        factory = TestUserFactory()
        test_email = f"e2e-persist-{uuid.uuid4().hex[:8]}@test.local"
        test_password = "TestPassword123!"
        
        user = factory.create_verified_test_user(
            email=test_email,
            password=test_password
        )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Login
                await page.goto(f'{WEB_SERVICE_URL}/login')
                await page.fill('input[name="email"]', test_email)
                await page.fill('input[name="password"]', test_password)
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/chat", timeout=10000)
                
                # Refresh page
                await page.reload()
                
                # Should still be on chat page (not redirected to login)
                await page.wait_for_load_state('networkidle')
                assert page.url.endswith('/chat'), "Should stay on chat page after refresh"
                
                # Can still send messages
                await page.fill('input[name="message"]', "Test after refresh")
                await page.keyboard.press("Enter")
                
                # Wait for response
                await page.wait_for_timeout(2000)
                messages = await page.query_selector_all('#messages div.mb-4 > div')
                assert len(messages) >= 2, "Should have messages after refresh"
                
            finally:
                await context.close()
                await browser.close()
                factory.cleanup_test_user(user["user_id"])
    
    @pytest.mark.asyncio
    async def test_real_logout(self):
        """Test logout functionality with real auth"""
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
                
                # Find and click logout
                logout_button = await page.query_selector('button:has-text("Logout")')
                if not logout_button:
                    # Try other possible selectors
                    logout_button = await page.query_selector('a:has-text("Logout")')
                
                assert logout_button is not None, "Should have logout button"
                await logout_button.click()
                
                # Should redirect to login
                await page.wait_for_url("**/login", timeout=5000)
                
                # Try to access chat directly - should redirect to login
                await page.goto(f'{WEB_SERVICE_URL}/chat')
                await page.wait_for_url("**/login", timeout=5000)
                
            finally:
                await browser.close()
                factory.cleanup_test_user(user["user_id"])