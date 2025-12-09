#!/usr/bin/env python3
"""
Check how many conversations are displayed in the web UI.
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))

from browser import BrowserSession, get_common_args, handle_post_actions
from auth import ensure_logged_in, get_test_credentials


async def check_conversations(
    headless: bool = True,
    slow_mo: int = 0,
    screenshot_path: str | None = None,
    base_url: str = "http://localhost:8080",
    wait: bool = False,
    viewport: dict | None = None
):
    """Check conversations displayed in web UI"""

    # Get credentials
    creds = get_test_credentials()

    async with BrowserSession(headless=headless, slow_mo=slow_mo, viewport=viewport) as session:
        page = session.page

        # Ensure logged in
        if not await ensure_logged_in(page, creds["email"], creds["password"], base_url):
            print("❌ Failed to log in")
            return

        # Navigate to chat if not already there
        if "/chat" not in page.url:
            await page.goto(f"{base_url}/chat")
            await page.wait_for_load_state("networkidle")

        print(f"📍 Current URL: {page.url}")

        # Look for conversation elements in sidebar
        # Try multiple possible selectors
        selectors_to_try = [
            '[data-testid="conversation-item"]',
            '.conversation-item',
            '[class*="conversation"]',
            'a[href^="/chat/"]',
            'button[class*="conversation"]',
            'li[class*="conversation"]',
        ]

        conversation_count = 0
        conversation_selector = None

        for selector in selectors_to_try:
            try:
                elements = await page.locator(selector).all()
                if elements:
                    conversation_count = len(elements)
                    conversation_selector = selector
                    print(f"✅ Found {conversation_count} conversations using selector: {selector}")
                    break
            except Exception as e:
                continue

        if conversation_count == 0:
            print("⚠️  No conversations found with standard selectors")
            print("\n🔍 Dumping page structure to find conversation elements...")

            # Get all links and buttons that might be conversations
            links = await page.locator('a').all()
            print(f"\n📊 Total links on page: {len(links)}")

            chat_links = []
            for link in links:
                href = await link.get_attribute('href')
                if href and '/chat/' in href:
                    text = await link.inner_text()
                    chat_links.append((href, text.strip()[:50]))

            if chat_links:
                print(f"\n💬 Found {len(chat_links)} chat links:")
                for href, text in chat_links[:10]:  # Show first 10
                    print(f"   • {href}: {text}")
                conversation_count = len(chat_links)
            else:
                print("   No chat links found")

            # Check for sidebar
            sidebar_selectors = [
                '[data-testid="sidebar"]',
                '.sidebar',
                'aside',
                '[class*="sidebar"]',
                'nav'
            ]

            for selector in sidebar_selectors:
                try:
                    sidebar = page.locator(selector).first
                    if await sidebar.count() > 0:
                        content = await sidebar.inner_text()
                        print(f"\n📋 Sidebar content ({selector}):")
                        print(content[:500])
                        break
                except:
                    continue

        # Take screenshot if requested
        if screenshot_path:
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Screenshot saved: {screenshot_path}")

        # Summary
        print("\n" + "="*60)
        print(f"📊 SUMMARY")
        print("="*60)
        print(f"User: {creds['email']}")
        print(f"Conversations displayed in UI: {conversation_count}")
        print(f"URL: {page.url}")

        # Wait if requested
        if wait:
            print("\n⏸️  Browser will stay open. Press Ctrl+C to close...")
            try:
                await page.wait_for_timeout(300000)  # 5 minutes
            except KeyboardInterrupt:
                print("\n✅ Closing browser...")


def main():
    parser = argparse.ArgumentParser(description="Check conversations in web UI")

    # Add common browser arguments
    args_dict = get_common_args(parser)
    args = parser.parse_args()

    # Run the async function
    asyncio.run(check_conversations(
        headless=not args.headful,
        slow_mo=args.slow * 1000 if args.slow else 0,
        screenshot_path=args.screenshot,
        base_url=args.base_url,
        wait=args.wait,
        viewport={"width": args.viewport_width, "height": args.viewport_height}
    ))


if __name__ == "__main__":
    main()
