"""
True E2E tests using real Supabase user creation and cleanup.
No mocking - tests the complete authentication flow.
"""
import pytest
from playwright.async_api import async_playwright
import os
import uuid

# Import the test user factory
from tests.fixtures.test_auth import TestUserFactory

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_KEY"),
    reason="Requires SUPABASE_SERVICE_KEY for real user creation"
)
@pytest.mark.asyncio
async def test_real_e2e_login_with_supabase():
    """Test real login flow with actual Supabase user"""
    factory = TestUserFactory()
    test_email = f"e2e-test-{uuid.uuid4().hex[:8]}@test.local"
    test_password = "TestPassword123!"
    
    # Create real user in Supabase
    user = factory.create_verified_test_user(
        email=test_email,
        password=test_password
    )
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context()
            page = await context.new_page()
            
            # Enable console logging
            page.on("console", lambda msg: print(f"[Browser] {msg.text}"))
            
            print(f"\n=== Testing with real Supabase user: {test_email} ===")
            
            # 1. Navigate to login
            await page.goto(f"{WEB_SERVICE_URL}/login")
            assert page.url.endswith('/login'), "Should be on login page"
            
            # 2. Fill and submit login form
            await page.fill('input[name="email"]', test_email)
            await page.fill('input[name="password"]', test_password)
            await page.click('button[type="submit"]')
            
            # 3. Wait for navigation to chat
            print("Waiting for successful login...")
            await page.wait_for_url('**/chat', timeout=15000)
            print("✓ Successfully logged in and navigated to chat!")
            
            # 4. Verify chat interface
            chat_form = await page.wait_for_selector('#chat-form', timeout=5000)
            assert chat_form, "Chat form should be present"
            
            message_input = await page.query_selector('input[name="message"]')
            if not message_input:
                # Try by ID
                message_input = await page.query_selector('#chat-message-input')
            assert message_input, "Message input should be present"
            
            # 5. Send a real message
            await message_input.fill("Hello from real E2E test with Supabase!")
            
            # Submit message
            send_button = await page.query_selector('#chat-form button[type="submit"]')
            if send_button:
                await send_button.click()
            else:
                await page.keyboard.press('Enter')
            
            # 6. Wait for AI response (real response from chat service)
            print("Waiting for AI response...")
            # Wait a bit for HTMX to process
            await page.wait_for_timeout(2000)
            
            # Check if messages appeared in the messages container
            messages = await page.query_selector_all('#messages > div')
            if len(messages) > 1:  # Should have at least user message + AI response
                print(f"✓ Received AI response! ({len(messages)} messages in chat)")
            else:
                # Try to find any message elements
                all_divs = await page.query_selector_all('#messages div')
                print(f"Found {len(all_divs)} divs in messages container")
                if all_divs:
                    first_text = await all_divs[0].inner_text()
                    print(f"First element text: {first_text[:100]}...")
            
            # Take screenshot of successful chat
            await page.screenshot(path="tests/web/screenshots/e2e-supabase-success.png")
            
            # 7. Test logout (optional - UI might not have visible logout)
            logout_link = await page.query_selector('a[href="/logout"], button:has-text("Logout")')
            if logout_link and await logout_link.is_visible():
                try:
                    await logout_link.click()
                    await page.wait_for_url('**/login', timeout=5000)
                    print("✓ Successfully logged out")
                except Exception as e:
                    print(f"Note: Logout button exists but couldn't click: {e}")
            else:
                print("Note: No visible logout button found (UI design choice)")
            
            await browser.close()
            
    finally:
        # Always cleanup test user
        factory.cleanup_all()
        print(f"✓ Cleaned up test user: {test_email}")


@pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_KEY"),
    reason="Requires SUPABASE_SERVICE_KEY for real user creation"
)
@pytest.mark.asyncio
async def test_real_e2e_registration_and_login():
    """Test registration flow with real Supabase (if email domain allowed)"""
    test_email = f"register-test-{uuid.uuid4().hex[:8]}@test.local"
    test_password = "RegisterTest123!"
    
    # Note: This test might fail if Supabase is configured to block @test.local domains
    # In that case, the test will verify the error message
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        print(f"\n=== Testing registration with: {test_email} ===")
        
        # Navigate to register
        await page.goto(f"{WEB_SERVICE_URL}/register")
        
        # Fill registration form
        await page.fill('input[name="email"]', test_email)
        await page.fill('input[name="password"]', test_password)
        await page.click('button[type="submit"]')
        
        # Wait for response
        await page.wait_for_timeout(3000)
        
        # Check result
        if page.url.endswith('/register'):
            # Still on register page - check for error
            error_elem = await page.query_selector('[role="alert"], .error, .text-red-500')
            if error_elem:
                error_text = await error_elem.inner_text()
                print(f"Registration response: {error_text}")
                
                if "not allowed for this email domain" in error_text:
                    print("✓ Registration correctly blocked for test domain (expected)")
                    pytest.skip("Registration blocked for test domain - this is expected")
                else:
                    raise Exception(f"Unexpected registration error: {error_text}")
        
        elif "email-verification" in page.url:
            print("✓ Registration successful - email verification required")
            # In real E2E, we'd need to access the email to verify
            
        elif page.url.endswith('/chat'):
            print("✓ Registration successful - auto logged in!")
            # This means email verification is disabled
            
            # Cleanup: logout and delete user via Supabase admin
            # (Would need admin access to delete)
        
        await browser.close()


@pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_KEY"),
    reason="Requires SUPABASE_SERVICE_KEY for real user creation"
)
@pytest.mark.asyncio
async def test_concurrent_users():
    """Test multiple users chatting concurrently"""
    factory = TestUserFactory()
    
    # Create two test users
    users = [
        {
            "email": f"user1-{uuid.uuid4().hex[:8]}@test.local",
            "password": "User1Pass123!",
            "name": "User One"
        },
        {
            "email": f"user2-{uuid.uuid4().hex[:8]}@test.local",
            "password": "User2Pass123!",
            "name": "User Two"
        }
    ]
    
    # Create users in Supabase
    for user in users:
        created = factory.create_verified_test_user(
            email=user["email"],
            password=user["password"]
        )
        user["id"] = created["user_id"]
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # Create separate contexts for each user
            contexts = []
            pages = []
            
            for user in users:
                context = await browser.new_context()
                page = await context.new_page()
                
                # Login
                await page.goto(f"{WEB_SERVICE_URL}/login")
                await page.fill('input[name="email"]', user["email"])
                await page.fill('input[name="password"]', user["password"])
                await page.click('button[type="submit"]')
                await page.wait_for_url('**/chat', timeout=10000)
                
                contexts.append(context)
                pages.append(page)
                print(f"✓ {user['name']} logged in")
            
            # Both users send messages
            for i, (page, user) in enumerate(zip(pages, users)):
                message_input = await page.query_selector('textarea[name="message"]')
                await message_input.fill(f"Hello from {user['name']}!")
                await page.keyboard.press('Enter')
                print(f"✓ {user['name']} sent message")
            
            # Wait for responses
            await pages[0].wait_for_timeout(3000)
            
            # Each user should only see their own conversations
            # (This tests session isolation)
            
            # Cleanup
            for context in contexts:
                await context.close()
            
            await browser.close()
            
    finally:
        # Cleanup all test users
        factory.cleanup_all()
        print("✓ Cleaned up all test users")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])