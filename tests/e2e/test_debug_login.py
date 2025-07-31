"""
Debug test to understand login page structure.
"""
import pytest
from playwright.async_api import async_playwright
import os

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_debug_login_form():
    """Debug test to understand login form structure"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        # Log all network requests
        page.on("request", lambda req: print(f"[Request] {req.method} {req.url}"))
        page.on("response", lambda res: print(f"[Response] {res.status} {res.url}"))
        
        print(f"Loading login page: {WEB_SERVICE_URL}/login")
        await page.goto(f'{WEB_SERVICE_URL}/login')
        
        # Find the form
        login_form = await page.query_selector('form')
        if login_form:
            # Get form attributes
            method = await login_form.get_attribute('method')
            action = await login_form.get_attribute('action')
            hx_post = await login_form.get_attribute('hx-post')
            hx_target = await login_form.get_attribute('hx-target')
            hx_swap = await login_form.get_attribute('hx-swap')
            
            print(f"\nForm attributes:")
            print(f"  method: {method}")
            print(f"  action: {action}")
            print(f"  hx-post: {hx_post}")
            print(f"  hx-target: {hx_target}")
            print(f"  hx-swap: {hx_swap}")
        
        # Check if HTMX is loaded
        htmx_loaded = await page.evaluate("typeof htmx !== 'undefined'")
        print(f"\nHTMX loaded: {htmx_loaded}")
        
        # Find submit button
        submit_button = await page.query_selector('button[type="submit"]')
        if submit_button:
            button_text = await submit_button.inner_text()
            print(f"\nSubmit button text: '{button_text}'")
        
        # Mock the auth endpoint to see what happens
        response_sent = False
        
        async def handle_auth(route):
            nonlocal response_sent
            response_sent = True
            print(f"\n[Mock] Intercepted {route.request.method} to {route.request.url}")
            
            # Check if it's HTMX request
            headers = route.request.headers
            if 'hx-request' in headers:
                print("[Mock] This is an HTMX request!")
                # For HTMX, we might need to return HTML content
                await route.fulfill(
                    status=200,
                    headers={"HX-Redirect": "/chat"},
                    body=""
                )
            else:
                # Regular form submission
                await route.fulfill(
                    status=303,
                    headers={"Location": "/chat"},
                    body=""
                )
        
        await page.route("**/auth/login", handle_auth)
        
        # Fill and submit form
        print("\nFilling form...")
        await page.fill('input[name="email"]', 'test@test.local')
        await page.fill('input[name="password"]', 'test123')
        
        print("Clicking submit...")
        await page.click('button[type="submit"]')
        
        # Wait a bit to see what happens
        await page.wait_for_timeout(2000)
        
        print(f"\nFinal URL: {page.url}")
        print(f"Auth endpoint was called: {response_sent}")
        
        # Check current page content
        if not page.url.endswith('/chat'):
            # We're still on login page, check for any updates
            error_element = await page.query_selector('[role="alert"], .error')
            if error_element:
                error_text = await error_element.inner_text()
                print(f"Error message: {error_text}")
        
        await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])