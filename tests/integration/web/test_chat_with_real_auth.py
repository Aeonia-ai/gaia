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
                
                # Try multiple selectors for message input
                message_input = None
                selectors = [
                    'textarea[name="message"]',
                    'textarea#message',
                    'textarea[placeholder*="message" i]',
                    'textarea[placeholder*="type" i]',
                    '#chat-input',
                    '#message-input',
                    'input[name="message"]',
                    'form textarea',
                    'textarea'
                ]
                
                for selector in selectors:
                    message_input = await page.query_selector(selector)
                    if message_input:
                        print(f"Found message input with selector: {selector}")
                        break
                
                if not message_input:
                    # Get page content to debug
                    content = await page.content()
                    print(f"Page content length: {len(content)}")
                    print("Looking for textarea elements...")
                    textareas = await page.query_selector_all('textarea')
                    print(f"Found {len(textareas)} textarea elements")
                    forms = await page.query_selector_all('form')
                    print(f"Found {len(forms)} form elements")
                
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
            
            # Try to send a message - look for input or textarea
            message_input = await page.query_selector('input[name="message"]') or await page.query_selector('textarea[name="message"]')
            if message_input:
                test_message = "Hello from integration test!"
                await message_input.fill(test_message)
                
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
                    messages = await page.query_selector_all('#messages > div')
                    assert len(messages) > 0, "Should see at least one message after sending"
                    
                    # Verify our message is displayed
                    message_texts = []
                    for msg in messages:
                        text = await msg.inner_text()
                        message_texts.append(text)
                    
                    assert any(test_message in text for text in message_texts), \
                        f"Should see our test message '{test_message}' in messages"
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