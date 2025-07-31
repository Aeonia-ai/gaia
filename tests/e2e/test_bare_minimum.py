"""
Absolute minimum browser test to isolate async issues.
"""
import pytest
import os

@pytest.mark.asyncio
class TestBareMinimum:
    """Minimal browser test to debug async issues"""
    
    async def test_basic_page_load(self, page):
        """Test basic page loading with no custom fixtures"""
        WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")
        
        # Just load the login page
        await page.goto(f"{WEB_SERVICE_URL}/login")
        
        # Check title
        title = await page.title()
        assert "Gaia" in title, f"Expected 'Gaia' in title, got '{title}'"
        
        # Check basic form exists
        email_input = await page.query_selector('input[name="email"]')
        assert email_input is not None, "Email input should exist"