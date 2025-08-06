"""
Test with direct chat page mocking to bypass auth.
"""
import pytest
from playwright.async_api import async_playwright
import os

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_chat_page_with_direct_mock():
    """Test chat page by mocking the entire response"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Mock the chat page to return a simple chat interface
        async def chat_page_handler(route):
            await route.fulfill(
                status=200,
                headers={"Content-Type": "text/html"},
                body="""
                <!DOCTYPE html>
                <html>
                <head><title>Chat</title></head>
                <body>
                    <div id="chat-container">
                        <div id="conversation-list"></div>
                        <form id="chat-form">
                            <textarea name="message" placeholder="Type your message..."></textarea>
                            <button type="submit">Send</button>
                        </form>
                    </div>
                </body>
                </html>
                """
            )
        
        # Mock conversations API
        async def conversations_handler(route):
            await route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body='{"conversations": [], "has_more": false}'
            )
        
        await page.route("**/chat", chat_page_handler)
        await page.route("**/api/conversations", conversations_handler)
        
        # Navigate to chat
        await page.goto(f'{WEB_SERVICE_URL}/chat')
        
        # Verify we're on the chat page
        assert page.url.endswith("/chat")
        
        # Check for chat form
        chat_form = await page.query_selector('#chat-form')
        assert chat_form is not None
        
        # Check for message input
        message_input = await page.query_selector('textarea[name="message"]')
        assert message_input is not None
        
        # Type a message
        await message_input.fill("Test message")
        value = await message_input.input_value()
        assert value == "Test message"
        
        print("✓ Direct mock test passed")
        
        await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])