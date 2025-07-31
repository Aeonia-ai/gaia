"""
Simple browser auth tests using reliable fixtures.
These tests validate core auth functionality without complex dependencies.
"""
import pytest
import os
from playwright.async_api import expect

# Import simplified fixtures
from tests.web.simple_browser_auth import simple_auth_page, error_test_page

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")

@pytest.mark.asyncio 
class TestSimpleAuth:
    """Browser auth tests with simplified, reliable fixtures"""
    
    async def test_invalid_login_error_message(self, error_test_page):
        """Test that invalid login shows error message"""
        page = error_test_page
        
        # Submit invalid credentials
        await page.fill('input[name="email"]', 'wrong@test.com')
        await page.fill('input[name="password"]', 'wrongpass')
        await page.click('button[type="submit"]')
        
        # Wait for and verify error message
        await page.wait_for_selector('text="Login failed. Please try again."', timeout=5000)
        error_element = await page.query_selector('text="Login failed. Please try again."')
        assert error_element is not None, "Error message should be displayed"
    
    async def test_successful_login_navigation(self, simple_auth_page):
        """Test that valid login navigates to chat"""
        page = simple_auth_page
        
        # Should be on chat page after fixture setup
        assert "/chat" in page.url, f"Should be on chat page, but on {page.url}"
        
        # Should have basic chat elements
        message_input = await page.query_selector('textarea[name="message"]')
        assert message_input is not None, "Chat input should be present"
    
    async def test_login_form_elements_present(self, error_test_page):
        """Test that login form has required elements"""
        page = error_test_page
        
        # Check form elements exist
        email_input = await page.query_selector('input[name="email"]')
        password_input = await page.query_selector('input[name="password"]')
        submit_button = await page.query_selector('button[type="submit"]')
        
        assert email_input is not None, "Email input should be present"
        assert password_input is not None, "Password input should be present"  
        assert submit_button is not None, "Submit button should be present"
        
        # Check submit button text
        button_text = await submit_button.inner_text()
        assert "Sign In" in button_text, f"Submit button should say 'Sign In', got '{button_text}'"