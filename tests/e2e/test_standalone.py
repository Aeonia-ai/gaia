"""
Standalone browser test without class structure.
"""
import pytest
from playwright.async_api import async_playwright
import os

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")

@pytest.mark.asyncio
async def test_standalone_page_load():
    """Test basic page loading with working pattern"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        try:
            # Just load the login page
            await page.goto(f"{WEB_SERVICE_URL}/login")
            
            # Check title
            title = await page.title()
            assert "Gaia" in title, f"Expected 'Gaia' in title, got '{title}'"
            
        finally:
            await browser.close()