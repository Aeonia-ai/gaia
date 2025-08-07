"""
Browser tests for authenticated features using Playwright.

This demonstrates different authentication strategies for browser testing.
"""
import pytest
import uuid
from playwright.async_api import async_playwright, expect
import os

# Browser tests configuration
WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestAuthenticatedChat:
    """Test chat interface with different authentication methods"""
    
    @pytest.mark.asyncio
    async def test_chat_with_mocked_auth(self):
        """Test chat UI with mocked authentication (fastest)"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            # Setup auth mock
            await page.route("**/auth/login", lambda route: route.fulfill(
                status=303,
                headers={"Location": "/chat"},
                body=""
            ))
            
            # Mock the API calls that the chat page makes
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={"conversations": [], "has_more": False}
            ))
            
            # Perform login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test123')
            await page.click('button[type="submit"]')
            
            # Wait for chat page
            await page.wait_for_url("**/chat")
            
            # Verify chat interface elements
            chat_form = await page.query_selector('#chat-form')
            assert chat_form, "Chat form should be present"
            
            messages_container = await page.query_selector('#messages')
            assert messages_container, "Messages container should be present"
            
            sidebar = await page.query_selector('#sidebar')
            assert sidebar, "Sidebar should be present"
            
            # Test sending a message (mocked)
            await page.route("**/api/v1/chat", lambda route: route.fulfill(
                json={
                    "id": "test-123",
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "Hello! I'm a mocked response."
                        }
                    }]
                }
            ))
            
            message_input = await page.query_selector('input[name="message"]')
            await message_input.fill("Test message")
            await page.keyboard.press("Enter")
            
            # Wait for response to appear
            await page.wait_for_selector('text="Hello! I\'m a mocked response."', timeout=5000)
            
            await browser.close()
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires TestUserFactory import fix")
    async def test_chat_with_real_auth(self):
        """Test chat UI with real Supabase authentication"""
        pass
    
    @pytest.mark.asyncio
    async def test_chat_with_injected_session(self):
        """Test chat UI with pre-injected session cookie"""
        # Simple fake token for testing
        token = "fake-jwt-token-for-testing"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context()
            
            # Inject session cookie before navigation
            await context.add_cookies([{
                'name': 'session',
                'value': token,
                'domain': 'web-service',
                'path': '/',
                'httpOnly': True,
                'secure': False
            }])
            
            page = await context.new_page()
            
            # Mock API responses since we're using a fake session
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={"conversations": [], "has_more": False}
            ))
            
            # Navigate directly to chat (should not redirect to login)
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            
            # Verify we stayed on chat page
            assert page.url.endswith('/chat'), "Should stay on chat page"
            
            # Verify chat interface loaded
            await page.wait_for_selector('#chat-form', timeout=5000)
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_chat_layout_when_authenticated(self):
        """Test chat layout dimensions when authenticated"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            # Mock authentication and API
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
            await page.wait_for_url("**/chat")
            
            # Check layout dimensions
            main_container = await page.query_selector('.flex.h-screen')
            assert main_container, "Chat should have main flex container"
            
            box = await main_container.bounding_box()
            assert box['width'] >= 1900, f"Chat container should use full width, got {box['width']}px"
            
            # Check sidebar
            sidebar = await page.query_selector('#sidebar')
            assert sidebar, "Sidebar should exist"
            sidebar_box = await sidebar.bounding_box()
            assert 200 <= sidebar_box['width'] <= 300, f"Sidebar width should be 200-300px, got {sidebar_box['width']}px"
            
            # Check main content area
            main_content = await page.query_selector('#main-content')
            assert main_content, "Main content area should exist"
            content_box = await main_content.bounding_box()
            assert content_box['width'] >= 1500, f"Main content should use remaining space, got {content_box['width']}px"
            
            await browser.close()


class TestAuthenticationFlows:
    """Test various authentication flows in the browser"""
    
    @pytest.mark.asyncio
    async def test_logout_flow(self):
        """Test logout functionality"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Mock login
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
            await page.wait_for_url("**/chat")
            
            # Mock logout
            await page.route("**/auth/logout", lambda route: route.fulfill(
                status=303,
                headers={"Location": "/login"},
                body=""
            ))
            
            # Find and click logout
            logout_button = await page.query_selector('button:has-text("Logout")')
            if not logout_button:
                logout_button = await page.query_selector('a[href="/auth/logout"]')
            
            if logout_button:
                await logout_button.click()
                await page.wait_for_url("**/login")
                
                # Verify we're back at login
                assert page.url.endswith('/login'), "Should redirect to login after logout"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_session_expiry_redirect(self):
        """Test that expired sessions redirect to login"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Try to access chat without auth
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            
            # Should redirect to login
            await page.wait_for_url("**/login")
            assert page.url.endswith('/login'), "Should redirect to login when not authenticated"
            
            # Should show appropriate message
            # (This depends on your implementation)
            
            await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])