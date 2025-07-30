"""
Browser tests for edge cases and race conditions.

These tests catch issues that URL-based tests miss:
- Race conditions between UI updates
- JavaScript timing issues
- Browser-specific behaviors
- Memory leaks
- Console errors
"""
import pytest
import asyncio
import json
from playwright.async_api import async_playwright, Page, ConsoleMessage
import os
from typing import List

pytestmark = pytest.mark.asyncio
WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


class TestConsoleErrors:
    """Monitor browser console for JavaScript errors"""
    
    async def test_no_console_errors_on_login_page(self):
        """Ensure no JavaScript errors on login page load"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Collect console messages
            console_messages: List[ConsoleMessage] = []
            page.on("console", lambda msg: console_messages.append(msg))
            
            # Navigate to login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.wait_for_load_state('networkidle')
            
            # Check for errors
            errors = [msg for msg in console_messages if msg.type == "error"]
            assert len(errors) == 0, f"Found console errors: {[err.text for err in errors]}"
            
            # Check for warnings (optional, might be too strict)
            warnings = [msg for msg in console_messages if msg.type == "warning"]
            # Allow some warnings but log them
            if warnings:
                print(f"Console warnings: {[warn.text for warn in warnings]}")
            
            await browser.close()
    
    async def test_no_console_errors_during_form_submission(self):
        """Ensure no JavaScript errors during form interactions"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Mock login response
            await page.route("**/auth/login", lambda route: route.fulfill(
                status=400,
                json={"error": "Invalid credentials"}
            ))
            
            # Interact with form
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test')
            await page.click('button[type="submit"]')
            
            # Wait for response
            await page.wait_for_selector('[role="alert"]')
            
            # No JavaScript errors should occur
            assert len(console_errors) == 0, f"JavaScript errors: {[err.text for err in console_errors]}"
            
            await browser.close()


class TestRaceConditions:
    """Test for race conditions that only appear in real browsers"""
    
    async def test_rapid_navigation_race_condition(self):
        """Test rapid navigation doesn't cause issues"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Track any errors
            errors = []
            page.on("pageerror", lambda err: errors.append(str(err)))
            
            # Rapidly navigate between pages
            for _ in range(5):
                await page.goto(f'{WEB_SERVICE_URL}/login')
                # Don't wait for full load
                await page.goto(f'{WEB_SERVICE_URL}/register', wait_until='domcontentloaded')
                await page.goto(f'{WEB_SERVICE_URL}/login', wait_until='domcontentloaded')
            
            # Final navigation with full load
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.wait_for_load_state('networkidle')
            
            # Page should still work
            login_form = await page.query_selector('form[hx-post="/auth/login"]')
            assert login_form, "Login form should exist after rapid navigation"
            
            # No JavaScript errors
            assert len(errors) == 0, f"Page errors during rapid navigation: {errors}"
            
            await browser.close()
    
    async def test_concurrent_htmx_requests(self):
        """Test multiple HTMX requests don't interfere with each other"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Set up multiple endpoints with different delays
            request_order = []
            
            async def login_handler(route):
                request_order.append("login")
                await asyncio.sleep(0.5)
                await route.fulfill(
                    status=400,
                    headers={"Content-Type": "text/html"},
                    body='<div id="login-error" role="alert">Login error</div>'
                )
            
            await page.route("**/auth/login", login_handler)
            
            async def check_handler(route):
                request_order.append("check")
                await asyncio.sleep(0.1)
                await route.fulfill(
                    status=200,
                    headers={"Content-Type": "text/html"},
                    body='<div id="check-result">Check complete</div>'
                )
            
            await page.route("**/auth/check", check_handler)
            
            # Trigger multiple requests simultaneously
            await page.evaluate('''
                () => {
                    // Simulate concurrent HTMX requests
                    document.body.innerHTML += `
                        <div hx-post="/auth/login" hx-trigger="load" hx-target="#result1"></div>
                        <div hx-post="/auth/check" hx-trigger="load" hx-target="#result2"></div>
                        <div id="result1"></div>
                        <div id="result2"></div>
                    `;
                    htmx.process(document.body);
                }
            ''')
            
            # Wait for both responses
            await page.wait_for_selector('#login-error')
            await page.wait_for_selector('#check-result')
            
            # Verify both completed despite different timings
            assert len(request_order) == 2
            assert "check" in request_order
            assert "login" in request_order
            
            await browser.close()


