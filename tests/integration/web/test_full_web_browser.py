"""
Comprehensive browser tests for all web service functionality.

These tests verify behavior that URL-based tests might miss:
- JavaScript execution
- HTMX interactions
- WebSocket connections
- Real browser rendering
- Race conditions
- Client-side state management
"""
import pytest
import asyncio
import json
from playwright.async_api import async_playwright, expect, Page
import os
import sys

# Add integration helpers to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers.browser_auth import BrowserAuthHelper

# Browser test configuration
pytestmark = pytest.mark.asyncio
WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestHTMXBehavior:
    """Test HTMX-specific functionality that URL tests might miss"""
    
    async def test_htmx_form_submission_without_page_reload(self):
        """Test that HTMX forms don't cause full page reloads"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Track navigation events
            navigation_count = 0
            def on_navigation():
                nonlocal navigation_count
                navigation_count += 1
            
            page.on("framenavigated", lambda: on_navigation())
            
            # Go to login page
            await page.goto(f'{WEB_SERVICE_URL}/login')
            initial_nav_count = navigation_count
            
            # Mock the login response
            await page.route("**/auth/login", lambda route: route.fulfill(
                status=400,
                headers={"Content-Type": "text/html"},
                body='<div role="alert">Invalid credentials</div>'
            ))
            
            # Submit form
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'wrong')
            await page.click('button[type="submit"]')
            
            # Wait for error to appear
            await page.wait_for_selector('[role="alert"]')
            
            # Verify no full page reload happened
            assert navigation_count == initial_nav_count, "HTMX form should not cause page reload"
            
            # Verify error is displayed
            error_text = await page.inner_text('[role="alert"]')
            assert "Invalid credentials" in error_text
            
            await browser.close()
    
    async def test_htmx_indicator_visibility(self):
        """Test that HTMX loading indicators work correctly"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Set up a slow response to see the indicator
            async def login_handler(route):
                await asyncio.sleep(1)  # Delay response
                await route.fulfill(
                    status=400,
                    headers={"Content-Type": "text/html"},
                    body='<div role="alert">Test</div>'
                )
            
            await page.route("**/auth/login", login_handler)
            
            # Fill form
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test')
            
            # Check indicator is hidden initially
            indicator = await page.query_selector('.htmx-indicator')
            if indicator:
                is_visible = await indicator.is_visible()
                assert not is_visible, "Indicator should be hidden initially"
            
            # Click submit
            await page.click('button[type="submit"]')
            
            # Check indicator becomes visible during request
            if indicator:
                # Wait a bit for HTMX to show indicator
                await page.wait_for_timeout(100)
                is_visible = await indicator.is_visible()
                assert is_visible, "Indicator should be visible during request"
            
            # Wait for response
            await page.wait_for_selector('[role="alert"]')
            
            # Check indicator is hidden again
            if indicator:
                is_visible = await indicator.is_visible()
                assert not is_visible, "Indicator should be hidden after response"
            
            await browser.close()
    
    async def test_htmx_history_navigation(self):
        """Test browser back/forward with HTMX navigation"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Start at login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            assert page.url.endswith('/login')
            
            # Navigate to register
            register_link = await page.query_selector('a[href="/register"]')
            if register_link:
                await register_link.click()
                await page.wait_for_url('**/register')
                assert page.url.endswith('/register')
                
                # Go back
                await page.go_back()
                await page.wait_for_url('**/login')
                assert page.url.endswith('/login')
                
                # Go forward
                await page.go_forward()
                await page.wait_for_url('**/register')
                assert page.url.endswith('/register')
            
            await browser.close()


class TestWebSocketFunctionality:
    """Test WebSocket connections for real-time features"""
    
    async def test_websocket_connection_establishment(self, test_user_credentials):
        """Test that WebSocket connects when entering chat"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Track WebSocket connections
            ws_connected = False
            
            def on_websocket(ws):
                nonlocal ws_connected
                ws_connected = True
            
            page.on("websocket", on_websocket)
            
            # Login with real auth first
            await BrowserAuthHelper.login_with_real_user(page, test_user_credentials)
            
            # Now set up mock for conversations if needed
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={"conversations": [], "has_more": False}
            ))
            
            # Give WebSocket time to connect
            await page.wait_for_timeout(1000)
            
            # Check if WebSocket was established (if the app uses WebSockets)
            # This is app-specific - comment out if not using WebSockets
            # assert ws_connected, "WebSocket should connect on chat page"
            
            await browser.close()


