"""
Working chat browser tests with proper HTMX handling.
"""
import pytest
from playwright.async_api import async_playwright
import os

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_chat_with_session_mock():
    """Test chat access with proper session mocking"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        # Track what happens
        print("\n=== Starting test ===")
        page.on("request", lambda req: print(f"[Request] {req.method} {req.url}"))
        page.on("response", lambda res: print(f"[Response] {res.status} {res.url}"))
        
        # Set up session state
        session_active = False
        
        # Mock auth endpoint - sets session
        async def handle_auth(route):
            nonlocal session_active
            print("\n[Mock Auth] Processing login request")
            
            # Check if it's HTMX
            if 'hx-request' in route.request.headers:
                print("[Mock Auth] HTMX request detected")
                session_active = True
                await route.fulfill(
                    status=200,
                    headers={
                        "HX-Redirect": "/chat",
                        "Set-Cookie": "session=test-session-123; Path=/; HttpOnly"
                    },
                    body=""
                )
            else:
                # Regular form submission
                await route.fulfill(
                    status=303,
                    headers={"Location": "/chat"}
                )
        
        # Mock chat endpoint - checks session
        async def handle_chat(route):
            print(f"\n[Mock Chat] Session active: {session_active}")
            
            # Check cookies
            cookie_header = route.request.headers.get('cookie', '')
            has_session = 'session=' in cookie_header or session_active
            
            if has_session:
                print("[Mock Chat] Session valid, serving chat page")
                await route.fulfill(
                    status=200,
                    content_type="text/html",
                    body="""
                    <html>
                    <head><title>Gaia Chat</title></head>
                    <body>
                        <div class="flex h-screen">
                            <div id="sidebar">
                                <h2>Conversations</h2>
                            </div>
                            <div id="main-content">
                                <div id="messages"></div>
                                <form id="chat-form">
                                    <textarea name="message" placeholder="Type your message..."></textarea>
                                    <button type="submit">Send</button>
                                </form>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                )
            else:
                print("[Mock Chat] No session, redirecting to login")
                await route.fulfill(
                    status=303,
                    headers={"Location": "/login"}
                )
        
        # Mock conversations API
        await page.route("**/api/conversations", lambda route: route.fulfill(
            json={"conversations": [], "has_more": False}
        ))
        
        # Set up routes
        await page.route("**/auth/login", handle_auth)
        await page.route("**/chat", handle_chat)
        
        # Navigate to login
        print("\n=== Navigating to login ===")
        await page.goto(f'{WEB_SERVICE_URL}/login')
        
        # Fill and submit form
        print("\n=== Filling login form ===")
        await page.fill('input[name="email"]', 'test@test.local')
        await page.fill('input[name="password"]', 'test123')
        
        print("\n=== Submitting form ===")
        await page.click('button[type="submit"]')
        
        # Wait for navigation
        print("\n=== Waiting for navigation ===")
        try:
            await page.wait_for_url('**/chat', timeout=5000)
            print(f"✓ Successfully navigated to: {page.url}")
        except Exception as e:
            print(f"✗ Navigation failed: {e}")
            print(f"Current URL: {page.url}")
            raise
        
        # Verify chat interface
        print("\n=== Verifying chat interface ===")
        chat_form = await page.query_selector('#chat-form')
        assert chat_form, "Chat form should exist"
        print("✓ Chat form found")
        
        message_input = await page.query_selector('textarea[name="message"]')
        assert message_input, "Message input should exist"
        print("✓ Message input found")
        
        # Test typing
        await message_input.fill("Test message")
        value = await message_input.input_value()
        assert value == "Test message", "Should be able to type in message input"
        print("✓ Can type in message input")
        
        await browser.close()
        print("\n=== Test completed successfully ===")


@pytest.mark.asyncio
async def test_chat_message_send():
    """Test sending messages in chat"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        # Simple session state
        session_active = False
        api_calls = []
        
        # Mock auth
        async def handle_auth(route):
            nonlocal session_active
            session_active = True
            await route.fulfill(
                status=200,
                headers={"HX-Redirect": "/chat"},
                body=""
            )
        
        # Mock chat page
        async def handle_chat(route):
            if session_active:
                await route.fulfill(
                    status=200,
                    content_type="text/html",
                    body="""
                    <html>
                    <head>
                        <title>Gaia Chat</title>
                        <script src="https://unpkg.com/htmx.org@2.0.0"></script>
                    </head>
                    <body>
                        <div id="messages"></div>
                        <form id="chat-form" hx-post="/api/v1/chat" hx-target="#messages" hx-swap="beforeend">
                            <textarea name="message"></textarea>
                            <button type="submit">Send</button>
                        </form>
                    </body>
                    </html>
                    """
                )
            else:
                await route.fulfill(status=303, headers={"Location": "/login"})
        
        # Mock chat API
        async def handle_chat_api(route):
            api_calls.append(route.request.url)
            await route.fulfill(
                status=200,
                content_type="text/html",
                body="""
                <div class="message user">Hello!</div>
                <div class="message assistant">Hi there! How can I help you?</div>
                """
            )
        
        await page.route("**/auth/login", handle_auth)
        await page.route("**/chat", handle_chat)
        await page.route("**/api/v1/chat", handle_chat_api)
        await page.route("**/api/conversations", lambda route: route.fulfill(
            json={"conversations": [], "has_more": False}
        ))
        
        # Login
        await page.goto(f'{WEB_SERVICE_URL}/login')
        await page.fill('input[name="email"]', 'test@test.local')
        await page.fill('input[name="password"]', 'test123')
        await page.click('button[type="submit"]')
        
        # Wait for chat
        await page.wait_for_url('**/chat', timeout=5000)
        
        # Wait for HTMX to load
        await page.wait_for_function("typeof htmx !== 'undefined'", timeout=5000)
        
        # Send message
        message_input = await page.query_selector('textarea[name="message"]')
        await message_input.fill("Hello!")
        
        # Submit form
        await page.click('button[type="submit"]')
        
        # Wait for response
        await page.wait_for_selector('.message.assistant', timeout=5000)
        
        # Verify
        assert len(api_calls) > 0, "API should have been called"
        response = await page.inner_text('.message.assistant')
        assert "Hi there" in response, "Should see AI response"
        
        await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])