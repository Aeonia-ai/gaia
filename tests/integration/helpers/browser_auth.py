"""
Shared authentication helpers for browser-based integration tests.

Provides consistent login/logout functionality for Playwright tests.
"""
import os
from typing import Dict, Optional
from playwright.async_api import Page, BrowserContext
from tests.fixtures.shared_test_user import SharedTestUser


class BrowserAuthHelper:
    """Helper for browser-based authentication in tests."""
    
    @staticmethod
    async def login_with_real_user(
        page: Page,
        user_credentials: Optional[Dict[str, str]] = None,
        wait_for_navigation: bool = True
    ) -> bool:
        """
        Perform real login with test user credentials.
        
        Args:
            page: Playwright page object
            user_credentials: Optional dict with email/password. If None, uses SharedTestUser
            wait_for_navigation: Whether to wait for navigation to /chat after login
            
        Returns:
            bool: True if login successful, False otherwise
        """
        if user_credentials is None:
            # Get shared test user credentials
            creds = SharedTestUser.get_credentials()
            email = creds["email"]
            password = creds["password"]
        else:
            email = user_credentials["email"]
            password = user_credentials["password"]
        
        try:
            # Navigate to login page
            await page.goto(f"{os.getenv('WEB_SERVICE_URL', 'http://web-service:8000')}/login")
            
            # Fill login form
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            
            # Click submit and optionally wait for navigation
            if wait_for_navigation:
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/chat", timeout=30000)
            else:
                await page.click('button[type="submit"]')
                
            return True
            
        except Exception as e:
            print(f"Login failed: {e}")
            return False
    
    @staticmethod
    async def ensure_logged_out(page: Page) -> None:
        """Ensure user is logged out before test."""
        try:
            # Try to navigate to logout
            await page.goto(f"{os.getenv('WEB_SERVICE_URL', 'http://web-service:8000')}/auth/logout")
        except:
            # If logout fails, clear cookies
            await page.context.clear_cookies()
    
    @staticmethod
    async def create_authenticated_context(browser, viewport=None) -> tuple[BrowserContext, Page]:
        """
        Create a new browser context with authenticated session.
        
        Returns:
            Tuple of (context, page) with user already logged in
        """
        context = await browser.new_context(
            viewport=viewport or {'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Login with real user
        await BrowserAuthHelper.login_with_real_user(page)
        
        return context, page
    
    @staticmethod
    def get_mock_session_cookie(user_id: str = "test-user-123") -> dict:
        """
        Get a mock session cookie for API testing.
        
        Note: This should only be used for API contract tests,
        not for browser integration tests.
        """
        return {
            "name": "session",
            "value": f"mock-session-{user_id}",
            "domain": "web-service",
            "path": "/",
            "httpOnly": True
        }