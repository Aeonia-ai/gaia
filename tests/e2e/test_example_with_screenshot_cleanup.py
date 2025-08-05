"""
Example test showing how to use the screenshot cleanup fixtures.

This demonstrates the best practices for taking screenshots in tests
while ensuring they are properly cleaned up.
"""
import pytest
from playwright.async_api import async_playwright


@pytest.mark.screenshot
async def test_with_managed_screenshots(screenshot_manager):
    """Example test using screenshot manager for automatic cleanup"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            await page.goto("http://localhost:8000/login")
            
            # Take screenshots using the manager - they'll be auto-cleaned
            screenshot_manager.take_screenshot(page, "login-page.png")
            
            # Fill login form
            await page.fill('input[name="email"]', "test@example.com")
            await page.fill('input[name="password"]', "testpass")
            
            # Take screenshot in a subdirectory
            screenshot_manager.take_screenshot(
                page, 
                "filled-form.png", 
                subdir="forms"
            )
            
            # Submit form
            await page.click('button[type="submit"]')
            
            # Wait for navigation
            await page.wait_for_url("**/chat", timeout=5000)
            
            # Take final screenshot
            screenshot_manager.take_screenshot(page, "chat-page.png")
            
        finally:
            await browser.close()


@pytest.mark.screenshot
@pytest.mark.keep_screenshots  # This test's screenshots won't be deleted
async def test_visual_regression(screenshot_cleanup):
    """Example of visual regression test that preserves screenshots"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            await page.goto("http://localhost:8000/login")
            
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
async def test_with_failure_screenshot(page, screenshot_on_failure):
    """Example test that automatically takes screenshot on failure"""
    # The screenshot_on_failure fixture will automatically
    # capture a screenshot if this test fails
    
    await page.goto("http://localhost:8000/login")
    
    # This assertion might fail
    assert await page.title() == "Expected Title"
    
    # If the test fails, a screenshot will be saved to:
    # tests/web/screenshots/failures/test_with_failure_screenshot_failure.png


# Example of converting existing test pattern
async def test_old_pattern_converted(page, request):
    """Shows how to convert from old pattern to new pattern"""
    
    # OLD PATTERN (don't use):
    # await page.screenshot(path="tests/web/screenshots/some-test.png")
    
    # NEW PATTERN (use this):
    from tests.fixtures.screenshot_cleanup import take_debug_screenshot
    
    await page.goto("http://localhost:8000")
    
    # Take debug screenshot with test name included
    await take_debug_screenshot(
        page, 
        "homepage-loaded", 
        test_name=request.node.name
    )
    
    # The screenshot will be saved to:
    # tests/web/screenshots/debug/test_old_pattern_converted_homepage-loaded.png
    # and cleaned up based on KEEP_TEST_SCREENSHOTS env var


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