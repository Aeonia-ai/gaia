#!/usr/bin/env python3
"""
User Flow Recording Script

Record a user flow with Playwright trace for debugging.

Usage:
    python scripts/webui/capture/record_flow.py --flow "login -> send_message"
    python scripts/webui/capture/record_flow.py --flow "chat_session" --output traces/debug.zip
"""
import sys
import os
import asyncio
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.browser import BrowserSession, get_common_args
from utils.auth import login, get_test_credentials


async def execute_flow(session: BrowserSession, flow_name: str):
    """Execute a predefined user flow"""
    page = session.get_page()
    credentials = get_test_credentials()

    if flow_name == "login":
        print("🔐 Executing login flow...")
        await login(
            page,
            credentials["email"],
            credentials["password"],
            session.base_url
        )

    elif flow_name == "send_message":
        print("💬 Executing send message flow...")
        # Assumes already logged in
        message_input = page.locator('[data-testid="message-input"]')
        await message_input.fill("Test message for recording")
        send_button = page.locator('[data-testid="send-button"]')
        await send_button.click()

        # Wait for response
        await page.wait_for_selector('[aria-busy="true"]', timeout=2000)
        await page.wait_for_selector('[aria-busy="true"]', state="hidden", timeout=10000)

    elif flow_name == "chat_session":
        print("💭 Executing full chat session flow...")
        # Login
        await login(
            page,
            credentials["email"],
            credentials["password"],
            session.base_url
        )

        # Send multiple messages
        for i, msg in enumerate(["Hello", "How are you?", "Tell me about yourself"], 1):
            print(f"  Message {i}: {msg}")
            message_input = page.locator('[data-testid="message-input"]')
            await message_input.fill(msg)
            send_button = page.locator('[data-testid="send-button"]')
            await send_button.click()

            # Wait for response
            await page.wait_for_selector('[aria-busy="true"]', timeout=2000)
            await page.wait_for_selector('[aria-busy="true"]', state="hidden", timeout=10000)

            await asyncio.sleep(1)  # Small delay between messages

    else:
        print(f"❌ Unknown flow: {flow_name}")
        return False

    return True


async def main():
    parser = argparse.ArgumentParser(description="Record user flow with Playwright trace")
    parser.add_argument(
        "--flow",
        required=True,
        help="Flow to record (login, send_message, chat_session, or custom)"
    )
    parser.add_argument(
        "--output",
        help="Output trace file (default: auto-generated)"
    )
    parser.add_argument(
        "--screenshots",
        action="store_true",
        help="Include screenshots in trace"
    )
    parser.add_argument(
        "--snapshots",
        action="store_true",
        help="Include DOM snapshots in trace"
    )

    # Add common arguments
    parser = get_common_args(parser)
    args = parser.parse_args()

    # Generate output filename if not provided
    if not args.output:
        os.makedirs("traces", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"traces/flow_{args.flow}_{timestamp}.zip"

    print(f"🎬 Recording flow: {args.flow}")

    # Create browser session
    async with BrowserSession(
        headless=not args.headful,
        slow_mo=args.slow or 100,  # Default to 100ms for recording
        base_url=args.base_url
    ) as session:
        page = session.get_page()

        # Start tracing
        await session.context.tracing.start(
            screenshots=args.screenshots or True,
            snapshots=args.snapshots or True,
            sources=True
        )

        try:
            # Execute the flow
            success = await execute_flow(session, args.flow)

            if not success:
                print("❌ Flow execution failed")
                sys.exit(1)

        finally:
            # Stop tracing and save
            await session.context.tracing.stop(path=args.output)
            print(f"💾 Trace saved: {args.output}")

            # Print file info
            file_size = os.path.getsize(args.output)
            print(f"📊 File size: {file_size / 1024:.1f} KB")
            print(f"\n📖 View trace:")
            print(f"   playwright show-trace {args.output}")

    print("✅ Flow recording complete")


if __name__ == "__main__":
    asyncio.run(main())
