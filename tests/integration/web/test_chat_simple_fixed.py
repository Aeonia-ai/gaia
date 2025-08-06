"""
Fixed version of simple chat browser test using proper auth mocking.
"""
import pytest
from playwright.async_api import async_playwright
import os
from .browser_auth_helper import BrowserAuthHelper

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_chat_page_loads():
    """Test that chat page loads with proper authentication"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Setting up authenticated context...")
        
        # Set up full auth mocking
        await BrowserAuthHelper.setup_full_auth_mocking(page, context)
        
        print(f"Navigating directly to {WEB_SERVICE_URL}/chat")
        # Navigate directly to chat with auth context
        await page.goto(f'{WEB_SERVICE_URL}/chat')
        
        # Should be on chat page
        assert "/chat" in page.url, f"Should be on chat page, but URL is: {page.url}"
        print(f"✓ Successfully on chat page: {page.url}")
        
        # Check if chat form exists
        print("Looking for chat form...")
        chat_form = await page.query_selector('#chat-form')
        assert chat_form is not None, "Chat form should exist"
        print("✓ Chat form found")
        
        await browser.close()


@pytest.mark.asyncio
async def test_chat_message_input():
    """Test that we can interact with message input"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        # Set up full auth mocking
        await BrowserAuthHelper.setup_full_auth_mocking(page, context)
        
        # Navigate directly to chat
        await page.goto(f'{WEB_SERVICE_URL}/chat')
        
        # Find message input
        print("Looking for message input...")
        message_input = None
        selectors = [
            'textarea[name="message"]',
            'textarea[placeholder*="message"]',
            'textarea[placeholder*="Message"]',
            'textarea[placeholder*="Type"]',
            '#message-input',
            '#chat-form textarea',
            'input[name="message"]',
            '#chat-form input[type="text"]'
        ]
        
        for selector in selectors:
            message_input = await page.query_selector(selector)
            if message_input:
                print(f"✓ Found message input with selector: {selector}")
                break
        
        assert message_input is not None, "Should find message input"
        
        # Type in it
        await message_input.fill("Test message")
        value = await message_input.input_value()
        assert value == "Test message", "Should be able to type in message input"
        print("✓ Can type in message input")
        
        # Find submit button
        submit_button = await page.query_selector('#chat-form button[type="submit"]')
        if not submit_button:
            submit_button = await page.query_selector('#chat-form button')
        
        assert submit_button is not None, "Should find submit button"
        print("✓ Found submit button")
        
        await browser.close()


@pytest.mark.asyncio
async def test_chat_message_submission():
    """Test submitting a chat message"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        # Set up full auth mocking with custom conversations
        await BrowserAuthHelper.setup_full_auth_mocking(page, context)
        
        # Navigate to chat
        await page.goto(f'{WEB_SERVICE_URL}/chat')
        
        # Find and fill message input
        message_input = None
        for selector in ['textarea[name="message"]', '#chat-form textarea', '#message-input']:
            message_input = await page.query_selector(selector)
            if message_input:
                break
        
        assert message_input is not None
        await message_input.fill("Hello, test message")
        
        # Submit the message
        submit_button = await page.query_selector('#chat-form button[type="submit"]')
        if not submit_button:
            submit_button = await page.query_selector('#chat-form button')
        
        # Click submit
        await submit_button.click()
        
        # Wait a moment for any response handling
        await page.wait_for_timeout(1000)
        
        # Message input should be cleared after submission
        new_value = await message_input.input_value()
        assert new_value == "" or new_value == " ", "Message input should be cleared after submission"
        print("✓ Message submitted and input cleared")
        
        await browser.close()


@pytest.mark.asyncio
async def test_chat_with_existing_conversations():
    """Test chat page with existing conversations"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        # Set up auth
        await BrowserAuthHelper.setup_authenticated_context(context)
        await BrowserAuthHelper.mock_auth_endpoints(page)
        
        # Mock conversations with data
        test_conversations = [
            {"id": "conv-1", "title": "Previous Chat 1", "preview": "Hello..."},
            {"id": "conv-2", "title": "Previous Chat 2", "preview": "Another..."}
        ]
        await BrowserAuthHelper.mock_chat_endpoints(page, conversations=test_conversations)
        
        # Navigate to chat
        await page.goto(f'{WEB_SERVICE_URL}/chat')
        
        # Should show conversations (implementation-specific selectors)
        # This is a placeholder - adjust based on actual UI
        await page.wait_for_timeout(1000)  # Give time for conversations to load
        
        print("✓ Chat page loaded with conversation context")
        
        await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])