"""
Standalone browser test without class structure.
"""
import pytest
import os

@pytest.mark.asyncio
async def test_standalone_page_load(page):
    """Test basic page loading without class"""
    WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")
    
    # Just load the login page
    await page.goto(f"{WEB_SERVICE_URL}/login")
    
    # Check title
    title = await page.title()
    assert "Gaia" in title, f"Expected 'Gaia' in title, got '{title}'"