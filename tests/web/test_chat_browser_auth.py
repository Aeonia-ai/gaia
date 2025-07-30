"""
Example browser tests for chat functionality using various authentication methods.
"""
import pytest
from playwright.async_api import expect
import os

# Import our auth fixtures from the same directory
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from browser_auth_fixtures import (
    mock_authenticated_page,
    real_authenticated_page,
    session_authenticated_context,
    multi_user_contexts,
    auth_page_objects,
    authenticated_page_with_mocks
)

# Browser test configuration
pytestmark = pytest.mark.asyncio
WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestChatWithAuth:
    """Test chat functionality with proper authentication"""
    
    async def test_send_message_with_mock_auth(self, authenticated_page_with_mocks):
        """Test sending a chat message with mocked authentication"""
        page = authenticated_page_with_mocks
        
        # Send a message
        message_input = await page.query_selector('textarea[name="message"]')
        await message_input.fill("Hello, AI assistant!")
        await page.keyboard.press("Enter")
        
        # Wait for mocked response
        await page.wait_for_selector('text="This is a mocked AI response for testing."')
        
        # Verify message appears in chat
        messages = await page.query_selector_all('#messages > div')
        assert len(messages) >= 2  # User message + AI response
    
    async def test_conversation_list_with_mock_auth(self, authenticated_page_with_mocks):
        """Test conversation list shows mocked conversations"""
        page = authenticated_page_with_mocks
        
        # Check sidebar has conversation
        await page.wait_for_selector('text="Test Conversation"')
        
        # Click on conversation
        conv_link = await page.query_selector('text="Test Conversation"')
        await conv_link.click()
        
        # Verify we're still on chat page
        assert page.url.endswith('/chat') or '/chat/' in page.url
    
    async def test_logout_flow(self, authenticated_page_with_mocks):
        """Test logout functionality"""
        page = authenticated_page_with_mocks
        
        # Find logout button
        logout_btn = await page.query_selector('button:has-text("Logout")')
        if not logout_btn:
            logout_btn = await page.query_selector('a[href="/auth/logout"]')
        
        assert logout_btn, "Logout button should exist"
        
        # Click logout
        await logout_btn.click()
        
        # Should redirect to login
        await page.wait_for_url("**/login")
        assert page.url.endswith('/login')
    
    async def test_chat_with_page_objects(self, page, auth_page_objects):
        """Test using page object pattern"""
        LoginPage = auth_page_objects["LoginPage"]
        ChatPage = auth_page_objects["ChatPage"]
        
        # Mock auth
        await page.route("**/auth/login", lambda route: route.fulfill(
            status=303,
            headers={"Location": "/chat"},
            body=""
        ))
        await page.route("**/api/conversations", lambda route: route.fulfill(
            json={"conversations": [], "has_more": False}
        ))
        
        # Login using page object
        login_page = LoginPage(page)
        await login_page.goto()
        await login_page.login("test@test.local", "test123")
        
        # Wait for chat
        await page.wait_for_url("**/chat")
        
        # Use chat page object
        chat_page = ChatPage(page)
        
        # Mock chat response
        await page.route("**/api/v1/chat", lambda route: route.fulfill(
            json={
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "Hello from page object test!"
                    }
                }]
            }
        ))
        
        await chat_page.send_message("Test message")
        
        # Verify response appears
        await page.wait_for_selector('text="Hello from page object test!"')
    
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_SERVICE_KEY"),
        reason="Requires SUPABASE_SERVICE_KEY for real auth"
    )
    async def test_real_chat_flow(self, real_authenticated_page):
        """Test with real Supabase authentication"""
        page = real_authenticated_page
        
        # We're on the real chat page with a real session
        chat_form = await page.query_selector('#chat-form')
        assert chat_form, "Chat form should exist with real auth"
        
        # Could test real API calls here if needed
        # For now just verify we're authenticated
        cookies = await page.context.cookies()
        session_cookie = next((c for c in cookies if c['name'] == 'session'), None)
        assert session_cookie is not None
    
    async def test_multi_user_chat(self, multi_user_contexts):
        """Test multiple users in chat simultaneously"""
        # Get contexts for different users
        alice_ctx = multi_user_contexts["alice@test.local"]
        bob_ctx = multi_user_contexts["bob@test.local"]
        
        # Create pages for each user
        alice_page = await alice_ctx.new_page()
        bob_page = await bob_ctx.new_page()
        
        try:
            # Mock API responses
            for page in [alice_page, bob_page]:
                await page.route("**/api/conversations", lambda route: route.fulfill(
                    json={"conversations": [], "has_more": False}
                ))
            
            # Both navigate to chat
            await alice_page.goto(f"{WEB_SERVICE_URL}/chat")
            await bob_page.goto(f"{WEB_SERVICE_URL}/chat")
            
            # Verify both are on chat page
            assert alice_page.url.endswith('/chat')
            assert bob_page.url.endswith('/chat')
            
            # Each user has their own session
            alice_session = await alice_page.evaluate("() => document.cookie")
            bob_session = await bob_page.evaluate("() => document.cookie")
            assert alice_session != bob_session
            
        finally:
            await alice_page.close()
            await bob_page.close()


class TestAuthenticationEdgeCases:
    """Test authentication edge cases and error handling"""
    
    async def test_expired_session_redirect(self, page):
        """Test that expired sessions redirect to login"""
        # Try to access chat without auth
        await page.goto(f"{WEB_SERVICE_URL}/chat")
        
        # Should redirect to login
        await page.wait_for_url("**/login")
        assert page.url.endswith('/login')
    
    async def test_invalid_login_shows_error(self, page):
        """Test that invalid credentials show error message"""
        await page.goto(f"{WEB_SERVICE_URL}/login")
        
        # Mock failed login
        await page.route("**/auth/login", lambda route: route.fulfill(
            status=400,
            json={"error": "Invalid credentials"}
        ))
        
        # Try to login
        await page.fill('input[name="email"]', 'wrong@test.local')
        await page.fill('input[name="password"]', 'wrongpass')
        await page.click('button[type="submit"]')
        
        # Should show error
        await page.wait_for_selector('[role="alert"]')
        error_text = await page.inner_text('[role="alert"]')
        assert "Invalid credentials" in error_text
    
    async def test_session_persistence_across_navigation(self, session_authenticated_context):
        """Test that session persists across page navigation"""
        page = await session_authenticated_context.new_page()
        
        # Mock API
        await page.route("**/api/conversations", lambda route: route.fulfill(
            json={"conversations": [], "has_more": False}
        ))
        
        # Navigate to chat
        await page.goto(f"{WEB_SERVICE_URL}/chat")
        assert page.url.endswith('/chat')
        
        # Navigate away and back
        await page.goto(f"{WEB_SERVICE_URL}/")
        await page.goto(f"{WEB_SERVICE_URL}/chat")
        
        # Should still be authenticated
        assert page.url.endswith('/chat')
        
        await page.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])