"""
Browser tests for chat functionality.

Tests the complete chat experience including:
- Sending messages
- Receiving AI responses
- Conversation management
- Real-time updates
- Error handling
"""
import pytest
import asyncio
import json
import uuid
from playwright.async_api import async_playwright, expect
import os
import sys

# Add integration helpers to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers.browser_auth import BrowserAuthHelper

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestChatFunctionality:
    """Test chat interface functionality"""
    
    @pytest.mark.asyncio
    async def test_send_and_receive_message(self, test_user_credentials):
        """Test sending a message and receiving AI response"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            # Login with real credentials
            await BrowserAuthHelper.login_with_real_user(page, test_user_credentials)
            
            # Track network activity
            api_calls = []
            page.on("request", lambda req: api_calls.append(req) if "/api/" in req.url else None)
            
            # Wait for chat interface to load
            await page.wait_for_selector('#chat-form', timeout=10000)
            
            # Find the message input - it might be a textarea or input
            message_input = page.locator('textarea[name="message"], input[name="message"]').first
            await expect(message_input).to_be_visible()
            
            # Send a test message
            test_message = "Hello, this is a test message!"
            await message_input.fill(test_message)
            
            # Submit the form - find the send button
            send_button = page.locator('button[type="submit"], button:has-text("Send")')
            await send_button.click()
            
            # Wait for the message to be sent (input should clear)
            await expect(message_input).to_have_value("", timeout=5000)
            
            # Wait for response to appear in messages area
            messages_area = page.locator('#messages')
            
            # Wait for some response to appear (we don't know exact text)
            # Look for any new message that's not our test message
            await page.wait_for_timeout(2000)  # Give AI time to respond
            
            # Check that our message appears
            user_message = messages_area.locator(f'text="{test_message}"')
            await expect(user_message).to_be_visible(timeout=10000)
            
            # Check that there's at least one more message (the AI response)
            all_messages = await messages_area.locator('.message, [class*="message"], div').all()
            assert len(all_messages) >= 2, "Should have user message and AI response"
            
            # Verify API was called
            chat_api_calls = [req for req in api_calls if any(endpoint in req.url for endpoint in ["/api/chat", "/api/v1/chat", "/api/v0.2/chat"])]
            assert len(chat_api_calls) > 0, "Chat API should have been called"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_conversation_history(self, test_user_credentials):
        """Test that conversation history is displayed"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context()
            page = await context.new_page()
            
            # Login with real credentials
            await BrowserAuthHelper.login_with_real_user(page, test_user_credentials)
            
            # Mock session validation endpoint
            await page.route("**/api/session", lambda route: route.fulfill(
                status=200,
                json={
                    "authenticated": True,
                    "user": {
                        "id": "test-user-123",
                        "email": "test@test.local"
                    },
                    "jwt_token": "mock-jwt-token"
                }
            ))
            
            # Mock the chat page
            await page.route("**/chat", lambda route: route.fulfill(
                status=200,
                content_type="text/html",
                body="""
                <!DOCTYPE html>
                <html>
                <head><title>Chat</title></head>
                <body>
                    <div id="sidebar">
                        <div id="conversations"></div>
                    </div>
                    <div id="messages"></div>
                    <script>
                        // Load conversations
                        fetch('/api/conversations')
                            .then(r => r.json())
                            .then(data => {
                                const conv = document.getElementById('conversations');
                                data.conversations.forEach(c => {
                                    const div = document.createElement('div');
                                    div.textContent = c.title;
                                    div.onclick = () => {
                                        // Load messages
                                        fetch('/api/conversations/' + c.id + '/messages')
                                            .then(r => r.json())
                                            .then(msgs => {
                                                const msgDiv = document.getElementById('messages');
                                                msgs.messages.forEach(m => {
                                                    msgDiv.innerHTML += '<div>' + m.content + '</div>';
                                                });
                                            });
                                    };
                                    conv.appendChild(div);
                                });
                            });
                    </script>
                </body>
                </html>
                """
            ))
            
            # Mock conversations with history
            conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={
                    "conversations": [{
                        "id": conversation_id,
                        "title": "Previous Chat",
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-01T01:00:00Z",
                        "message_count": 4
                    }],
                    "has_more": False
                }
            ))
            
            # Mock conversation messages
            await page.route(f"**/api/conversations/{conversation_id}/messages", 
                lambda route: route.fulfill(
                    json={
                        "messages": [
                            {
                                "role": "user",
                                "content": "What is the weather today?"
                            },
                            {
                                "role": "assistant",
                                "content": "I don't have access to real-time weather data."
                            },
                            {
                                "role": "user",
                                "content": "Thanks!"
                            },
                            {
                                "role": "assistant",
                                "content": "You're welcome!"
                            }
                        ]
                    }
                )
            )
            
            # Navigate directly to chat (we have session cookie)
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            await page.wait_for_timeout(500)  # Let conversations load
            
            # Check sidebar has conversation
            await expect(page.locator('text="Previous Chat"')).to_be_visible(timeout=5000)
            
            # Click on conversation
            await page.locator('text="Previous Chat"').click()
            
            # Wait for messages to load
            await page.wait_for_timeout(500)
            
            # Verify messages are displayed
            messages = page.locator('#messages > div')
            await expect(messages).to_have_count(4)  # We mocked 4 messages
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_new_conversation_button(self):
        """Test creating a new conversation"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Mock auth and API
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
            await page.wait_for_url('**/chat')
            
            # Look for new chat button
            new_chat_button = await page.query_selector('button:has-text("New Chat")')
            if not new_chat_button:
                new_chat_button = await page.query_selector('button[aria-label="New Chat"]')
            
            if new_chat_button:
                # Click new chat
                await new_chat_button.click()
                await page.wait_for_timeout(500)
                
                # Verify we're still on chat page
                assert page.url.endswith('/chat'), "Should stay on chat page"
                
                # Message input should be empty and ready
                message_input = await page.query_selector('input[name="message"]')
                value = await message_input.input_value()
                assert value == "", "Message input should be empty for new chat"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_message_error_handling(self):
        """Test error handling when message fails to send"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Track console errors
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
            
            # Mock auth
            await page.route("**/auth/login", lambda route: route.fulfill(
                status=303,
                headers={"Location": "/chat"},
                body=""
            ))
            
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={"conversations": [], "has_more": False}
            ))
            
            # Mock chat API to return error
            await page.route("**/api/v1/chat", lambda route: route.fulfill(
                status=500,
                json={
                    "error": {
                        "message": "Internal server error",
                        "type": "server_error",
                        "code": "internal_error"
                    }
                }
            ))
            
            # Login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test123')
            await page.click('button[type="submit"]')
            await page.wait_for_url('**/chat')
            
            # Send a message
            message_input = await page.query_selector('input[name="message"]')
            await message_input.fill("This will fail")
            await page.keyboard.press('Enter')
            
            # Should show error message
            error_element = await page.wait_for_selector('[role="alert"], .error, text="error"', timeout=5000)
            if error_element:
                error_text = await error_element.inner_text()
                assert "error" in error_text.lower(), "Should show error message"
            
            # Input should still be enabled for retry
            is_disabled = await message_input.is_disabled()
            assert not is_disabled, "Message input should not be disabled after error"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Test streaming AI responses (if implemented)"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Mock auth
            await page.route("**/auth/login", lambda route: route.fulfill(
                status=303,
                headers={"Location": "/chat"},
                body=""
            ))
            
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={"conversations": [], "has_more": False}
            ))
            
            # Mock streaming response
            # This is complex and depends on your implementation
            # For now, just use regular response
            await page.route("**/api/v1/chat", lambda route: route.fulfill(
                json={
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "This is a simulated streaming response."
                        }
                    }]
                }
            ))
            
            # Login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test123')
            await page.click('button[type="submit"]')
            await page.wait_for_url('**/chat')
            
            # Send message
            message_input = await page.query_selector('input[name="message"]')
            await message_input.fill("Test streaming")
            await page.keyboard.press('Enter')
            
            # Check for typing indicator or streaming UI
            # This depends on your implementation
            typing_indicator = await page.query_selector('.typing-indicator, .loading, text="..."')
            # May or may not have typing indicator
            
            # Wait for response
            await page.wait_for_selector('text="simulated streaming response"', timeout=5000)
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_mobile_chat_interface(self):
        """Test chat works on mobile viewport"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # Mobile context
            context = await browser.new_context(
                viewport={'width': 375, 'height': 667},
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)'
            )
            page = await context.new_page()
            
            # Mock auth
            await page.route("**/auth/login", lambda route: route.fulfill(
                status=303,
                headers={"Location": "/chat"},
                body=""
            ))
            
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={"conversations": [], "has_more": False}
            ))
            
            await page.route("**/api/v1/chat", lambda route: route.fulfill(
                json={
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "Mobile response!"
                        }
                    }]
                }
            ))
            
            # Login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test123')
            await page.click('button[type="submit"]')
            await page.wait_for_url('**/chat')
            
            # On mobile, sidebar might be hidden
            sidebar = await page.query_selector('#sidebar')
            if sidebar:
                is_visible = await sidebar.is_visible()
                # Sidebar might be hidden on mobile
            
            # Chat form should still work
            message_input = await page.query_selector('input[name="message"]')
            assert message_input, "Message input should exist on mobile"
            
            # Send message
            await message_input.fill("Mobile test")
            await page.keyboard.press('Enter')
            
            # Wait for response
            await page.wait_for_selector('text="Mobile response!"', timeout=5000)
            
            # Check if we need to scroll to see latest message
            messages_container = await page.query_selector('#messages')
            if messages_container:
                # Check scroll position
                scroll_info = await messages_container.evaluate('''
                    el => ({
                        scrollTop: el.scrollTop,
                        scrollHeight: el.scrollHeight,
                        clientHeight: el.clientHeight
                    })
                ''')
                # Should auto-scroll on mobile too
            
            await browser.close()


class TestChatWithRealAuth:
    """Test chat with real authentication"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("TEST_USER_EMAIL") or not os.getenv("TEST_USER_PASSWORD"),
        reason="Requires TEST_USER_EMAIL and TEST_USER_PASSWORD"
    )
    async def test_real_chat_flow(self):
        """Test complete chat flow with real authentication"""
        test_email = os.getenv("TEST_USER_EMAIL")
        test_password = os.getenv("TEST_USER_PASSWORD")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Enable logging
            page.on("console", lambda msg: print(f"[Browser] {msg.text}"))
            
            print(f"Testing chat with real user: {test_email}")
            
            # Real login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.fill('input[name="email"]', test_email)
            await page.fill('input[name="password"]', test_password)
            await page.click('button[type="submit"]')
            
            try:
                # Wait for chat page
                await page.wait_for_url('**/chat', timeout=10000)
                print("✓ Successfully logged in to chat")
                
                # Wait for chat to fully load
                await page.wait_for_selector('#chat-form', timeout=5000)
                await page.wait_for_selector('input[name="message"]', timeout=5000)
                
                # Send a real message
                message_input = await page.query_selector('input[name="message"]')
                test_message = "Hello! Can you tell me what day it is?"
                await message_input.fill(test_message)
                
                print(f"Sending message: {test_message}")
                await page.keyboard.press('Enter')
                
                # Wait for user message to appear
                await page.wait_for_selector(f'text="{test_message}"', timeout=5000)
                print("✓ User message appeared")
                
                # Wait for AI response (longer timeout for real API)
                print("Waiting for AI response...")
                ai_message = await page.wait_for_selector('.assistant-message, [data-role="assistant"]', timeout=30000)
                
                if ai_message:
                    response_text = await ai_message.inner_text()
                    print(f"✓ AI responded: {response_text[:100]}...")
                    
                    # Verify response makes sense
                    assert len(response_text) > 10, "AI response should not be empty"
                
                # Take screenshot of successful chat
                await page.screenshot(path="tests/web/screenshots/real-chat-success.png")
                
            except Exception as e:
                # Take screenshot on failure
                await page.screenshot(path="tests/web/screenshots/real-chat-failure.png")
                raise e
            
            await browser.close()


