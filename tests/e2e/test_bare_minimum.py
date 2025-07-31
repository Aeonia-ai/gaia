"""
Absolute minimum browser test to isolate async issues.
"""
import pytest
from playwright.async_api import async_playwright
import os

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")

@pytest.mark.asyncio
async def test_basic_page_load():
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
            
            # Check basic form exists
            email_input = await page.query_selector('input[name="email"]')
            assert email_input is not None, "Email input should exist"
            
        finally:
            await browser.close()