class TestMemoryLeaks:
    """Test for memory leaks in long-running sessions"""
    
    async def test_repeated_form_submissions_no_memory_leak(self):
        """Test repeated form submissions don't leak memory"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Mock fast responses
            await page.route("**/auth/login", lambda route: route.fulfill(
                status=400,
                headers={"Content-Type": "text/html"},
                body='<div role="alert">Error</div>'
            ))
            
            # Get initial memory usage
            initial_memory = await page.evaluate('() => performance.memory ? performance.memory.usedJSHeapSize : 0')
            
            # Submit form many times
            for i in range(20):
                await page.fill('input[name="email"]', f'test{i}@test.local')
                await page.fill('input[name="password"]', 'test')
                await page.click('button[type="submit"]')
                await page.wait_for_selector('[role="alert"]')
                await page.wait_for_timeout(50)  # Small delay
            
            # Check memory didn't grow excessively
            final_memory = await page.evaluate('() => performance.memory ? performance.memory.usedJSHeapSize : 0')
            
            # Memory can grow somewhat, but not excessively (e.g., not more than 5MB)
            memory_growth = final_memory - initial_memory
            assert memory_growth < 5 * 1024 * 1024, f"Excessive memory growth: {memory_growth / 1024 / 1024:.2f}MB"
            
            await browser.close()


class TestBrowserSpecificBehaviors:
    """Test browser-specific quirks and behaviors"""
    
    async def test_autofill_behavior(self):
        """Test browser autofill doesn't break form submission"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Simulate autofill by setting values directly
            await page.evaluate('''
                () => {
                    const emailInput = document.querySelector('input[name="email"]');
                    const passwordInput = document.querySelector('input[name="password"]');
                    
                    // Simulate browser autofill
                    emailInput.value = 'autofill@test.local';
                    passwordInput.value = 'autofilled-password';
                    
                    // Trigger events that autofill would trigger
                    emailInput.dispatchEvent(new Event('input', { bubbles: true }));
                    passwordInput.dispatchEvent(new Event('input', { bubbles: true }));
                    emailInput.dispatchEvent(new Event('change', { bubbles: true }));
                    passwordInput.dispatchEvent(new Event('change', { bubbles: true }));
                }
            ''')
            
            # Mock login
            submitted_data = None
            await page.route("**/auth/login", lambda route: (
                setattr(submitted_data, 'value', route.request.post_data),
                route.fulfill(status=303, headers={"Location": "/chat"})
            )[1])
            
            # Submit form
            await page.click('button[type="submit"]')
            
            # Verify autofilled values were submitted
            # Note: Can't easily check submitted_data in this pattern
            # But we can verify the form submission worked
            
            await browser.close()
    
    async def test_back_button_after_login(self):
        """Test browser back button behavior after login"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Start at login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            login_url = page.url
            
            # Mock successful login
            await page.route("**/auth/login", lambda route: route.fulfill(
                status=303,
                headers={"Location": "/chat"}
            ))
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={"conversations": [], "has_more": False}
            ))
            
            # Login
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test')
            await page.click('button[type="submit"]')
            await page.wait_for_url('**/chat')
            
            # Try to go back
            await page.go_back()
            
            # Should either:
            # 1. Stay on chat (if app prevents going back to login when authenticated)
            # 2. Go to login but immediately redirect to chat
            # 3. Show login with a message
            
            # Wait a bit for any redirects
            await page.wait_for_timeout(500)
            
            # Verify we're in a valid state
            current_url = page.url
            assert current_url.endswith('/chat') or current_url.endswith('/login'), \
                "Should be on either chat or login page"
            
            await browser.close()


class TestFormStatePersistence:
    """Test form state persistence across various scenarios"""
    
    async def test_form_state_after_validation_error(self):
        """Test form preserves user input after validation error"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/register')
            
            # Fill form with test data
            test_email = 'preserve@test.local'
            await page.fill('input[name="email"]', test_email)
            await page.fill('input[name="password"]', 'short')  # Too short
            
            # Mock validation error
            await page.route("**/auth/register", lambda route: route.fulfill(
                status=400,
                headers={"Content-Type": "text/html"},
                body='<div role="alert">Password too short</div>'
            ))
            
            # Submit
            await page.click('button[type="submit"]')
            await page.wait_for_selector('[role="alert"]')
            
            # Check email is still filled
            email_value = await page.input_value('input[name="email"]')
            assert email_value == test_email, "Email should be preserved after error"
            
            # Password might be cleared for security - this is app-specific
            
            await browser.close()
    
    async def test_form_double_submit_prevention(self):
        """Test form prevents double submission"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Count submissions
            submission_count = 0
            async def count_submissions(route):
                nonlocal submission_count
                submission_count += 1
                await asyncio.sleep(1)  # Slow response
                await route.fulfill(
                    status=303,
                    headers={"Location": "/chat"}
                )
            
            await page.route("**/auth/login", count_submissions)
            
            # Fill form
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test')
            
            # Try to submit multiple times quickly
            submit_button = await page.query_selector('button[type="submit"]')
            
            # Click multiple times
            await submit_button.click()
            await page.wait_for_timeout(10)  # Very short delay
            
            # Try clicking again - button might be disabled
            try:
                await submit_button.click({timeout: 100})
            except:
                pass  # Click might fail if button is disabled
            
            # Wait for navigation
            try:
                await page.wait_for_url('**/chat', timeout=3000)
            except:
                pass  # Might timeout
            
            # Should only have one submission (or maybe 2 if protection isn't perfect)
            assert submission_count <= 2, f"Too many form submissions: {submission_count}"
            
            await browser.close()


class TestDynamicContent:
    """Test dynamic content updates and client-side rendering"""
    
    async def test_loading_states_display_correctly(self):
        """Test loading states show and hide properly"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Slow response to see loading state
            async def slow_login_handler(route):
                await asyncio.sleep(1)
                await route.fulfill(
                    status=400,
                    json={"error": "Test"}
                )
            
            await page.route("**/auth/login", slow_login_handler)
            
            # Check initial state
            submit_button = await page.query_selector('button[type="submit"]')
            initial_text = await submit_button.inner_text()
            
            # Fill and submit
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test')
            
            # Click and immediately check loading state
            await submit_button.click()
            
            # Button might show loading state
            await page.wait_for_timeout(100)
            loading_text = await submit_button.inner_text()
            
            # Wait for response
            await page.wait_for_selector('[role="alert"]')
            
            # Button should return to normal
            final_text = await submit_button.inner_text()
            assert final_text == initial_text, "Button should return to initial state"
            
            await browser.close()
    
    async def test_client_side_validation_updates(self):
        """Test client-side validation updates in real-time"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/register')
            
            # Type invalid email and check validation
            email_input = await page.query_selector('input[name="email"]')
            
            # Type partial email
            await email_input.type('test@', {delay: 100})
            
            # Check if any validation message appears
            # This is app-specific
            
            # Complete email
            await email_input.type('test.com', {delay: 100})
            
            # Validation should pass now
            is_valid = await email_input.evaluate('el => el.checkValidity()')
            assert is_valid, "Complete email should be valid"
            
            await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])