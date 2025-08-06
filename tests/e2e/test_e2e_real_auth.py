"""
True end-to-end tests using real authentication and server endpoints.
No mocking - tests the actual user experience.
"""
import pytest
from playwright.async_api import async_playwright
import os
import uuid
from datetime import datetime

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")

# Test with real dev credentials if in debug mode
# Otherwise, would need to create real users via Supabase
DEV_EMAIL = "dev@gaia.local"
DEV_PASSWORD = "testtest"


@pytest.mark.asyncio
async def test_real_login_flow():
    """Test real login flow without any mocking"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # Create a new context with no pre-existing cookies/session
        context = await browser.new_context()
        page = await context.new_page()
        
        # Enable console logging for debugging
        page.on("console", lambda msg: print(f"[Browser Console] {msg.text}"))
        
        print("\n=== Starting Real E2E Test ===")
        
        # 1. Navigate to home page
        print("1. Navigating to home page...")
        await page.goto(WEB_SERVICE_URL)
        
        # Should redirect to login since not authenticated
        await page.wait_for_url('**/login', timeout=5000)
        assert page.url.endswith('/login'), "Should redirect to login when not authenticated"
        print("✓ Redirected to login page")
        
        # 2. Fill in login form with real credentials
        print("\n2. Filling login form...")
        email_input = await page.wait_for_selector('input[name="email"]', timeout=5000)
        await email_input.fill(DEV_EMAIL)
        
        password_input = await page.query_selector('input[name="password"]')
        await password_input.fill(DEV_PASSWORD)
        print(f"✓ Filled form with {DEV_EMAIL}")
        
        # 3. Submit form and wait for navigation
        print("\n3. Submitting login form...")
        submit_button = await page.query_selector('button[type="submit"]')
        await submit_button.click()
        
        # Wait for either successful navigation to chat or error message
        try:
            # Try to wait for navigation to chat
            await page.wait_for_url('**/chat', timeout=10000)
            print("✓ Successfully navigated to chat!")
            
            # 4. Verify we're on the chat page
            print("\n4. Verifying chat page...")
            assert page.url.endswith('/chat'), "Should be on chat page"
            
            # Wait for chat interface to load
            chat_form = await page.wait_for_selector('form', timeout=5000)
            assert chat_form, "Chat form should be present"
            print("✓ Chat form loaded")
            
            message_input = await page.query_selector('input[name="message"]')
            assert message_input, "Message input should be present"
            print("✓ Message input found")
            
            # 5. Try sending a message
            print("\n5. Sending a test message...")
            await message_input.fill("Hello from E2E test!")
            
            # Look for send button or use Enter
            send_button = await page.query_selector('form button[type="submit"]')
            if send_button:
                await send_button.click()
            else:
                await page.keyboard.press('Enter')
            
            print("✓ Message sent")
            
            # 6. Wait for response (this would be from real chat service)
            print("\n6. Waiting for AI response...")
            # In real E2E, we'd wait for actual response element
            # For now, just wait a bit
            await page.wait_for_timeout(2000)
            
            # Take screenshot of successful chat
            await page.screenshot(path="tests/web/screenshots/e2e-chat-success.png")
            print("✓ Screenshot saved")
            
        except Exception as e:
            # Login failed - check for error message
            print(f"✗ Login failed: {e}")
            
            # Look for error message on page
            error_element = await page.query_selector('.bg-red-500\/10, .error, .text-red-500')
            if error_element:
                error_text = await error_element.inner_text()
                print(f"Error message: {error_text}")
            
            # Take screenshot of failure
            await page.screenshot(path="tests/web/screenshots/e2e-login-failure.png")
            
            # Re-raise the exception
            raise e
        
        finally:
            await browser.close()
            print("\n=== E2E Test Complete ===")


@pytest.mark.asyncio
async def test_real_registration_flow():
    """Test real registration flow (if enabled)"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Generate unique test email
        test_id = uuid.uuid4().hex[:8]
        test_email = f"test-{test_id}@test.local"
        test_password = "TestPass123!"
        
        print(f"\n=== Testing Registration with {test_email} ===")
        
        # Navigate to registration page
        await page.goto(f"{WEB_SERVICE_URL}/register")
        
        # Fill registration form
        await page.fill('input[name="email"]', test_email)
        await page.fill('input[name="password"]', test_password)
        
        # Submit form
        await page.click('button[type="submit"]')
        
        # Wait for response
        await page.wait_for_timeout(2000)
        
        # Check what happened
        if page.url.endswith('/register'):
            # Still on register page - check for error
            error_element = await page.query_selector('.bg-red-500\/10, .error')
            if error_element:
                error_text = await error_element.inner_text()
                print(f"Registration error: {error_text}")
                
                # This is expected if registration is restricted
                if "not allowed for this email domain" in error_text:
                    print("✓ Registration correctly blocked for test domain")
                else:
                    raise Exception(f"Unexpected error: {error_text}")
        else:
            # Navigated somewhere else - could be email verification page
            print(f"Navigated to: {page.url}")
            
            if "email-verification" in page.url:
                print("✓ Email verification required")
            elif page.url.endswith('/chat'):
                print("✓ Auto-logged in after registration")
        
        await browser.close()


@pytest.mark.asyncio
async def test_logout_flow():
    """Test logout functionality"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        # First login
        await page.goto(f"{WEB_SERVICE_URL}/login")
        await page.fill('input[name="email"]', DEV_EMAIL)
        await page.fill('input[name="password"]', DEV_PASSWORD)
        await page.click('button[type="submit"]')
        
        # Wait for chat page
        try:
            await page.wait_for_url('**/chat', timeout=10000)
            
            # Now test logout
            print("\n=== Testing Logout ===")
            
            # Look for logout link/button
            logout_link = await page.query_selector('a[href="/logout"], button:has-text("Logout")')
            if logout_link:
                await logout_link.click()
                
                # Should redirect to login
                await page.wait_for_url('**/login', timeout=5000)
                print("✓ Successfully logged out")
                
                # Try to access chat directly
                await page.goto(f"{WEB_SERVICE_URL}/chat")
                
                # Should redirect back to login
                await page.wait_for_url('**/login', timeout=5000)
                print("✓ Protected route correctly redirects to login")
            else:
                print("✗ Logout link not found")
                
        except Exception as e:
            print(f"✗ Login failed, cannot test logout: {e}")
            raise
        
        await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])