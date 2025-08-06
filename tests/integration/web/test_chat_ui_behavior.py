"""
UI behavior tests that verify specific functionality without full auth.
These tests focus on UI interactions and client-side behavior.
"""
import pytest
from playwright.async_api import async_playwright
import os
import json

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestChatUIBehavior:
    """Test chat UI behavior and interactions"""
    
    @pytest.mark.asyncio
    async def test_login_form_validation(self):
        """Test client-side form validation on login page"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Navigate to real login page
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Try to submit empty form
            submit_button = await page.query_selector('button[type="submit"]')
            await submit_button.click()
            
            # Check HTML5 validation - email should be required
            email_input = await page.query_selector('input[name="email"]')
            is_invalid = await email_input.evaluate('el => !el.validity.valid')
            assert is_invalid, "Email field should show validation error when empty"
            
            # Fill invalid email
            await email_input.fill("not-an-email")
            await submit_button.click()
            
            # Check email format validation
            is_invalid = await email_input.evaluate('el => !el.validity.valid')
            assert is_invalid, "Email field should show validation error for invalid format"
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_responsive_layout(self):
        """Test that chat UI adapts to different screen sizes"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Test mobile viewport
            mobile_context = await browser.new_context(
                viewport={'width': 375, 'height': 667},
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
            )
            mobile_page = await mobile_context.new_page()
            
            await mobile_page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Check if viewport meta tag exists
            viewport_meta = await mobile_page.query_selector('meta[name="viewport"]')
            assert viewport_meta is not None, "Should have viewport meta tag for mobile"
            
            # Check if form is visible and usable on mobile
            form = await mobile_page.query_selector('form')
            is_visible = await form.is_visible()
            assert is_visible, "Login form should be visible on mobile"
            
            await mobile_context.close()
            
            # Test desktop viewport
            desktop_context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            desktop_page = await desktop_context.new_page()
            
            await desktop_page.goto(f'{WEB_SERVICE_URL}/login')
            
            form = await desktop_page.query_selector('form')
            is_visible = await form.is_visible()
            assert is_visible, "Login form should be visible on desktop"
            
            await desktop_context.close()
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_error_message_display(self):
        """Test that error messages are displayed properly"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Mock auth to return error
            await page.route("**/api/v1/auth/login", lambda route: route.fulfill(
                status=400,
                headers={"Content-Type": "application/json"},
                body=json.dumps({"detail": "Invalid credentials"})
            ))
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Submit invalid credentials
            await page.fill('input[name="email"]', 'wrong@example.com')
            await page.fill('input[name="password"]', 'wrongpass')
            await page.click('button[type="submit"]')
            
            # Wait for error to appear
            await page.wait_for_timeout(1000)
            
            # Check for error message
            error_elements = await page.query_selector_all('.error, [class*="error"], [role="alert"]')
            found_error = False
            for elem in error_elements:
                text = await elem.inner_text()
                if text and "error" in text.lower() or "invalid" in text.lower():
                    found_error = True
                    break
            
            assert found_error, "Should display error message for invalid credentials"
            
            await browser.close()
    
    @pytest.mark.asyncio  
    async def test_loading_states(self):
        """Test that loading states are shown during async operations"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Mock slow auth response
            async def slow_auth_handler(route):
                await page.wait_for_timeout(500)  # Simulate delay
                await route.fulfill(
                    status=200,
                    headers={"Content-Type": "application/json"},
                    body=json.dumps({"access_token": "test", "user": {"id": "1"}})
                )
            
            await page.route("**/api/v1/auth/login", slow_auth_handler)
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Fill form
            await page.fill('input[name="email"]', 'test@example.com')
            await page.fill('input[name="password"]', 'password')
            
            # Track button state
            submit_button = await page.query_selector('button[type="submit"]')
            
            # Click and immediately check if button shows loading state
            await submit_button.click()
            
            # Check if button is disabled or shows loading indicator
            is_disabled = await submit_button.is_disabled()
            button_text = await submit_button.inner_text()
            
            # Button should either be disabled or show different text during loading
            assert is_disabled or button_text != "Sign In", \
                "Submit button should indicate loading state"
            
            await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])