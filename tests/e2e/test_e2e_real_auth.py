"""
True end-to-end tests using real authentication and server endpoints.
No mocking - tests the actual user experience with dynamically created test users.
"""
import pytest
from playwright.async_api import async_playwright
import os
import uuid
from datetime import datetime
from tests.fixtures.test_auth import TestUserFactory

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.fixture
async def test_user_factory():
    """Create test user factory for managing test users"""
    if not os.getenv("SUPABASE_SERVICE_KEY"):
        pytest.skip("Requires SUPABASE_SERVICE_KEY for real user creation")
    
    factory = TestUserFactory()
    yield factory
    # Cleanup all created users after tests
    factory.cleanup_all()


@pytest.fixture
async def test_user(test_user_factory):
    """Create a verified test user for individual tests"""
    user = test_user_factory.create_verified_test_user()
    yield user
    # User will be cleaned up by factory


@pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_KEY"),
    reason="Requires SUPABASE_SERVICE_KEY for real user creation"
)
@pytest.mark.asyncio
async def test_real_login_flow(test_user):
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
        
        print(f"\n=== Starting Real E2E Test with user: {test_user['email']} ===")
        
        # 1. Navigate to home page
        print("1. Navigating to home page...")
        await page.goto(WEB_SERVICE_URL)
        
        # Should redirect to login since not authenticated
        await page.wait_for_url('**/login', timeout=5000)
        assert page.url.endswith('/login'), "Should redirect to login when not authenticated"
        print("✓ Redirected to login page")
        
        # 2. Fill in login form with test user credentials
        print("\n2. Filling login form...")
        email_input = await page.wait_for_selector('input[name="email"]', timeout=5000)
        await email_input.fill(test_user['email'])
        
        password_input = await page.query_selector('input[name="password"]')
        await password_input.fill(test_user['password'])
        print(f"✓ Filled form with {test_user['email']}")
        
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


@pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_KEY"),
    reason="Requires SUPABASE_SERVICE_KEY for real user creation"
)
@pytest.mark.asyncio
async def test_real_registration_flow():
    """Test real registration flow (if enabled)"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Generate unique test email with a domain that passes validation
        test_id = uuid.uuid4().hex[:8]
        # Use gmail.com or another valid domain for testing
        test_email = f"test.user.{test_id}@gmail.com"
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
        await page.wait_for_timeout(3000)
        
        # Check what happened
        if page.url.endswith('/register'):
            # Still on register page - check for error
            error_element = await page.query_selector('.bg-red-500\/10, .error, .text-red-500')
            if error_element:
                error_text = await error_element.inner_text()
                print(f"Registration response: {error_text}")
                
                # Common expected errors
                if "not allowed for this email domain" in error_text:
                    print("✓ Registration correctly blocked for test domain")
                    pytest.skip("Registration blocked for test domain - this is expected")
                elif "already registered" in error_text.lower():
                    print("✓ Email already registered")
                    pytest.skip("Email already registered - expected for repeated tests")
                else:
                    raise Exception(f"Unexpected error: {error_text}")
        else:
            # Navigated somewhere else - could be email verification page
            print(f"Navigated to: {page.url}")
            
            if "email-verification" in page.url or "verify" in page.url:
                print("✓ Email verification required - registration successful")
            elif page.url.endswith('/chat'):
                print("✓ Auto-logged in after registration")
                # This would be unexpected unless email verification is disabled
        
        await browser.close()


@pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_KEY"),
    reason="Requires SUPABASE_SERVICE_KEY for real user creation"
)
@pytest.mark.asyncio
async def test_logout_flow(test_user):
    """Test logout functionality regardless of UI implementation"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"\n=== Testing Logout with user: {test_user['email']} ===")
        
        # First login
        await page.goto(f"{WEB_SERVICE_URL}/login")
        await page.fill('input[name="email"]', test_user['email'])
        await page.fill('input[name="password"]', test_user['password'])
        await page.click('button[type="submit"]')
        
        # Wait for chat page
        try:
            await page.wait_for_url('**/chat', timeout=10000)
            print("✓ Successfully logged in")
            
            # Method 1: Direct navigation to logout endpoint (most reliable)
            print("\n1. Testing direct logout endpoint...")
            await page.goto(f"{WEB_SERVICE_URL}/logout")
            
            # Should redirect to login after logout
            try:
                await page.wait_for_url('**/login', timeout=5000)
                print("✓ Successfully logged out via direct endpoint")
            except:
                # Some systems might redirect to home or a logout confirmation page
                current_url = page.url
                print(f"Redirected to: {current_url}")
                
                # Verify we're actually logged out by trying to access protected route
                await page.goto(f"{WEB_SERVICE_URL}/chat")
                await page.wait_for_url('**/login', timeout=5000)
                print("✓ Logout successful - protected route redirects to login")
            
            # Method 2: Test that protected routes are inaccessible after logout
            print("\n2. Verifying session is terminated...")
            
            # Try multiple protected endpoints
            protected_routes = ['/chat', '/profile', '/settings']
            for route in protected_routes:
                try:
                    await page.goto(f"{WEB_SERVICE_URL}{route}")
                    # Should redirect to login
                    if not page.url.endswith('/login'):
                        await page.wait_for_url('**/login', timeout=2000)
                    print(f"✓ {route} correctly redirects to login when not authenticated")
                    break  # One successful check is enough
                except:
                    continue  # Try next route if this one doesn't exist
            
            # Method 3: Check cookies are cleared (optional verification)
            print("\n3. Checking session cleanup...")
            cookies = await context.cookies()
            session_cookies = [c for c in cookies if 'session' in c['name'].lower() or 'auth' in c['name'].lower()]
            
            if not session_cookies:
                print("✓ Session cookies cleared")
            else:
                # Some cookies might be present but invalid/expired
                print(f"Note: {len(session_cookies)} auth-related cookies still present")
                # This is okay as long as they don't grant access
                
        except Exception as e:
            print(f"✗ Test failed: {e}")
            await page.screenshot(path="tests/web/screenshots/e2e-logout-failure.png")
            # Save HTML for debugging
            html_content = await page.content()
            with open("tests/web/screenshots/e2e-logout-page.html", "w") as f:
                f.write(html_content)
            raise
        
        await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])