#!/usr/bin/env python3
"""
Login Pattern Script

Login to the web UI and optionally capture session state.

Usage:
    python scripts/webui/patterns/login.py --email test@example.com
    python scripts/webui/patterns/login.py --email test@example.com --headful
    python scripts/webui/patterns/login.py --email test@example.com --screenshot login.png
    python scripts/webui/patterns/login.py --email test@example.com --wait
"""
import sys
import os
import asyncio
import argparse
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.browser import BrowserSession, get_common_args, handle_post_actions
from utils.auth import login, get_session_cookies, get_test_credentials


async def main():
    parser = argparse.ArgumentParser(description="Login to web UI")
    parser.add_argument(
        "--email",
        help="User email (default: TEST_EMAIL env var)"
    )
    parser.add_argument(
        "--password",
        help="User password (default: TEST_PASSWORD env var)"
    )
    parser.add_argument(
        "--save-cookies",
        type=str,
        help="Save session cookies to file"
    )
    parser.add_argument(
        "--navigate-to",
        help="Navigate to URL after login"
    )

    # Add common arguments
    parser = get_common_args(parser)
    args = parser.parse_args()

    # Get credentials
    credentials = get_test_credentials()
    email = args.email or credentials["email"]
    password = args.password or credentials["password"]

    print(f"🔐 Logging in as: {email}")

    # Create browser session
    async with BrowserSession(
        headless=not args.headful,
        slow_mo=args.slow,
        base_url=args.base_url
    ) as session:
        page = session.get_page()

        # Attempt login
        success = await login(page, email, password, args.base_url)

        if not success:
            print("❌ Login failed")
            sys.exit(1)

        # Save cookies if requested
        if args.save_cookies:
            cookies = await get_session_cookies(page)
            with open(args.save_cookies, 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"💾 Cookies saved to: {args.save_cookies}")

        # Navigate to specific URL if requested
        if args.navigate_to:
            print(f"🔗 Navigating to: {args.navigate_to}")
            await session.goto(args.navigate_to)
            await session.wait_for_load()

        # Print current state
        print(f"\n📍 Current URL: {page.url}")
        print(f"📊 Session cookies: {len(await get_session_cookies(page))} cookies")

        # Handle post-actions (screenshot, wait)
        await handle_post_actions(session, args)

    print("✅ Login pattern complete")


if __name__ == "__main__":
    asyncio.run(main())