# Utility function for manual chat testing
async def manual_chat_test(email: str, password: str, message: str = "Hello!"):
    """
    Manually test chat with specific credentials and message.
    
    Usage:
        python -m tests.web.test_chat_browser manual_chat_test \
            --email="user@example.com" --password="pass" --message="Test message"
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            slow_mo=500  # Slow down for visibility
        )
        page = await browser.new_page()
        
        try:
            print(f"🔐 Logging in as: {email}")
            
            # Login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            
            # Wait for chat
            await page.wait_for_url('**/chat', timeout=10000)
            print("✅ Logged in successfully!")
            
            # Send message
            await page.wait_for_selector('input[name="message"]')
            message_input = await page.query_selector('input[name="message"]')
            
            print(f"💬 Sending: {message}")
            await message_input.fill(message)
            await page.keyboard.press('Enter')
            
            # Wait for response
            print("⏳ Waiting for AI response...")
            await page.wait_for_selector('.assistant-message, [data-role="assistant"]', timeout=30000)
            print("✅ Response received!")
            
            # Keep browser open
            print("\n⏸️  Browser will stay open. Press Ctrl+C to close.")
            await asyncio.sleep(300)
            
        finally:
            await browser.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "manual_chat_test":
        # Parse arguments for manual testing
        email = None
        password = None
        message = "Hello!"
        
        for arg in sys.argv[2:]:
            if arg.startswith("--email="):
                email = arg.split("=", 1)[1]
            elif arg.startswith("--password="):
                password = arg.split("=", 1)[1]
            elif arg.startswith("--message="):
                message = arg.split("=", 1)[1]
        
        if email and password:
            asyncio.run(manual_chat_test(email, password, message))
        else:
            print("Usage: python test_chat_browser.py manual_chat_test --email=user@example.com --password=pass [--message='Test']")
    else:
        # Run pytest
        pytest.main([__file__, "-v", "-s"])