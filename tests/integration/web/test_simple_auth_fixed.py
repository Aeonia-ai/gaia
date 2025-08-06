"""
Simple browser auth tests using working async_playwright() pattern.
These tests validate core auth functionality without complex dependencies.
Migrated from broken fixture pattern.
"""
import pytest
import os
from playwright.async_api import async_playwright

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")

@pytest.mark.asyncio 
class TestSimpleAuth:
    """Browser auth tests using working async_playwright() pattern"""
    
    async def test_invalid_login_error_message(self):
        """Test that invalid login shows error message"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
            # Submit invalid credentials
            await page.fill('input[name="email"]', 'wrong@test.com')
            await page.fill('input[name="password"]', 'wrongpass')
            await page.click('button[type="submit"]')
            
            # Wait for and verify error message
            await page.wait_for_selector('text="Login failed. Please try again."', timeout=5000)
            error_element = await page.query_selector('text="Login failed. Please try again."')
            assert error_element is not None, "Error message should be displayed"
            
            await browser.close()
    
    async def test_successful_login_navigation(self):
        """Test that valid login navigates to chat"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            # Mock successful authentication
            session_active = False
            
            async def handle_auth(route):
                nonlocal session_active
                session_active = True
                if 'hx-request' in route.request.headers:
                    await route.fulfill(
                        status=200,
                        headers={"HX-Redirect": "/chat"},
                        body=""
                    )
                else:
                    await route.fulfill(
                        status=303,
                        headers={"Location": "/chat"}
                    )
            
            async def handle_chat(route):
                if session_active:
                    await route.fulfill(
                        status=200,
                        content_type="text/html",
                        body="""
                        <html>
                        <head><title>Gaia Chat</title></head>
                        <body>
                            <div id="chat-interface">
                                <div id="messages"></div>
                                <textarea name="message" placeholder="Type your message..."></textarea>
                                <button type="submit">Send</button>
                            </div>
                        </body>
                        </html>
                        """
                    )
                else:
                    await route.fulfill(status=303, headers={"Location": "/login"})
            
            await page.route("**/auth/login", handle_auth)
            await page.route("**/chat", handle_chat)
            await page.route("**/api/conversations", lambda route: route.fulfill(
                json={"conversations": [], "has_more": False}
            ))
            
            # Perform login
            await page.goto(f'{WEB_SERVICE_URL}/login')
            await page.fill('input[name="email"]', 'test@test.local')
            await page.fill('input[name="password"]', 'test123')
            await page.click('button[type="submit"]')
            await page.wait_for_url('**/chat')
            
            # Should be on chat page after login
            assert "/chat" in page.url, f"Should be on chat page, but on {page.url}"
            
            # Should have basic chat elements
            message_input = await page.query_selector('input[name="message"]')
            assert message_input is not None, "Chat input should be present"
            
            await browser.close()
    
    async def test_login_form_elements_present(self):
        """Test that login form has required elements"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            page = await browser.new_page()
            
            await page.goto(f'{WEB_SERVICE_URL}/login')
            
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
            
            await browser.close()