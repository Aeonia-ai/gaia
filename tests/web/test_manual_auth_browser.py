"""
Browser tests for manual authentication testing.

Use these tests to verify login with specific accounts.
"""
import pytest
import os
from playwright.async_api import async_playwright
import asyncio

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestManualAuth:
    """Tests for manual authentication verification"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("TEST_USER_EMAIL") or not os.getenv("TEST_USER_PASSWORD"),
        reason="Requires TEST_USER_EMAIL and TEST_USER_PASSWORD environment variables"
    )
    async def test_login_with_env_credentials(self):
        """Test login with credentials from environment variables"""
        test_email = os.getenv("TEST_USER_EMAIL")
        test_password = os.getenv("TEST_USER_PASSWORD")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Enable console logging for debugging
            page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
            page.on("pageerror", lambda err: print(f"Page error: {err}"))
            
            print(f"Attempting login with email: {test_email}")
            
            # Navigate to login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            print(f"Navigated to: {page.url}")
            
            # Fill login form
            await page.fill('input[name="email"]', test_email)
            await page.fill('input[name="password"]', test_password)
            
            # Take screenshot before submit (for debugging)
            await page.screenshot(path="tests/web/screenshots/before-login.png")
            
            # Submit form
            await page.click('button[type="submit"]')
            print("Clicked submit button")
            
            # Wait for navigation or error
            try:
                # Wait for successful redirect to chat
                await page.wait_for_url('**/chat', timeout=10000)
                print(f"✓ Successfully logged in! Now at: {page.url}")
                
                # Verify we're on chat page
                assert page.url.endswith('/chat'), "Should be on chat page"
                
                # Take screenshot of chat page
                await page.screenshot(path="tests/web/screenshots/chat-page.png")
                
                # Check for chat elements
                chat_form = await page.query_selector('#chat-form')
                assert chat_form, "Chat form should be present"
                
                messages = await page.query_selector('#messages')
                assert messages, "Messages container should be present"
                
                # Try sending a test message
                message_input = await page.query_selector('textarea[name="message"]')
                if message_input:
                    await message_input.fill("Hello from browser test!")
                    print("✓ Can interact with chat interface")
                
            except Exception as e:
                print(f"✗ Login failed or timed out: {e}")
                
                # Take screenshot of error state
                await page.screenshot(path="tests/web/screenshots/login-error.png")
                
                # Check for error message
                error = await page.query_selector('[role="alert"]')
                if error:
                    error_text = await error.inner_text()
                    print(f"Error message: {error_text}")
                    pytest.fail(f"Login failed with error: {error_text}")
                else:
                    pytest.fail(f"Login failed: {str(e)}")
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_dev_login_if_available(self):
        """Test dev login (if available in non-production environments)"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Check if dev login button exists
            dev_login_button = await page.query_selector('button:has-text("Dev Login")')
            
            if dev_login_button:
                print("Dev login button found!")
                
                # Click dev login
                await dev_login_button.click()
                
                try:
                    # Should redirect to chat
                    await page.wait_for_url('**/chat', timeout=5000)
                    print("✓ Dev login successful!")
                    assert page.url.endswith('/chat')
                except:
                    error = await page.query_selector('[role="alert"]')
                    if error:
                        error_text = await error.inner_text()
                        print(f"Dev login error: {error_text}")
            else:
                print("No dev login button found (expected in production)")
                pytest.skip("Dev login not available in this environment")
            
            await browser.close()


# Standalone function for manual testing
async def manual_login_test(email: str, password: str, headless: bool = False):
    """
    Manually test login with specific credentials.
    
    Usage:
        python -m pytest tests/web/test_manual_auth_browser.py::manual_login_test \
            --email="user@example.com" --password="password"
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Enable verbose logging
        page.on("console", lambda msg: print(f"[Browser] {msg.type}: {msg.text}"))
        page.on("request", lambda req: print(f"[Request] {req.method} {req.url}"))
        page.on("response", lambda res: print(f"[Response] {res.status} {res.url}"))
        
        try:
            print(f"\n🔐 Testing login for: {email}")
            print(f"🌐 URL: {WEB_SERVICE_URL}")
            
            # Navigate to login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.wait_for_load_state('networkidle')
            
            # Fill form
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            
            # Submit
            print("📤 Submitting login form...")
            await page.click('button[type="submit"]')
            
            # Wait for result
            try:
                await page.wait_for_url('**/chat', timeout=10000)
                print("✅ Login successful! Redirected to chat.")
                
                # Test chat functionality
                chat_form = await page.query_selector('#chat-form')
                if chat_form:
                    print("✅ Chat interface loaded successfully")
                
                # Keep browser open for manual inspection if not headless
                if not headless:
                    print("\n⏸️  Browser will stay open. Press Ctrl+C to close.")
                    await asyncio.sleep(300)  # 5 minutes
                    
            except Exception as e:
                print(f"❌ Login failed: {e}")
                
                # Check for error
                error = await page.query_selector('[role="alert"]')
                if error:
                    error_text = await error.inner_text()
                    print(f"📋 Error message: {error_text}")
                
                # Take screenshot
                await page.screenshot(path="tests/web/screenshots/login-failed.png")
                print("📸 Screenshot saved to tests/web/screenshots/login-failed.png")
                
        finally:
            await browser.close()


if __name__ == "__main__":
    # Check if running as script with arguments
    import sys
    if len(sys.argv) > 1:
        # Parse command line arguments for manual testing
        email = None
        password = None
        headless = True
        
        for i, arg in enumerate(sys.argv):
            if arg.startswith("--email="):
                email = arg.split("=", 1)[1]
            elif arg.startswith("--password="):
                password = arg.split("=", 1)[1]
            elif arg == "--headed":
                headless = False
        
        if email and password:
            asyncio.run(manual_login_test(email, password, headless))
        else:
            print("Usage: python test_manual_auth_browser.py --email=user@example.com --password=pass [--headed]")
    else:
        # Run pytest
        pytest.main([__file__, "-v", "-s"])