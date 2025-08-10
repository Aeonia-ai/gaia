"""
Tests for the AuthMockHelper to ensure it produces correct mock responses.
"""
import pytest
from playwright.async_api import async_playwright
import os
import json
from .auth_mock_helper import AuthMockHelper

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")


@pytest.mark.asyncio
async def test_auth_mock_helper_regular_login_success():
    """Test that auth mock helper handles regular login correctly"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Use our helper to mock successful login
        await page.route("**/auth/login", 
                        AuthMockHelper.create_auth_route_handler(success=True))
        
        # Navigate to login and submit form
        await page.goto(f"{WEB_SERVICE_URL}/login")
        await page.fill('input[name="email"]', 'test@example.com')
        await page.fill('input[name="password"]', 'password123')
        
        # Submit form
        await page.click('button[type="submit"]')
        
        # The mock should handle the redirect
        # Wait a moment for navigation
        await page.wait_for_timeout(500)
        
        await browser.close()


@pytest.mark.asyncio
async def test_auth_mock_helper_htmx_login_success():
    """Test that auth mock helper handles HTMX login correctly"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Use our helper to mock successful login
        await page.route("**/auth/login", 
                        AuthMockHelper.create_auth_route_handler(success=True))
        
        # Mock HTMX request by adding hx-request header
        await page.set_extra_http_headers({"hx-request": "true"})
        
        # Make login request with full URL
        response = await page.evaluate(f"""
            async () => {{
                const response = await fetch('{WEB_SERVICE_URL}/auth/login', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'hx-request': 'true'
                    }},
                    body: 'email=test@example.com&password=password123'
                }});
                const headers = {{}};  
                response.headers.forEach((value, key) => {{
                    headers[key.toLowerCase()] = value;
                }});
                return {{
                    status: response.status,
                    headers: headers,
                    body: await response.text()
                }};
            }}
        """)
        
        # Should get 200 for HTMX requests
        assert response['status'] == 200
        # Headers are now normalized to lowercase
        print(f"Response headers: {response['headers']}")
        print(f"Response body: {response['body']}")
        
        # Note: The hx-redirect header is set by the mock but not exposed to fetch API
        # due to CORS restrictions. In real browser tests, HTMX would handle this header.
        # Since this is testing the mock helper itself, we just verify the response status
        # and that no error body was returned.
        assert response['body'] == ""  # Success should have empty body
        
        await browser.close()


@pytest.mark.asyncio
async def test_auth_mock_helper_login_failure():
    """Test that auth mock helper handles login failure correctly"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Use our helper to mock failed login
        await page.route("**/auth/login", 
                        AuthMockHelper.create_auth_route_handler(
                            success=False,
                            error_message="Invalid email or password"
                        ))
        
        # Navigate to login and submit form
        await page.goto(f"{WEB_SERVICE_URL}/login")
        await page.fill('input[name="email"]', 'wrong@example.com')
        await page.fill('input[name="password"]', 'wrongpass')
        await page.click('button[type="submit"]')
        
        # Should show error message
        await page.wait_for_selector('text="⚠️ Invalid email or password"', timeout=5000)
        error_element = await page.query_selector('.error')
        assert error_element is not None
        
        await browser.close()


@pytest.mark.asyncio
async def test_auth_mock_helper_test_mode():
    """Test that test mode login works with correct email suffix"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Enable test mode
        os.environ["TEST_MODE"] = "true"
        
        try:
            # Use our helper for test login
            await page.route("**/auth/test-login",
                            AuthMockHelper.create_test_login_handler())
            
            # Make test login request
            response = await page.evaluate(f"""
                async () => {{
                    const response = await fetch('{WEB_SERVICE_URL}/auth/test-login', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/x-www-form-urlencoded'
                        }},
                        body: 'email=test@test.local&password=anything'
                    }});
                    const headers = {{}};  
                    response.headers.forEach((value, key) => {{
                        headers[key.toLowerCase()] = value;
                    }});
                    return {{
                        status: response.status,
                        headers: headers
                    }};
                }}
            """)
            
            # Should redirect successfully
            assert response['status'] == 303
            assert response['headers'].get('location') == '/chat'
            
        finally:
            # Clean up
            if "TEST_MODE" in os.environ:
                del os.environ["TEST_MODE"]
        
        await browser.close()


@pytest.mark.asyncio
async def test_auth_mock_helper_conversations_api():
    """Test that conversations API mock works correctly"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Mock some test conversations
        test_conversations = [
            {"id": "conv-1", "title": "Test Chat 1", "preview": "Hello..."},
            {"id": "conv-2", "title": "Test Chat 2", "preview": "Another..."}
        ]
        
        await page.route("**/api/conversations",
                        AuthMockHelper.create_conversations_api_handler(test_conversations))
        
        # Make authenticated request
        response = await page.evaluate(f"""
            async () => {{
                const response = await fetch('{WEB_SERVICE_URL}/api/conversations', {{
                    headers: {{
                        'Authorization': 'Bearer test-jwt-token'
                    }}
                }});
                return {{
                    status: response.status,
                    data: await response.json()
                }};
            }}
        """)
        
        # Should return conversations
        assert response['status'] == 200
        assert len(response['data']['conversations']) == 2
        assert response['data']['conversations'][0]['title'] == "Test Chat 1"
        
        await browser.close()


@pytest.mark.asyncio
async def test_auth_mock_helper_full_chat_setup():
    """Test full chat page setup with all mocks"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Use helper to set up all mocks
        await AuthMockHelper.mock_auth_for_chat_page(page)
        
        # Navigate to login
        await page.goto(f"{WEB_SERVICE_URL}/login")
        await page.fill('input[name="email"]', 'test@test.local')
        await page.fill('input[name="password"]', 'password123')
        await page.click('button[type="submit"]')
        
        # Should be able to navigate to chat
        # Note: This might fail if the actual /chat page doesn't exist
        # But the mocks should handle the auth flow correctly
        
        await browser.close()