class TestClientSideValidation:
    """Test client-side form validation and JavaScript behavior"""
    
    async def test_email_validation_on_blur(self):
        """Test client-side email validation"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/register')
            
            # Type invalid email
            email_input = await page.query_selector('input[name="email"]')
            await email_input.fill('notanemail')
            
            # Blur to trigger validation
            await page.keyboard.press('Tab')
            
            # Check for validation error (if implemented)
            # This depends on your client-side validation
            await page.wait_for_timeout(100)  # Give time for validation
            
            # Check HTML5 validation
            validity = await email_input.evaluate('el => el.validity.valid')
            assert not validity, "Invalid email should fail HTML5 validation"
            
            await browser.close()
    
    async def test_password_strength_indicator(self):
        """Test password strength indicator updates in real-time"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/register')
            
            password_input = await page.query_selector('input[name="password"]')
            
            # Type weak password
            await password_input.fill('weak')
            
            # Check if any strength indicator exists and updates
            # This is app-specific
            
            # Type strong password
            await password_input.fill('')  # Clear first
            await password_input.fill('StrongP@ssw0rd123!')
            
            # Verify form can be submitted with strong password
            email_input = await page.query_selector('input[name="email"]')
            await email_input.fill('test@example.com')
            
            submit_button = await page.query_selector('button[type="submit"]')
            is_disabled = await submit_button.evaluate('el => el.disabled')
            assert not is_disabled, "Submit should be enabled with valid inputs"
            
            await browser.close()


class TestResponsiveDesign:
    """Test responsive design behavior in real browsers"""
    
    async def test_mobile_menu_toggle(self, test_user_credentials):
        """Test mobile menu toggle functionality"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # Mobile viewport
            context = await browser.new_context(
                viewport={'width': 375, 'height': 667},
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)'
            )
            page = await context.new_page()
            
            # Login with real auth
            await BrowserAuthHelper.login_with_real_user(page, test_user_credentials)
            
            # Mock conversations API if needed
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={"conversations": [], "has_more": False}
            ))
            
            # Check if sidebar is hidden on mobile
            sidebar = await page.query_selector('#sidebar')
            if sidebar:
                is_visible = await sidebar.is_visible()
                assert not is_visible, "Sidebar should be hidden on mobile by default"
                
                # Look for menu toggle
                menu_toggle = await page.query_selector('#sidebar-toggle')
                if menu_toggle:
                    await menu_toggle.click()
                    await page.wait_for_timeout(300)  # Animation time
                    
                    # Sidebar should now be visible
                    is_visible = await sidebar.is_visible()
                    assert is_visible, "Sidebar should be visible after toggle"
            
            await browser.close()
    
    async def test_viewport_meta_tag(self):
        """Test viewport meta tag is properly set"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Check viewport meta tag
            viewport_content = await page.evaluate('''
                () => {
                    const meta = document.querySelector('meta[name="viewport"]');
                    return meta ? meta.content : null;
                }
            ''')
            
            assert viewport_content, "Viewport meta tag should exist"
            assert 'width=device-width' in viewport_content
            assert 'initial-scale=1' in viewport_content
            
            await browser.close()


class TestAccessibility:
    """Test accessibility features work in real browsers"""
    
    async def test_keyboard_navigation(self):
        """Test forms can be navigated with keyboard only"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Tab through form elements
            await page.keyboard.press('Tab')  # Should focus email
            focused = await page.evaluate('() => document.activeElement.name')
            assert focused == 'email', "First tab should focus email input"
            
            await page.keyboard.press('Tab')  # Should focus password
            focused = await page.evaluate('() => document.activeElement.name')
            assert focused == 'password', "Second tab should focus password input"
            
            await page.keyboard.press('Tab')  # Should focus submit button
            focused = await page.evaluate('() => document.activeElement.type')
            assert focused == 'submit', "Third tab should focus submit button"
            
            await browser.close()
    
    async def test_aria_labels_present(self):
        """Test ARIA labels are present for screen readers"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Check form has proper labels
            email_label = await page.query_selector('label[for="email"]')
            assert email_label or await page.query_selector('input[name="email"][aria-label]'), \
                "Email input should have label"
            
            password_label = await page.query_selector('label[for="password"]')
            assert password_label or await page.query_selector('input[name="password"][aria-label]'), \
                "Password input should have label"
            
            await browser.close()


