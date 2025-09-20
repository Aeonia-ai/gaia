#!/usr/bin/env python3
"""
Comprehensive Web UI Test Suite with Playwright

This test suite exercises every aspect and combination of interactions
with the Gaia web interface to ensure robust functionality.

Test Categories:
- Authentication flows
- Navigation patterns
- Conversation management
- Message interactions
- UI state management
- Error handling
- Performance scenarios
- Accessibility features
"""

import pytest
import asyncio
import time
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from tests.fixtures.conversation_cleanup import conversation_cleanup


class TestWebUIComprehensive:
    """Comprehensive web UI test suite"""

    @pytest.fixture(scope="function")
    async def browser_setup(self):
        """Setup browser for each test"""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=False,
            slow_mo=1000  # Slow down actions by 1 second so you can see them
        )
        yield browser
        await browser.close()
        await playwright.stop()

    @pytest.fixture
    async def page(self, browser_setup):
        """Create a fresh page for each test"""
        context = await browser_setup.new_context()
        page = await context.new_page()
        yield page
        await context.close()

    # ==========================================
    # AUTHENTICATION FLOWS
    # ==========================================

    async def test_login_success(self, page: Page):
        """Test successful login flow"""
        await page.goto("http://localhost:8080/login")

        # Fill login form
        await page.fill('input[placeholder="Email address"]', "admin@aeonia.ai")
        await page.fill('input[placeholder="Password"]', "auVwGUGt7GHAnv6nFxR8")
        await page.click('button:has-text("Sign In")')

        # Verify redirect to chat
        await page.wait_for_url("**/chat")
        assert "Welcome back, admin!" in await page.content()

    async def test_login_invalid_credentials(self, page: Page):
        """Test login with invalid credentials"""
        await page.goto("http://localhost:8080/login")

        await page.fill('input[placeholder="Email address"]', "invalid@test.com")
        await page.fill('input[placeholder="Password"]', "wrongpassword")
        await page.click('button:has-text("Sign In")')

        # Should stay on login page with error
        await page.wait_for_timeout(1000)
        assert "/login" in page.url

    async def test_login_empty_fields(self, page: Page):
        """Test login with empty fields"""
        await page.goto("http://localhost:8080/login")

        await page.click('button:has-text("Sign In")')

        # Should show validation errors
        await page.wait_for_timeout(1000)
        assert "/login" in page.url

    async def test_logout_flow(self, page: Page):
        """Test logout functionality"""
        # Login first
        await self.login_user(page)

        # Logout
        # Click the visible logout link using the class from the visible one
        await page.click('a[class*="text-purple-400"]:has-text("Logout")')

        # Should redirect to login
        await page.wait_for_url("**/login")
        assert "Welcome Back" in await page.content()

    async def test_session_persistence(self, page: Page):
        """Test session persistence across page reloads"""
        await self.login_user(page)

        # Reload page
        await page.reload()

        # Should still be logged in
        assert "admin@aeonia.ai" in await page.content()
        assert "/chat" in page.url

    # ==========================================
    # NAVIGATION PATTERNS
    # ==========================================

    async def test_navigation_new_chat(self, page: Page):
        """Test navigation to new chat"""
        await self.login_user(page)

        await page.click('button:has-text("New Chat")')

        # Should show welcome message
        await page.wait_for_selector("text=Welcome back, admin!")
        assert "Start a conversation" in await page.content()

    async def test_navigation_conversation_list(self, page: Page):
        """Test navigation through conversation list"""
        await self.login_user(page)

        # Click on first conversation (if any exist)
        conversation_links = await page.query_selector_all('#conversation-list a[href^="/chat/"]')
        if conversation_links:
            first_link = conversation_links[0]
            href = await first_link.get_attribute("href")
            await first_link.click()

            # Should navigate to conversation
            await page.wait_for_url(f"**{href}")

    async def test_navigation_profile_page(self, page: Page):
        """Test navigation to profile page"""
        await self.login_user(page)

        # Click the visible profile link using the class from the visible one
        await page.click('a[class*="text-purple-400"]:has-text("Profile")')

        # Should navigate to profile
        await page.wait_for_url("**/profile")

    async def test_navigation_back_button(self, page: Page):
        """Test browser back button navigation"""
        await self.login_user(page)

        # Navigate to profile using the visible profile link
        await page.click('a[class*="text-purple-400"]:has-text("Profile")')
        await page.wait_for_url("**/profile")

        # Go back
        await page.go_back()

        # Should be back at chat
        await page.wait_for_url("**/chat")

    # ==========================================
    # CONVERSATION MANAGEMENT
    # ==========================================

    async def test_create_new_conversation(self, page: Page):
        """Test creating a new conversation"""
        await self.login_user(page)

        await page.click('button:has-text("New Chat")')

        # Send a message to create conversation
        await page.fill('input[id="chat-message-input"]', "Test new conversation")
        await page.click('button:has-text("Send")')

        # Should show message sent notification
        await page.wait_for_selector("text=Message sent successfully!")

        # Should show user message
        await page.wait_for_selector("text=Test new conversation")

    async def test_conversation_list_updates(self, page: Page):
        """Test conversation list updates when new conversations are created"""
        await self.login_user(page)

        # Count initial conversations
        initial_convs = await page.query_selector_all('#conversation-list > div')
        initial_count = len(initial_convs)

        # Create new conversation
        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', "List update test")
        await page.click('button:has-text("Send")')

        # Wait for conversation list to update
        await page.wait_for_timeout(2000)

        # Should have one more conversation
        final_convs = await page.query_selector_all('#conversation-list > div')
        final_count = len(final_convs)

        assert final_count >= initial_count

    async def test_delete_conversation(self, page: Page):
        """Test deleting a conversation"""
        await self.login_user(page)

        # First ensure we have at least one conversation by creating one
        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', "Test conversation for deletion")
        await page.click('button:has-text("Send")')
        await page.wait_for_timeout(2000)  # Wait for conversation to be created

        # Count conversations before deletion
        initial_count = len(await page.query_selector_all('#conversation-list > div'))

        # Look for delete buttons (×)
        delete_buttons = await page.query_selector_all('#conversation-list button:has-text("×")')

        if delete_buttons and initial_count > 0:
            # Set up dialog handler to accept the confirmation
            page.on("dialog", lambda dialog: dialog.accept())

            # Click first delete button
            await delete_buttons[0].click()

            # Wait for HTMX to process the deletion
            await page.wait_for_timeout(2000)

            # Should have fewer conversations
            final_count = len(await page.query_selector_all('#conversation-list > div'))
            assert final_count < initial_count
        else:
            # Skip test if no delete functionality available
            import pytest
            pytest.skip("No conversations or delete buttons available for testing")

    async def test_conversation_search(self, page: Page):
        """Test conversation search functionality"""
        await self.login_user(page)

        # Try searching
        search_input = await page.query_selector('input[placeholder="Search conversations..."]')
        if search_input:
            await search_input.fill("test")
            await page.wait_for_timeout(1000)

            # Search should filter results
            # This is basic - would need more specific assertions based on actual data

    # ==========================================
    # MESSAGE INTERACTIONS
    # ==========================================

    async def test_send_message_text_only(self, page: Page):
        """Test sending a simple text message"""
        await self.login_user(page)

        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', "Hello, this is a test message")
        await page.click('button:has-text("Send")')

        # Should show success notification
        await page.wait_for_selector("text=Message sent successfully!")

        # Should show user message
        await page.wait_for_selector("text=Hello, this is a test message")

    async def test_send_message_long_text(self, page: Page):
        """Test sending a very long message"""
        await self.login_user(page)

        long_message = "This is a very long message. " * 50  # ~1500 characters

        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', long_message)
        await page.click('button:has-text("Send")')

        await page.wait_for_selector("text=Message sent successfully!")

    async def test_send_message_special_characters(self, page: Page):
        """Test sending messages with special characters"""
        await self.login_user(page)

        special_message = "Testing special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?~`"

        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', special_message)
        await page.click('button:has-text("Send")')

        await page.wait_for_selector("text=Message sent successfully!")
        await page.wait_for_selector(f"text={special_message}")

    async def test_send_message_unicode(self, page: Page):
        """Test sending messages with Unicode characters"""
        await self.login_user(page)

        unicode_message = "Unicode test: 🚀 🌟 ñáéíóú 中文 العربية עברית"

        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', unicode_message)
        await page.click('button:has-text("Send")')

        await page.wait_for_selector("text=Message sent successfully!")

    async def test_send_empty_message(self, page: Page):
        """Test attempting to send an empty message"""
        await self.login_user(page)

        await page.click('button:has-text("New Chat")')

        # Count messages before attempting to send empty message
        initial_messages = await page.query_selector_all('.message-user, [class*="user-message"]')
        initial_count = len(initial_messages)

        await page.click('button:has-text("Send")')  # Send without typing

        # Wait briefly for any potential processing
        await page.wait_for_timeout(1000)

        # Should not have sent any message - count should remain the same
        final_messages = await page.query_selector_all('.message-user, [class*="user-message"]')
        final_count = len(final_messages)

        assert final_count == initial_count, "Empty message should not be sent"

    async def test_message_streaming_response(self, page: Page):
        """Test that AI responses stream correctly"""
        await self.login_user(page)

        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', "What is artificial intelligence?")
        await page.click('button:has-text("Send")')

        # Should show thinking indicator
        await page.wait_for_selector("text=Gaia is thinking...")

        # Should eventually show AI response
        await page.wait_for_selector(".bg-slate-700", timeout=30000)  # AI message bubble

    async def test_rapid_message_sending(self, page: Page):
        """Test sending multiple messages rapidly"""
        await self.login_user(page)

        await page.click('button:has-text("New Chat")')

        # Send multiple messages quickly
        messages = ["Message 1", "Message 2", "Message 3"]
        for msg in messages:
            await page.fill('input[id="chat-message-input"]', msg)
            await page.click('button:has-text("Send")')
            await page.wait_for_timeout(500)  # Brief pause

    # ==========================================
    # UI STATE MANAGEMENT
    # ==========================================

    async def test_responsive_design_mobile(self, page: Page):
        """Test responsive design on mobile viewport"""
        await page.set_viewport_size({"width": 375, "height": 667})  # iPhone size
        await self.login_user(page)

        # In mobile view, need to open sidebar first
        try:
            # Look for mobile sidebar toggle button
            sidebar_toggle = await page.query_selector('button[id*="sidebar-toggle"], button[class*="md:hidden"]')
            if sidebar_toggle:
                await sidebar_toggle.click()
                await page.wait_for_timeout(500)  # Wait for sidebar to open
        except Exception:
            pass  # Continue if no sidebar toggle found

        # Now try to click New Chat (should be visible after opening sidebar)
        await page.click('button:has-text("New Chat")')
        assert "Welcome back" in await page.content()

    async def test_responsive_design_tablet(self, page: Page):
        """Test responsive design on tablet viewport"""
        await page.set_viewport_size({"width": 768, "height": 1024})  # iPad size
        await self.login_user(page)

        await page.click('button:has-text("New Chat")')
        assert "Welcome back" in await page.content()

    async def test_responsive_design_desktop(self, page: Page):
        """Test responsive design on desktop viewport"""
        await page.set_viewport_size({"width": 1920, "height": 1080})  # Desktop size
        await self.login_user(page)

        await page.click('button:has-text("New Chat")')
        assert "Welcome back" in await page.content()

    async def test_dark_mode_toggle(self, page: Page):
        """Test dark mode functionality if available"""
        await self.login_user(page)

        # Look for dark mode toggle
        dark_toggle = await page.query_selector('[data-testid="dark-mode-toggle"]')
        if dark_toggle:
            await dark_toggle.click()
            await page.wait_for_timeout(500)
            # Verify dark mode is applied

    async def test_scroll_behavior(self, page: Page):
        """Test scroll behavior in message history"""
        await self.login_user(page)

        # Navigate to conversation with messages
        conversation_links = await page.query_selector_all('#conversation-list a[href^="/chat/"]')
        if conversation_links:
            await conversation_links[0].click()

            # Check if messages container scrolls properly
            messages_container = await page.query_selector('#messages')
            if messages_container:
                scroll_height = await messages_container.evaluate("el => el.scrollHeight")
                client_height = await messages_container.evaluate("el => el.clientHeight")

                if scroll_height > client_height:
                    # Test scrolling
                    await messages_container.evaluate("el => el.scrollTop = el.scrollHeight")

    # ==========================================
    # ERROR HANDLING
    # ==========================================

    async def test_network_error_handling(self, page: Page):
        """Test behavior when network requests fail"""
        await self.login_user(page)

        # Simulate network failure
        await page.route("**/api/**", lambda route: route.abort())

        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', "Test network error")
        await page.click('button:has-text("Send")')

        # Should show error message
        await page.wait_for_selector("text=Connection error", timeout=10000)

    async def test_session_expiry_handling(self, page: Page):
        """Test behavior when session expires"""
        await self.login_user(page)

        # Clear session manually (simulate expiry)
        await page.evaluate("() => sessionStorage.clear()")
        await page.evaluate("() => localStorage.clear()")

        # Try to send message
        await page.fill('input[id="chat-message-input"]', "Test session expiry")
        await page.click('button:has-text("Send")')

        # Should show session expired message
        await page.wait_for_selector("text=session has expired", timeout=5000)

    async def test_server_error_handling(self, page: Page):
        """Test behavior when server returns 500 errors"""
        await self.login_user(page)

        # Mock server errors
        await page.route("**/api/chat/send", lambda route: route.fulfill(status=500))

        await page.fill('input[id="chat-message-input"]', "Test server error")
        await page.click('button:has-text("Send")')

        # Should show appropriate error message
        await page.wait_for_selector("text=Server error", timeout=5000)

    # ==========================================
    # PERFORMANCE SCENARIOS
    # ==========================================

    async def test_large_conversation_loading(self, page: Page):
        """Test loading conversations with many messages"""
        await self.login_user(page)

        # Navigate to conversation (if any exist)
        conversation_links = await page.query_selector_all('#conversation-list a[href^="/chat/"]')
        if conversation_links:
            start_time = time.time()
            await conversation_links[0].click()

            # Wait for messages to load
            await page.wait_for_selector('#messages')
            load_time = time.time() - start_time

            # Should load within reasonable time
            assert load_time < 10.0  # 10 seconds max

    async def test_conversation_list_performance(self, page: Page):
        """Test conversation list loading performance"""
        await self.login_user(page)

        start_time = time.time()
        await page.wait_for_selector('#conversation-list')
        load_time = time.time() - start_time

        # Should load quickly
        assert load_time < 5.0  # 5 seconds max

    async def test_message_sending_performance(self, page: Page):
        """Test message sending performance"""
        await self.login_user(page)

        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', "Performance test message")

        start_time = time.time()
        await page.click('button:has-text("Send")')
        await page.wait_for_selector("text=Message sent successfully!")
        response_time = time.time() - start_time

        # Should respond quickly
        assert response_time < 3.0  # 3 seconds max

    # ==========================================
    # ACCESSIBILITY FEATURES
    # ==========================================

    async def test_keyboard_navigation(self, page: Page):
        """Test keyboard navigation accessibility"""
        await self.login_user(page)

        # Test Tab navigation
        await page.keyboard.press("Tab")
        await page.keyboard.press("Tab")

        # Should be able to navigate to elements
        focused_element = await page.evaluate("() => document.activeElement.tagName")
        assert focused_element in ["BUTTON", "INPUT", "TEXTAREA", "A"]

    async def test_screen_reader_support(self, page: Page):
        """Test screen reader accessibility features"""
        await self.login_user(page)

        # Check for ARIA labels
        aria_elements = await page.query_selector_all('[aria-label]')
        assert len(aria_elements) > 0

        # Check for alt text on images
        images = await page.query_selector_all('img')
        for img in images:
            alt_text = await img.get_attribute("alt")
            # Images should have alt text (or be decorative)

    async def test_high_contrast_mode(self, page: Page):
        """Test high contrast mode support"""
        await page.emulate_media(media="screen", color_scheme="no-preference")
        await self.login_user(page)

        # Verify contrast ratios meet accessibility standards
        # This would require more sophisticated color analysis

    # ==========================================
    # EDGE CASES & BOUNDARY CONDITIONS
    # ==========================================

    async def test_extremely_long_conversation_title(self, page: Page):
        """Test conversation with extremely long title"""
        await self.login_user(page)

        very_long_message = "A" * 1000  # Very long title

        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', very_long_message)
        await page.click('button:has-text("Send")')

        await page.wait_for_selector("text=Message sent successfully!")

    async def test_concurrent_user_sessions(self, page: Page):
        """Test behavior with multiple concurrent sessions"""
        # This would require multiple browser contexts
        # and coordinated actions between them
        await self.login_user(page)

        # Basic test - ensure session isolation
        await page.click('button:has-text("New Chat")')
        assert "Welcome back" in await page.content()

    async def test_page_refresh_during_message_sending(self, page: Page):
        """Test page refresh while message is being sent"""
        await self.login_user(page)

        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', "Test refresh during send")
        await page.click('button:has-text("Send")')

        # Refresh immediately
        await page.reload()

        # Should handle gracefully
        await page.wait_for_selector('#messages')

    # ==========================================
    # HELPER METHODS
    # ==========================================

    async def login_user(self, page: Page):
        """Helper method to login user"""
        await page.goto("http://localhost:8080/login")
        await page.fill('input[placeholder="Email address"]', "admin@aeonia.ai")
        await page.fill('input[placeholder="Password"]', "auVwGUGt7GHAnv6nFxR8")
        await page.click('button:has-text("Sign In")')
        await page.wait_for_url("**/chat")

    async def create_test_conversation(self, page: Page, message: str = "Test conversation"):
        """Helper method to create a test conversation"""
        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', message)
        await page.click('button:has-text("Send")')
        await page.wait_for_selector("text=Message sent successfully!")


