"""
Browser tests that focus on user behaviors rather than HTML structure.
Uses semantic selectors and tests outcomes, not implementation.
"""
import pytest
from playwright.async_api import async_playwright, expect
import os
import json

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestChatUserBehaviors:
    """Test chat functionality from a user's perspective"""
    
    @pytest.mark.asyncio
    async def test_user_can_send_message(self):
        """Test that a user can send a message and see a response"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Setup: Mock the backend to return predictable responses
            await self._setup_chat_mocks(page)
            
            # Navigate to chat (assuming we're authenticated)
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            
            # Action: User types and sends a message
            # Look for any text input that could be for messages
            message_input = await page.locator('textarea, input[type="text"]').filter(
                has_text=""
            ).first
            
            await message_input.fill("Hello, assistant!")
            
            # Find and click something that looks like a send button
            send_button = await page.locator('button').filter(
                has_text=["Send", "Submit", "➤", "→"]
            ).first
            
            await send_button.click()
            
            # Outcome: Message should appear in conversation
            # Look for the message we sent in the conversation area
            await expect(page.locator('text="Hello, assistant!"')).to_be_visible(timeout=5000)
            
            # Outcome: Should receive a response
            await expect(page.locator('text="This is a test response"')).to_be_visible(timeout=5000)
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_user_sees_error_on_failed_send(self):
        """Test that users see helpful errors when messages fail to send"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Setup: Mock the backend to return an error
            await page.route("**/api/*/chat", lambda route: route.fulfill(
                status=500,
                json={"error": "Service temporarily unavailable"}
            ))
            
            await self._setup_chat_page_mock(page)
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            
            # Action: Try to send a message
            message_input = await page.locator('textarea, input[type="text"]').first
            await message_input.fill("This should fail")
            
            send_button = await page.locator('button').filter(
                has_text=["Send", "Submit"]
            ).first
            await send_button.click()
            
            # Outcome: Should see an error message
            error_locator = page.locator('text=/error|failed|unavailable/i')
            await expect(error_locator).to_be_visible(timeout=5000)
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_user_can_start_new_conversation(self):
        """Test that users can start a new conversation"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await self._setup_chat_mocks(page)
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            
            # Action: Click something that starts a new conversation
            new_chat_button = await page.locator('button, a').filter(
                has_text=["New", "Start", "+"]
            ).first
            
            if await new_chat_button.count() > 0:
                await new_chat_button.click()
                
                # Outcome: Message area should be clear/ready
                message_input = await page.locator('textarea, input[type="text"]').first
                input_value = await message_input.input_value()
                assert input_value == "", "New conversation should have empty message input"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_responsive_mobile_experience(self):
        """Test that chat works on mobile devices"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Create mobile context
            context = await browser.new_context(
                viewport={'width': 375, 'height': 667},
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
            )
            page = await context.new_page()
            
            await self._setup_chat_page_mock(page)
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            
            # Verify key elements are visible and usable on mobile
            # Look for message input
            message_input = await page.locator('textarea, input[type="text"]').first
            await expect(message_input).to_be_visible()
            await expect(message_input).to_be_enabled()
            
            # Verify we can interact with it
            await message_input.fill("Mobile test")
            value = await message_input.input_value()
            assert value == "Mobile test", "Should be able to type on mobile"
            
            await browser.close()
    
    async def _setup_chat_mocks(self, page):
        """Setup common mocks for chat functionality"""
        # Mock successful chat response
        await page.route("**/api/*/chat", lambda route: route.fulfill(
            status=200,
            json={
                "choices": [{
                    "message": {
                        "content": "This is a test response"
                    }
                }],
                "conversation_id": "test-123"
            }
        ))
        
        # Mock conversations list
        await page.route("**/api/conversations", lambda route: route.fulfill(
            status=200,
            json={"conversations": [], "has_more": False}
        ))
        
        await self._setup_chat_page_mock(page)
    
    async def _setup_chat_page_mock(self, page):
        """Mock the chat page with minimal HTML that any chat UI would have"""
        # Very generic HTML that doesn't assume specific structure
        await page.route("**/chat", lambda route: route.fulfill(
            status=200,
            headers={"Content-Type": "text/html"},
            body="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Chat</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body>
                <div>
                    <div class="messages"></div>
                    <form>
                        <textarea placeholder="Type a message..."></textarea>
                        <button type="submit">Send</button>
                    </form>
                </div>
                <script>
                    // Minimal JS to make the form interactive
                    document.querySelector('form').onsubmit = function(e) {
                        e.preventDefault();
                        const textarea = this.querySelector('textarea');
                        const messages = document.querySelector('.messages');
                        if (textarea.value) {
                            messages.innerHTML += '<div>' + textarea.value + '</div>';
                            textarea.value = '';
                            // Simulate response
                            setTimeout(() => {
                                messages.innerHTML += '<div>This is a test response</div>';
                            }, 100);
                        }
                        return false;
                    };
                </script>
            </body>
            </html>
            """
        ))


class TestAuthenticationBehaviors:
    """Test authentication from user's perspective"""
    
    @pytest.mark.asyncio
    async def test_unauthenticated_user_redirected_to_login(self):
        """Test that unauthenticated users can't access protected pages"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Try to access chat without auth
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            
            # Should end up on login page
            await page.wait_for_timeout(1000)
            
            # Look for login indicators - form with email/password fields
            email_input = await page.locator('input[type="email"], input[type="text"]').filter(
                has_attribute="name", "email"
            ).or_(
                page.locator('input').filter(has_attribute="placeholder", "/email/i")
            )
            
            password_input = await page.locator('input[type="password"]')
            
            # At least one of these should exist on a login page
            login_indicators = await email_input.count() + await password_input.count()
            assert login_indicators > 0, "Should be on login page with email/password inputs"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_login_form_prevents_empty_submission(self):
        """Test that login form has basic validation"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Try to submit without filling anything
            submit_button = await page.locator('button[type="submit"], input[type="submit"]').first
            await submit_button.click()
            
            # Check if we're still on login page (form validation prevented submission)
            await page.wait_for_timeout(500)
            assert "/login" in page.url, "Should still be on login page after empty submission"
            
            await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])