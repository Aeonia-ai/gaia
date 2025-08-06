"""
Simple chat browser test for debugging.
"""
import pytest
from playwright.async_api import async_playwright
import os
from .mock_templates import CHAT_PAGE_HTML

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_chat_page_loads():
    """Test that chat page loads with mocked response"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Mock the chat page directly
        await page.route("**/chat", lambda route: route.fulfill(
            status=200,
            headers={"Content-Type": "text/html"},
            body=CHAT_PAGE_HTML
        ))
        
        # Mock conversations API
        await page.route("**/api/conversations", lambda route: route.fulfill(
            status=200,
            json={"conversations": [], "has_more": False}
        ))
        
        # Navigate directly to chat
        await page.goto(f'{WEB_SERVICE_URL}/chat')
        
        # Verify we're on the chat page
        assert "/chat" in page.url
        
        # Check if chat form exists
        chat_form = await page.query_selector('#chat-form')
        assert chat_form is not None, "Chat form should exist"
        
        # Check for message input
        message_input = await page.query_selector('textarea[name="message"]')
        assert message_input is not None, "Message input should exist"
        
        await browser.close()


@pytest.mark.asyncio
async def test_chat_message_input():
    """Test that we can interact with message input"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Mock the chat page
        await page.route("**/chat", lambda route: route.fulfill(
            status=200,
            headers={"Content-Type": "text/html"},
            body=CHAT_PAGE_HTML
        ))
        
        # Navigate to chat
        await page.goto(f'{WEB_SERVICE_URL}/chat')
        
        # Find message input
        message_input = await page.query_selector('textarea[name="message"]')
        assert message_input is not None, "Should find message input"
        
        # Type in it
        await message_input.fill("Test message")
        value = await message_input.input_value()
        assert value == "Test message", "Should be able to type in message input"
        
        # Find submit button
        submit_button = await page.query_selector('#chat-form button[type="submit"]')
        assert submit_button is not None, "Should find submit button"
        
        # Click submit and verify input is cleared
        await submit_button.click()
        await page.wait_for_timeout(200)  # Wait for mock JS to clear input
        
        new_value = await message_input.input_value()
        assert new_value == "", "Message input should be cleared after submission"
        
        await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])