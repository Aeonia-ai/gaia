#!/usr/bin/env python3
"""
Shared browser utilities for web UI scripts.
Provides common browser setup, configuration, and helpers.
"""
import os
import asyncio
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from typing import Optional, Dict, Any


class BrowserSession:
    """Manages a browser session for web UI scripts"""

    def __init__(
        self,
        headless: bool = True,
        slow_mo: int = 0,
        base_url: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None
    ):
        self.headless = headless
        self.slow_mo = slow_mo
        self.base_url = base_url or os.getenv("WEB_URL", "http://localhost:8080")
        self.viewport = viewport or {"width": 1280, "height": 720}

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def start(self):
        """Start browser session"""
        self.playwright = await async_playwright().start()

        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo
        )

        # Create context
        self.context = await self.browser.new_context(
            viewport=self.viewport,
            base_url=self.base_url
        )

        # Create page
        self.page = await self.context.new_page()

        return self

    async def close(self):
        """Close browser session"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def goto(self, url: str, **kwargs) -> None:
        """Navigate to URL (handles relative URLs)"""
        if not url.startswith("http"):
            url = f"{self.base_url}{url}"
        await self.page.goto(url, **kwargs)

    async def screenshot(self, path: str, **kwargs) -> None:
        """Take screenshot"""
        await self.page.screenshot(path=path, **kwargs)
        print(f"📸 Screenshot saved: {path}")

    async def wait_for_load(self, timeout: int = 5000) -> None:
        """Wait for page to finish loading"""
        await self.page.wait_for_load_state("networkidle", timeout=timeout)

    def get_page(self) -> Page:
        """Get the current page"""
        if not self.page:
            raise RuntimeError("Browser not started. Use 'async with BrowserSession()' or call start()")
        return self.page


def get_common_args(parser):
    """Add common arguments to argparse parser"""
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Show browser window (not headless)"
    )
    parser.add_argument(
        "--slow",
        type=int,
        default=0,
        help="Slow down actions (milliseconds)"
    )
    parser.add_argument(
        "--screenshot",
        type=str,
        help="Take screenshot after completion"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Keep browser open after completion"
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("WEB_URL", "http://localhost:8080"),
        help="Base URL for web service"
    )
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1280,
        help="Browser viewport width"
    )
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=720,
        help="Browser viewport height"
    )
    return parser


async def create_session_from_args(args) -> BrowserSession:
    """Create BrowserSession from argparse args"""
    session = BrowserSession(
        headless=not args.headful,
        slow_mo=args.slow,
        base_url=args.base_url,
        viewport={
            "width": args.viewport_width,
            "height": args.viewport_height
        }
    )
    await session.start()
    return session


async def handle_post_actions(session: BrowserSession, args) -> None:
    """Handle common post-action flags (screenshot, wait)"""
    if args.screenshot:
        await session.screenshot(args.screenshot)

    if args.wait:
        print("\n⏸️  Browser will stay open. Press Ctrl+C to close...")
        try:
            await asyncio.sleep(3600)  # Wait up to 1 hour
        except KeyboardInterrupt:
            print("\n👋 Closing browser...")
