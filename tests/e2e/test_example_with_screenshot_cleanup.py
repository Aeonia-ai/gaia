"""
Example test showing how to use the screenshot cleanup fixtures.

This demonstrates the best practices for taking screenshots in tests
while ensuring they are properly cleaned up.
"""
import pytest
from playwright.async_api import async_playwright, TimeoutError
import os
import uuid
from tests.fixtures.test_auth import TestUserFactory

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")

# Set a reasonable timeout for all browser operations
DEFAULT_TIMEOUT = 30000  # 30 seconds


@pytest.mark.screenshot
async def test_with_managed_screenshots(screenshot_manager):
    """Example test using screenshot manager for automatic cleanup"""
    # Create real test user
    factory = TestUserFactory()
    test_email = f"screenshot-{uuid.uuid4().hex[:8]}@test.local"
    test_password = os.getenv("GAIA_TEST_PASSWORD", "default-test-password")
    
    user = factory.create_verified_test_user(
        email=test_email,
        password=test_password
    )
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, timeout=DEFAULT_TIMEOUT)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        
        try:
            await page.goto(f"{WEB_SERVICE_URL}/login")
            
            # Take screenshots using the manager - they'll be auto-cleaned
            await screenshot_manager.take_screenshot(page, "login-page.png")
            
            # Fill login form with real credentials
            await page.fill('input[name="email"]', test_email)
            await page.fill('input[name="password"]', test_password)
            
            # Take screenshot in a subdirectory
            await screenshot_manager.take_screenshot(
                page, 
                "filled-form.png", 
                subdir="forms"
            )
            
            # Submit form
            await page.click('button[type="submit"]')
            
            # Wait for navigation
            await page.wait_for_url("**/chat", timeout=10000)
            
            # Take final screenshot
            await screenshot_manager.take_screenshot(page, "chat-page.png")
            
        finally:
            await browser.close()
            factory.cleanup_test_user(user["user_id"])


@pytest.mark.screenshot
@pytest.mark.keep_screenshots  # This test's screenshots won't be deleted
async def test_visual_regression(screenshot_cleanup):
    """Example of visual regression test that preserves screenshots"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, timeout=DEFAULT_TIMEOUT)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        
        try:
            await page.goto(f"{WEB_SERVICE_URL}/login")
            
            # Screenshots in 'baseline' directory are never cleaned
            await page.screenshot(
                path="tests/web/screenshots/baseline/login-reference.png"
            )
            
            # This screenshot will be preserved due to @pytest.mark.keep_screenshots
            await page.screenshot(
                path="tests/web/screenshots/login-test-preserved.png"
            )
            
        finally:
            await browser.close()


@pytest.mark.screenshot
@pytest.mark.asyncio
@pytest.mark.skip(reason="Conflict with pytest-playwright auto-parameterization")
async def test_failure_screenshot_example(screenshot_on_failure):
    """Example test that automatically takes screenshot on failure"""
    # The screenshot_on_failure fixture will automatically
    # capture a screenshot if this test fails
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, timeout=DEFAULT_TIMEOUT)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        
        try:
            await page.goto(f"{WEB_SERVICE_URL}/login")
            
            # This assertion might fail (intentionally for demo)
            title = await page.title()
            assert title == "GAIA Platform", f"Expected 'GAIA Platform' but got '{title}'"
            
        finally:
            await browser.close()
    
    # If the test fails, a screenshot will be saved to:
    # tests/web/screenshots/failures/test_with_failure_screenshot_failure.png


# Example of converting existing test pattern
@pytest.mark.asyncio
@pytest.mark.skip(reason="Conflict with pytest-playwright auto-parameterization")
async def test_pattern_conversion_example(request):
    """Shows how to convert from old pattern to new pattern"""
    
    # OLD PATTERN (don't use):
    # await page.screenshot(path="tests/web/screenshots/some-test.png")
    
    # NEW PATTERN (use this):
    from tests.fixtures.screenshot_cleanup import take_debug_screenshot
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, timeout=DEFAULT_TIMEOUT)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        
        try:
            await page.goto(f"{WEB_SERVICE_URL}")
    
            # Take debug screenshot with test name included
            await take_debug_screenshot(
                page, 
                "homepage-loaded", 
                test_name=request.node.name
            )
            
            # The screenshot will be saved to:
            # tests/web/screenshots/debug/test_old_pattern_converted_homepage-loaded.png
            # and cleaned up based on KEEP_TEST_SCREENSHOTS env var
            
        finally:
            await browser.close()


# Example pytest configuration for running with screenshot preservation
"""
To run tests and keep screenshots for debugging:
    KEEP_TEST_SCREENSHOTS=true pytest tests/e2e/

To run tests and clean up all screenshots (default):
    pytest tests/e2e/
    
To run only screenshot tests:
    pytest -m screenshot
    
To run tests that should preserve their screenshots:
    pytest -m keep_screenshots
"""