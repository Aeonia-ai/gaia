"""
Browser tests with real Supabase authentication.

These tests create real users in Supabase and perform actual login flows.
"""
import pytest
import uuid
import os
from playwright.async_api import async_playwright
import asyncio

# Import the test user factory
from tests.fixtures.test_auth import TestUserFactory

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestRealSupabaseAuth:
    """Test with real Supabase authentication"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_SERVICE_KEY"),
        reason="Requires SUPABASE_SERVICE_KEY environment variable"
    )
    async def test_real_user_registration_and_login(self):
        """Test creating a real user and logging in through the browser"""
        # Generate unique test email
        test_email = f"test-browser-{uuid.uuid4().hex[:8]}@test.local"
        test_password = "TestPassword123!@#"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Track console errors
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
            
            # 1. Register new user
            await page.goto(f'{WEB_SERVICE_URL}/register')
            await page.fill('input[name="email"]', test_email)
            await page.fill('input[name="password"]', test_password)
            await page.click('button[type="submit"]')
            
            # Should see email verification message
            await page.wait_for_selector('text="Check Your Email"', timeout=10000)
            
            # For testing, we'll create a pre-verified user using service key
            factory = TestUserFactory()
            try:
                # Create the same user but pre-verified
                user = factory.create_verified_test_user(
                    email=test_email,
                    password=test_password
                )
                
                # 2. Now try to login with the verified user
                await page.goto(f'{WEB_SERVICE_URL}/login')
                await page.fill('input[name="email"]', test_email)
                await page.fill('input[name="password"]', test_password)
                await page.click('button[type="submit"]')
                
                # Should redirect to chat
                await page.wait_for_url('**/chat', timeout=10000)
                
                # Verify we're on chat page
                assert page.url.endswith('/chat'), "Should be redirected to chat after login"
                
                # Check for chat elements
                chat_form = await page.query_selector('#chat-form')
                assert chat_form, "Chat form should be present"
                
                # Verify we have a real session cookie
                cookies = await page.context.cookies()
                session_cookie = next((c for c in cookies if c['name'] == 'session'), None)
                assert session_cookie is not None, "Should have session cookie"
                assert session_cookie['value'], "Session cookie should have a value"
                
                # 3. Test logout
                logout_button = await page.query_selector('button:has-text("Logout")')
                if not logout_button:
                    logout_button = await page.query_selector('a[href="/auth/logout"]')
                
                if logout_button:
                    await logout_button.click()
                    await page.wait_for_url('**/login', timeout=5000)
                    assert page.url.endswith('/login'), "Should redirect to login after logout"
                
                # No console errors
                assert len(console_errors) == 0, f"Console errors found: {[e.text for e in console_errors]}"
                
            finally:
                # Always cleanup test user
                factory.cleanup()
                await browser.close()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_SERVICE_KEY"),
        reason="Requires SUPABASE_SERVICE_KEY environment variable"
    )
    async def test_real_login_with_wrong_password(self):
        """Test login failure with real Supabase user"""
        factory = TestUserFactory()
        test_email = f"test-{uuid.uuid4().hex[:8]}@test.local"
        test_password = "CorrectPassword123!"
        
        # Create real user
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
                page = await browser.new_page()
                
                # Try to login with wrong password
                await page.goto(f'{WEB_SERVICE_URL}/login')
                await page.fill('input[name="email"]', test_email)
                await page.fill('input[name="password"]', 'WrongPassword123!')
                await page.click('button[type="submit"]')
                
                # Should show error message
                error_message = await page.wait_for_selector('[role="alert"]', timeout=5000)
                error_text = await error_message.inner_text()
                
                # Error should mention invalid credentials
                assert "Invalid" in error_text or "incorrect" in error_text.lower(), \
                    f"Should show invalid credentials error, got: {error_text}"
                
                # Should still be on login page
                assert page.url.endswith('/login'), "Should remain on login page after failed login"
                
                await browser.close()
        finally:
            factory.cleanup()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_SERVICE_KEY"),
        reason="Requires SUPABASE_SERVICE_KEY environment variable"
    )
    async def test_concurrent_user_sessions(self):
        """Test multiple users logged in simultaneously"""
        factory = TestUserFactory()
        
        # Create two test users
        user1_email = f"alice-{uuid.uuid4().hex[:8]}@test.local"
        user1_password = "AlicePassword123!"
        user2_email = f"bob-{uuid.uuid4().hex[:8]}@test.local"
        user2_password = "BobPassword123!"
        
        user1 = factory.create_verified_test_user(email=user1_email, password=user1_password)
        user2 = factory.create_verified_test_user(email=user2_email, password=user2_password)
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                # Create two separate browser contexts (like different browsers)
                context1 = await browser.new_context()
                context2 = await browser.new_context()
                
                page1 = await context1.new_page()
                page2 = await context2.new_page()
                
                # Login user 1
                await page1.goto(f'{WEB_SERVICE_URL}/login')
                await page1.fill('input[name="email"]', user1_email)
                await page1.fill('input[name="password"]', user1_password)
                await page1.click('button[type="submit"]')
                await page1.wait_for_url('**/chat', timeout=10000)
                
                # Login user 2
                await page2.goto(f'{WEB_SERVICE_URL}/login')
                await page2.fill('input[name="email"]', user2_email)
                await page2.fill('input[name="password"]', user2_password)
                await page2.click('button[type="submit"]')
                await page2.wait_for_url('**/chat', timeout=10000)
                
                # Both should be on chat
                assert page1.url.endswith('/chat')
                assert page2.url.endswith('/chat')
                
                # Get session cookies
                cookies1 = await context1.cookies()
                cookies2 = await context2.cookies()
                
                session1 = next((c for c in cookies1 if c['name'] == 'session'), None)
                session2 = next((c for c in cookies2 if c['name'] == 'session'), None)
                
                # Both should have sessions
                assert session1 and session1['value']
                assert session2 and session2['value']
                
                # Sessions should be different
                assert session1['value'] != session2['value'], "Each user should have unique session"
                
                await context1.close()
                await context2.close()
                await browser.close()
        finally:
            factory.cleanup()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_SERVICE_KEY"),
        reason="Requires SUPABASE_SERVICE_KEY environment variable"
    )
    async def test_session_persistence_across_page_refresh(self):
        """Test that real Supabase session persists across page refreshes"""
        factory = TestUserFactory()
        test_email = f"test-{uuid.uuid4().hex[:8]}@test.local"
        test_password = "TestPassword123!"
        
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
                
                # Login
                await page.goto(f'{WEB_SERVICE_URL}/login')
                await page.fill('input[name="email"]', test_email)
                await page.fill('input[name="password"]', test_password)
                await page.click('button[type="submit"]')
                await page.wait_for_url('**/chat', timeout=10000)
                
                # Get initial session
                initial_cookies = await context.cookies()
                initial_session = next((c for c in initial_cookies if c['name'] == 'session'), None)
                assert initial_session, "Should have session after login"
                
                # Refresh the page
                await page.reload()
                await page.wait_for_load_state('networkidle')
                
                # Should still be on chat (not redirected to login)
                assert page.url.endswith('/chat'), "Should stay on chat after refresh"
                
                # Session should persist
                refreshed_cookies = await context.cookies()
                refreshed_session = next((c for c in refreshed_cookies if c['name'] == 'session'), None)
                assert refreshed_session, "Session should persist after refresh"
                
                # Navigate to another page and back
                await page.goto(f'{WEB_SERVICE_URL}/')
                await page.goto(f'{WEB_SERVICE_URL}/chat')
                
                # Should still be authenticated
                assert page.url.endswith('/chat'), "Should stay authenticated across navigation"
                
                await browser.close()
        finally:
            factory.cleanup()


class TestRealAuthEdgeCases:
    """Test edge cases with real authentication"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_SERVICE_KEY"),
        reason="Requires SUPABASE_SERVICE_KEY environment variable"
    )
    async def test_login_with_unverified_email(self):
        """Test login attempt with unverified email"""
        # This test would require creating an unverified user
        # which is more complex with Supabase
        # For now, we'll skip implementation
        pytest.skip("Unverified email testing requires email service setup")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("SUPABASE_SERVICE_KEY"),
        reason="Requires SUPABASE_SERVICE_KEY environment variable"
    )
    async def test_registration_with_existing_email(self):
        """Test registration with email that already exists"""
        factory = TestUserFactory()
        test_email = f"existing-{uuid.uuid4().hex[:8]}@test.local"
        test_password = "TestPassword123!"
        
        # Create user first
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
                page = await browser.new_page()
                
                # Try to register with same email
                await page.goto(f'{WEB_SERVICE_URL}/register')
                await page.fill('input[name="email"]', test_email)
                await page.fill('input[name="password"]', 'NewPassword123!')
                await page.click('button[type="submit"]')
                
                # Should show error
                error = await page.wait_for_selector('[role="alert"]', timeout=5000)
                error_text = await error.inner_text()
                
                # Should mention email already exists
                assert "already" in error_text.lower() or "exists" in error_text.lower(), \
                    f"Should show email exists error, got: {error_text}"
                
                await browser.close()
        finally:
            factory.cleanup()


# Helper function to run specific auth test
async def test_specific_user_login(email: str, password: str):
    """Helper to test login with specific credentials"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser for debugging
            slow_mo=500  # Slow down actions
        )
        page = await browser.new_page()
        
        try:
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            
            # Wait for either chat or error
            try:
                await page.wait_for_url('**/chat', timeout=10000)
                print(f"✓ Successfully logged in as {email}")
                return True
            except:
                error = await page.query_selector('[role="alert"]')
                if error:
                    error_text = await error.inner_text()
                    print(f"✗ Login failed: {error_text}")
                return False
        finally:
            await browser.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])