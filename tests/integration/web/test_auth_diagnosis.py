"""
Diagnosis test to understand auth behavior in web service.
"""
import pytest
from playwright.async_api import async_playwright
import os

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_login_form_behavior():
    """Test to understand actual login form behavior"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = await browser.new_page()
        
        print(f"\n=== Testing login form at {WEB_SERVICE_URL}/login ===")
        
        # Navigate to login page
        await page.goto(f'{WEB_SERVICE_URL}/login')
        
        # Check what form attributes exist
        form = await page.query_selector('form')
        if form:
            action = await form.get_attribute('action')
            method = await form.get_attribute('method')
            hx_post = await form.get_attribute('hx-post')
            hx_target = await form.get_attribute('hx-target')
            hx_swap = await form.get_attribute('hx-swap')
            
            print(f"Form attributes:")
            print(f"  action: {action}")
            print(f"  method: {method}")
            print(f"  hx-post: {hx_post}")
            print(f"  hx-target: {hx_target}")
            print(f"  hx-swap: {hx_swap}")
        
        # Find submit button
        submit_button = await page.query_selector('button[type="submit"]')
        if submit_button:
            button_text = await submit_button.inner_text()
            print(f"Submit button text: {button_text}")
        
        # Set up request monitoring
        requests = []
        
        def capture_request(request):
            if 'auth' in request.url:
                requests.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': request.headers
                })
                print(f"\nRequest intercepted:")
                print(f"  URL: {request.url}")
                print(f"  Method: {request.method}")
                print(f"  Headers: {request.headers}")
        
        page.on('request', capture_request)
        
        # Fill and submit form WITHOUT mocking
        await page.fill('input[name="email"]', 'test@example.com')
        await page.fill('input[name="password"]', 'test123')
        
        print("\nSubmitting form...")
        await page.click('button[type="submit"]')
        
        # Wait a bit to see what happens
        await page.wait_for_timeout(2000)
        
        print(f"\nFinal URL: {page.url}")
        print(f"Total requests captured: {len(requests)}")
        
        # Check for error messages
        error_elements = await page.query_selector_all('.error, [class*="error"], [id*="error"]')
        if error_elements:
            print(f"\nFound {len(error_elements)} error elements")
            for i, elem in enumerate(error_elements):
                text = await elem.inner_text()
                if text.strip():
                    print(f"  Error {i+1}: {text}")
        
        await browser.close()


@pytest.mark.asyncio
async def test_htmx_vs_regular_mock():
    """Test different mock approaches"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # Test 1: Regular redirect mock
        print("\n=== Test 1: Regular 303 redirect mock ===")
        page1 = await browser.new_page()
        
        await page1.route("**/auth/login", lambda route: route.fulfill(
            status=303,
            headers={"Location": "/chat"},
            body=""
        ))
        
        await page1.goto(f'{WEB_SERVICE_URL}/login')
        await page1.fill('input[name="email"]', 'test@example.com')
        await page1.fill('input[name="password"]', 'test123')
        
        # Capture navigation
        nav_happened = False
        try:
            async with page1.expect_navigation(timeout=3000):
                await page1.click('button[type="submit"]')
                nav_happened = True
        except:
            pass
        
        print(f"Navigation happened: {nav_happened}")
        print(f"Current URL: {page1.url}")
        await page1.close()
        
        # Test 2: HTMX redirect mock
        print("\n=== Test 2: HTMX HX-Redirect mock ===")
        page2 = await browser.new_page()
        
        await page2.route("**/auth/login", lambda route: route.fulfill(
            status=200,
            headers={"HX-Redirect": "/chat"},
            body=""
        ))
        
        await page2.goto(f'{WEB_SERVICE_URL}/login')
        await page2.fill('input[name="email"]', 'test@example.com')
        await page2.fill('input[name="password"]', 'test123')
        
        # Monitor console for HTMX activity
        console_messages = []
        page2.on('console', lambda msg: console_messages.append(msg.text))
        
        await page2.click('button[type="submit"]')
        await page2.wait_for_timeout(2000)
        
        print(f"Current URL: {page2.url}")
        print(f"Console messages: {len(console_messages)}")
        for msg in console_messages[:5]:  # First 5 messages
            print(f"  - {msg}")
        
        await page2.close()
        await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])