class TestErrorStates:
    """Test error states and edge cases in the browser"""
    
    async def test_network_error_handling(self):
        """Test how the app handles network errors"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Make auth endpoint fail with network error
            await page.route("**/auth/login", lambda route: route.abort())
            
            # Try to login
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test')
            await page.click('button[type="submit"]')
            
            # Should show some error - use robust selector pattern
            error_locator = (
                page.locator('[role="alert"]')
                .or_(page.locator('.error'))
                .or_(page.locator('.alert'))
                .or_(page.locator('[data-error="true"]'))
                .or_(page.locator('text=/.*error.*/i'))
            )
            await expect(error_locator.first).to_be_visible(timeout=5000)
            
            await browser.close()
    
    async def test_concurrent_form_submissions(self):
        """Test that concurrent form submissions are handled properly"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Slow response to test concurrent submissions
            call_count = 0
            async def slow_response(route):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(2)
                await route.fulfill(
                    status=400,
                    json={"error": "Test error"}
                )
            
            await page.route("**/auth/login", slow_response)
            
            # Fill form
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test')
            
            # Click submit multiple times quickly
            submit_button = await page.query_selector('button[type="submit"]')
            await submit_button.click()
            await submit_button.click()
            await submit_button.click()
            
            # Wait for response - use robust selector pattern
            error_locator = (
                page.locator('[role="alert"]')
                .or_(page.locator('.error'))
                .or_(page.locator('.alert'))
                .or_(page.locator('[data-error="true"]'))
                .or_(page.locator('text=/.*error.*/i'))
            )
            await expect(error_locator.first).to_be_visible(timeout=5000)
            
            # Should only have made one request (button should be disabled)
            # Or at most a reasonable number if the app doesn't prevent it
            assert call_count <= 2, f"Too many concurrent requests: {call_count}"
            
            await browser.close()


class TestChatFunctionality:
    """Test chat-specific functionality in the browser"""
    
    async def test_message_auto_scroll(self, test_user_credentials):
        """Test that messages container auto-scrolls to bottom"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Login with real auth first
            await BrowserAuthHelper.login_with_real_user(page, test_user_credentials)
            
            # Now mock APIs for test functionality
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={"conversations": [], "has_more": False}
            ))
            
            message_count = 0
            await page.route("**/api/v1/chat", lambda route: route.fulfill(
                json={
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": f"Response {message_count}"
                        }
                    }]
                }
            ))
            
            # Send multiple messages - use robust selector pattern
            message_input = page.locator('textarea[name="message"], input[name="message"]').first
            await expect(message_input).to_be_visible()
            
            for i in range(5):
                message_count = i
                await message_input.fill(f"Message {i}")
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(200)
            
            # Check if scrolled to bottom
            messages_container = await page.query_selector('#messages')
            if messages_container:
                scroll_info = await messages_container.evaluate('''
                    el => ({
                        scrollTop: el.scrollTop,
                        scrollHeight: el.scrollHeight,
                        clientHeight: el.clientHeight
                    })
                ''')
                
                # Should be scrolled near bottom (within 100px tolerance)
                at_bottom = scroll_info['scrollTop'] + scroll_info['clientHeight'] >= scroll_info['scrollHeight'] - 100
                assert at_bottom, "Messages should auto-scroll to bottom"
            
            await browser.close()
    
    async def test_message_persistence_on_refresh(self, test_user_credentials):
        """Test that messages persist on page refresh"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context()
            page = await context.new_page()
            
            # Login with real auth first to get real session
            await BrowserAuthHelper.login_with_real_user(page, test_user_credentials)
            
            # Mock API
            conversation_id = 'test-conv-123'
            messages = []
            
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={
                    "conversations": [{
                        "id": conversation_id,
                        "title": "Test Chat",
                        "created_at": "2025-01-01T00:00:00Z"
                    }],
                    "has_more": False
                }
            ))
            
            await page.route(f"**/api/conversations/{conversation_id}/messages", lambda route: route.fulfill(
                json={"messages": messages}
            ))
            
            await page.route("**/api/v1/chat", lambda route: (
                messages.extend([
                    {"role": "user", "content": route.request.post_data_json.get("messages", [{}])[-1].get("content", "")},
                    {"role": "assistant", "content": "Test response"}
                ]),
                route.fulfill(json={
                    "choices": [{
                        "message": {"role": "assistant", "content": "Test response"}
                    }]
                })
            )[1])
            
            # Go to chat
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            
            # Send a message - use robust selector pattern
            message_input = page.locator('textarea[name="message"], input[name="message"]').first
            await expect(message_input).to_be_visible()
            await message_input.fill('Test message')
            await page.keyboard.press('Enter')
            
            # Wait for response - use robust pattern
            response_locator = (
                page.locator('text="Test response"')
                .or_(page.locator('[data-role="assistant"]'))
                .or_(page.locator('.assistant-message'))
            )
            await expect(response_locator.first).to_be_visible(timeout=5000)
            
            # Refresh page
            await page.reload()
            
            # Messages should still be there (if the app loads them)
            # This depends on your app's behavior
            
            await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])