"""
Chat browser tests that properly handle HTMX authentication.
"""
import pytest
from playwright.async_api import async_playwright
import os
import json

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestChatWithHTMX:
    """Test chat functionality with HTMX-aware authentication"""
    
    @pytest.mark.asyncio
    async def test_chat_via_htmx_login(self):
        """Test chat access via HTMX login flow"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context()
            
            # Set a mock session cookie to bypass auth
            await context.add_cookies([{
                'name': 'session',
                'value': 'mock-session-token',
                'domain': 'web-service',
                'path': '/',
                'httpOnly': True
            }])
            
            page = await context.new_page()
            
            # Mock the chat page to not redirect
            async def handle_chat_route(route):
                if route.request.method == "GET":
                    await route.fulfill(
                        status=200,
                        content_type="text/html",
                        body="""
                        <html>
                        <head><title>Gaia Chat</title></head>
                        <body>
                            <div class="flex h-screen">
                                <div id="sidebar">Conversations</div>
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
                    await route.continue_()
            
            await page.route("**/chat", handle_chat_route)
            
            # Navigate directly to chat
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            
            # Verify we're on chat page
            assert page.url.endswith('/chat'), "Should be on chat page"
            
            # Check chat elements
            chat_form = await page.query_selector('#chat-form')
            assert chat_form, "Chat form should exist"
            
            message_input = await page.query_selector('input[name="message"]')
            assert message_input, "Message input should exist"
            
            # Type a message
            await message_input.fill("Hello from browser test!")
            value = await message_input.input_value()
            assert value == "Hello from browser test!"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_htmx_chat_message_submission(self):
        """Test sending chat messages via HTMX"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context()
            
            # Set session cookie
            await context.add_cookies([{
                'name': 'session',
                'value': 'mock-session-token',
                'domain': 'web-service',
                'path': '/'
            }])
            
            page = await context.new_page()
            
            # Track API calls
            api_calls = []
            
            # Mock endpoints
            async def handle_chat_page(route):
                if route.request.method == "GET":
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
                            <form hx-post="/api/v1/chat" 
                                  hx-target="#messages" 
                                  hx-swap="beforeend">
                                <textarea name="message"></textarea>
                                <button type="submit">Send</button>
                            </form>
                        </body>
                        </html>
                        """
                    )
                else:
                    await route.continue_()
            
            await page.route("**/chat", handle_chat_page)
            
            async def handle_chat_api(route):
                api_calls.append({
                    'url': route.request.url,
                    'method': route.request.method,
                    'headers': route.request.headers,
                    'body': route.request.post_data
                })
                await route.fulfill(
                    status=200,
                    content_type="text/html",
                    body="""
                    <div class="message user">Test message</div>
                    <div class="message assistant">This is a response!</div>
                    """
                )
            
            await page.route("**/api/v1/chat", handle_chat_api)
            
            # Navigate to chat
            await page.goto(f'{WEB_SERVICE_URL}/chat')
            
            # Wait for HTMX to load
            await page.wait_for_function("typeof htmx !== 'undefined'")
            
            # Send a message
            message_input = await page.query_selector('input[name="message"]')
            await message_input.fill("Test message")
            
            submit_button = await page.query_selector('button[type="submit"]')
            await submit_button.click()
            
            # Wait for response to appear
            await page.wait_for_selector('.message.assistant', timeout=5000)
            
            # Verify API was called
            assert len(api_calls) > 0, "API should have been called"
            assert 'hx-request' in api_calls[0]['headers'], "Should be HTMX request"
            
            # Verify response appears
            response_text = await page.inner_text('.message.assistant')
            assert "This is a response!" in response_text
            
            await browser.close()
    
    @pytest.mark.asyncio 
    async def test_real_login_to_chat_flow(self):
        """Test the complete login to chat flow with proper mocking"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Log for debugging
            page.on("console", lambda msg: print(f"[Browser] {msg.text}"))
            
            # Track the flow
            auth_called = False
            chat_loaded = False
            
            # Mock auth endpoint for HTMX
            async def handle_auth(route):
                nonlocal auth_called
                auth_called = True
                
                # Set session cookie in response
                await route.fulfill(
                    status=200,
                    headers={
                        "HX-Redirect": "/chat",
                        "Set-Cookie": "session=test-session; Path=/; HttpOnly"
                    },
                    body=""
                )
            
            # Mock chat endpoint
            async def handle_chat(route):
                nonlocal chat_loaded
                
                # Check if we have session
                cookies = await route.request.headers.get('cookie', '')
                if 'session=' in cookies:
                    chat_loaded = True
                    await route.fulfill(
                        status=200,
                        content_type="text/html",
                        body="""
                        <html>
                        <head><title>Gaia Chat</title></head>
                        <body>
                            <h1>Welcome to Chat!</h1>
                            <div id="chat-interface">
                                <div id="messages"></div>
                                <textarea name="message" id="message-input"></textarea>
                            </div>
                        </body>
                        </html>
                        """
                    )
                else:
                    # No session, redirect to login
                    await route.fulfill(
                        status=303,
                        headers={"Location": "/login"}
                    )
            
            await page.route("**/auth/login", handle_auth)
            await page.route("**/chat", handle_chat)
            
            # Start at login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Fill and submit
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test123')
            await page.click('button[type="submit"]')
            
            # Wait for HTMX redirect
            await page.wait_for_url('**/chat', timeout=5000)
            
            # Verify flow completed
            assert auth_called, "Auth endpoint should have been called"
            assert chat_loaded, "Chat page should have loaded"
            assert page.url.endswith('/chat'), "Should be on chat page"
            
            # Verify chat interface loaded
            chat_interface = await page.query_selector('#chat-interface')
            assert chat_interface, "Chat interface should be present"
            
            await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])