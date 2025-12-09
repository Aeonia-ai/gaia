#!/usr/bin/env python3
"""
Send Message Pattern Script

Login (if needed) and send a chat message, capturing the response.

Usage:
    python scripts/webui/patterns/send_message.py --message "Hello!"
    python scripts/webui/patterns/send_message.py --message "Test" --headful
    python scripts/webui/patterns/send_message.py --message "Debug" --wait --slow 500
"""
import sys
import os
import asyncio
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.browser import BrowserSession, get_common_args, handle_post_actions
from utils.auth import ensure_logged_in, get_test_credentials


async def send_message(page, message: str):
    """Send a chat message and wait for response"""
    print(f"💬 Sending message: {message}")

    # Fill message input - try data-testid first, fall back to name attribute
    try:
        message_input = page.locator('[data-testid="message-input"]')
        await message_input.fill(message, timeout=1000)
    except:
        # Try input first, then textarea
        try:
            message_input = page.locator('input[name="message"]')
            await message_input.fill(message)
        except:
            message_input = page.locator('textarea[name="message"]')
            await message_input.fill(message)

    # Send - try pressing Enter (more reliable than finding submit button)
    await page.keyboard.press("Enter")

    # Wait for loading state
    print("⏳ Waiting for response...")
    try:
        # Wait for aria-busy to appear (request started)
        await page.wait_for_selector('[aria-busy="true"]', timeout=2000)

        # Wait for aria-busy to disappear (request complete)
        await page.wait_for_selector('[aria-busy="true"]', state="hidden", timeout=10000)

        print("✅ Response received")
        return True

    except Exception as e:
        print(f"⚠️  Response wait timed out: {e}")
        return False


async def get_last_message(page):
    """Get the last message in the chat"""
    # Try data-testid first, fall back to ID selector
    try:
        messages = page.locator('[data-testid="messages-container"] [role="article"]')
        count = await messages.count()
    except:
        # Fall back to current implementation
        messages = page.locator('#messages .mb-4')
        count = await messages.count()

    if count == 0:
        return None

    last_message = messages.nth(count - 1)
    text = await last_message.inner_text()
    return text


async def main():
    parser = argparse.ArgumentParser(description="Send a chat message")
    parser.add_argument(
        "--message",
        required=True,
        help="Message to send"
    )
    parser.add_argument(
        "--email",
        help="User email (default: TEST_EMAIL env var)"
    )
    parser.add_argument(
        "--password",
        help="User password (default: TEST_PASSWORD env var)"
    )
    parser.add_argument(
        "--capture-response",
        action="store_true",
        help="Print the AI response"
    )

    # Add common arguments
    parser = get_common_args(parser)
    args = parser.parse_args()

    # Get credentials
    credentials = get_test_credentials()
    email = args.email or credentials["email"]
    password = args.password or credentials["password"]

    # Create browser session
    async with BrowserSession(
        headless=not args.headful,
        slow_mo=args.slow,
        base_url=args.base_url
    ) as session:
        page = session.get_page()

        # Ensure logged in
        await ensure_logged_in(page, email, password, args.base_url)

        # Navigate to chat if not already there
        if "/chat" not in page.url:
            print("📍 Navigating to chat...")
            await session.goto("/chat")
            await session.wait_for_load()

        # Send the message
        success = await send_message(page, args.message)

        if not success:
            print("❌ Failed to send message or get response")
            sys.exit(1)

        # Capture response if requested
        if args.capture_response:
            print("\n📝 Capturing response...")
            await asyncio.sleep(1)  # Give time for content to render
            response = await get_last_message(page)
            if response:
                print(f"\n--- AI Response ---")
                print(response)
                print(f"--- End Response ---\n")

        # Handle post-actions
        await handle_post_actions(session, args)

    print("✅ Send message pattern complete")


if __name__ == "__main__":
    asyncio.run(main())
