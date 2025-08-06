"""
Integration tests using real authentication with test users.
These tests actually verify the web service functionality.
"""
import pytest
from playwright.async_api import async_playwright
import os
from tests.fixtures.test_auth import TestUserFactory

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestRealAuthentication:
    """Test chat functionality with real test users"""
    
    @pytest.fixture
    async def test_user(self):
        """Create a real test user for authentication"""
        factory = TestUserFactory()
        user = factory.create_verified_test_user()
        yield user
        # Cleanup after test
        factory.cleanup_test_user(user['user_id'])
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("SUPABASE_SERVICE_KEY"), 
                        reason="Requires SUPABASE_SERVICE_KEY for real auth")
    async def test_real_login_and_chat_access(self, test_user):
        """Test real login flow and chat page access"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to real login page
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Fill in real test user credentials
            await page.fill('input[name="email"]', test_user['email'])
            await page.fill('input[name="password"]', test_user['password'])
            
            # Submit the form
            await page.click('button[type="submit"]')
            
            # Wait for navigation to complete
            await page.wait_for_timeout(2000)
            
            # Check if we successfully logged in
            current_url = page.url
            
            # If successful, we should be on the chat page
            # If not, we might see an error or still be on login
            if "/chat" in current_url:
                print(f"✓ Successfully logged in and navigated to chat")
                
                # Verify chat elements exist
                chat_form = await page.query_selector('#chat-form')
                assert chat_form is not None, "Chat form should exist after login"
                
                message_input = await page.query_selector('textarea[name="message"]')
                assert message_input is not None, "Message input should exist"
                
            elif "/login" in current_url:
                # Still on login page - check for errors
                error_element = await page.query_selector('.error')
                if error_element:
                    error_text = await error_element.inner_text()
                    pytest.fail(f"Login failed with error: {error_text}")
                else:
                    pytest.fail("Login failed - still on login page")
            else:
                pytest.fail(f"Unexpected URL after login: {current_url}")
            
            await browser.close()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("SUPABASE_SERVICE_KEY"), 
                        reason="Requires SUPABASE_SERVICE_KEY for real auth")
    async def test_send_message_with_real_auth(self, test_user):
        """Test sending a chat message with real authentication"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Login with real user
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.fill('input[name="email"]', test_user['email'])
            await page.fill('input[name="password"]', test_user['password'])
            await page.click('button[type="submit"]')
            
            # Wait for login to complete
            await page.wait_for_timeout(2000)
            
            # Navigate to chat if not already there
            if "/chat" not in page.url:
                await page.goto(f'{WEB_SERVICE_URL}/chat')
                await page.wait_for_timeout(1000)
            
            # Try to send a message
            message_input = await page.query_selector('textarea[name="message"]')
            if message_input:
                await message_input.fill("Hello from integration test!")
                
                submit_button = await page.query_selector('#chat-form button[type="submit"]')
                if submit_button:
                    # Monitor network for API calls
                    api_called = False
                    
                    def check_request(request):
                        nonlocal api_called
                        if "chat" in request.url and request.method == "POST":
                            api_called = True
                    
                    page.on("request", check_request)
                    
                    await submit_button.click()
                    await page.wait_for_timeout(2000)
                    
                    # Verify message was sent (API was called)
                    assert api_called, "Chat API should have been called when sending message"
                    
                    # Check if message appears in UI
                    messages = await page.query_selector_all('.message')
                    assert len(messages) > 0, "Should see at least one message after sending"
            else:
                pytest.fail("Could not find message input on chat page")
            
            await browser.close()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("SUPABASE_SERVICE_KEY"), 
                        reason="Requires SUPABASE_SERVICE_KEY for real auth")
    async def test_unauthorized_chat_access(self):
        """Test that chat redirects to login when not authenticated"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Try to access chat without logging in
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            await page.wait_for_timeout(1000)
            
            # Should be redirected to login
            assert "/login" in page.url, "Should redirect to login when not authenticated"
            
            # Verify login form is present
            login_form = await page.query_selector('form')
            assert login_form is not None, "Login form should be present"
            
            await browser.close()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("SUPABASE_SERVICE_KEY"), 
                        reason="Requires SUPABASE_SERVICE_KEY for real auth") 
    async def test_session_persistence(self, test_user):
        """Test that session persists across page reloads"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.fill('input[name="email"]', test_user['email'])
            await page.fill('input[name="password"]', test_user['password'])
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(2000)
            
            # Navigate to chat
            if "/chat" not in page.url:
                await page.goto(f'{WEB_SERVICE_URL}/chat')
            
            # Reload the page
            await page.reload()
            await page.wait_for_timeout(1000)
            
            # Should still be on chat page (session persisted)
            if "/login" in page.url:
                pytest.fail("Session did not persist - redirected to login after reload")
            
            # Chat elements should still be accessible
            chat_form = await page.query_selector('#chat-form')
            assert chat_form is not None, "Chat form should exist after reload"
            
            await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])