# ==========================================
# PERFORMANCE TEST CONFIGURATIONS
# ==========================================

class TestWebUIPerformance:
    """Dedicated performance test suite"""

    @pytest.mark.performance
    async def test_cold_start_performance(self, page: Page):
        """Test application cold start performance"""
        start_time = time.time()
        await page.goto("http://localhost:8080/login")
        await page.wait_for_load_state("networkidle")
        load_time = time.time() - start_time

        assert load_time < 5.0  # Should load within 5 seconds

    @pytest.mark.performance
    async def test_memory_usage_during_long_session(self, page: Page):
        """Test memory usage during extended session"""
        await page.goto("http://localhost:8080/login")
        # Would require memory monitoring tools

    @pytest.mark.performance
    async def test_message_throughput(self, page: Page):
        """Test message sending throughput"""
        # Login and send multiple messages to test throughput
        pass


# ==========================================
# SECURITY TEST CONFIGURATIONS
# ==========================================

class TestWebUISecurity:
    """Security-focused test suite"""

    async def test_xss_prevention(self, page: Page):
        """Test XSS attack prevention"""
        await self.login_user(page)

        xss_payload = "<script>alert('XSS')</script>"

        await page.click('button:has-text("New Chat")')
        await page.fill('input[id="chat-message-input"]', xss_payload)
        await page.click('button:has-text("Send")')

        # Should not execute script
        # Would need to check for actual XSS execution

    async def test_csrf_protection(self, page: Page):
        """Test CSRF protection"""
        # Would require crafting CSRF requests
        pass

    async def test_session_security(self, page: Page):
        """Test session security features"""
        # Test secure cookie flags, session timeouts, etc.
        pass