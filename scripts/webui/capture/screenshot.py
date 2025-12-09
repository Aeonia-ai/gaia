#!/usr/bin/env python3
"""
Screenshot Capture Script

Take screenshots of web pages with optional login and navigation.

Usage:
    python scripts/webui/capture/screenshot.py --url /login --output login.png
    python scripts/webui/capture/screenshot.py --url /chat --login --output chat.png
    python scripts/webui/capture/screenshot.py --url /chat --full-page --output full_chat.png
"""
import sys
import os
import asyncio
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.browser import BrowserSession, get_common_args
from utils.auth import ensure_logged_in, get_test_credentials


async def main():
    parser = argparse.ArgumentParser(description="Capture screenshot of web page")
    parser.add_argument(
        "--url",
        default="/",
        help="URL to screenshot (default: /)"
    )
    parser.add_argument(
        "--output",
        help="Output filename (default: auto-generated)"
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Login before taking screenshot"
    )
    parser.add_argument(
        "--email",
        help="User email for login"
    )
    parser.add_argument(
        "--password",
        help="User password for login"
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Capture full page (not just viewport)"
    )
    parser.add_argument(
        "--selector",
        help="Screenshot specific element matching selector"
    )
    parser.add_argument(
        "--wait-for",
        help="Wait for selector before screenshot"
    )

    # Add common arguments
    parser = get_common_args(parser)
    args = parser.parse_args()

    # Generate output filename if not provided
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        url_slug = args.url.replace('/', '_').strip('_') or 'home'
        args.output = f"screenshot_{url_slug}_{timestamp}.png"

    print(f"📸 Capturing screenshot: {args.url}")

    # Create browser session
    async with BrowserSession(
        headless=not args.headful,
        slow_mo=args.slow,
        base_url=args.base_url
    ) as session:
        page = session.get_page()

        # Login if requested
        if args.login:
            credentials = get_test_credentials()
            email = args.email or credentials["email"]
            password = args.password or credentials["password"]
            await ensure_logged_in(page, email, password, args.base_url)

        # Navigate to URL
        await session.goto(args.url)
        await session.wait_for_load()

        # Wait for specific element if requested
        if args.wait_for:
            print(f"⏳ Waiting for: {args.wait_for}")
            await page.wait_for_selector(args.wait_for, timeout=10000)

        # Take screenshot
        screenshot_options = {
            "path": args.output,
            "full_page": args.full_page
        }

        if args.selector:
            element = page.locator(args.selector)
            await element.screenshot(**screenshot_options)
            print(f"📸 Element screenshot saved: {args.output}")
        else:
            await page.screenshot(**screenshot_options)
            print(f"📸 Screenshot saved: {args.output}")

        # Print file info
        file_size = os.path.getsize(args.output)
        print(f"📊 File size: {file_size / 1024:.1f} KB")

    print("✅ Screenshot capture complete")


if __name__ == "__main__":
    asyncio.run(main())
