#!/usr/bin/env python3
"""
Authentication helpers for web UI scripts.
Handles login, session management, and test user creation.
"""
import os
from pathlib import Path
from playwright.async_api import Page

# Load local .env if it exists
_webui_env = Path(__file__).parent.parent / ".env"
if _webui_env.exists():
    from dotenv import load_dotenv
    load_dotenv(_webui_env)


async def login(
    page: Page,
    email: str,
    password: str,
    base_url: str = "http://localhost:8080"
) -> bool:
    """
    Login to web UI and return success status.

    Args:
        page: Playwright page object
        email: User email
        password: User password
        base_url: Base URL of web service

    Returns:
        True if login successful, False otherwise
    """
    try:
        # Navigate to login page
        await page.goto(f"{base_url}/login")

        # Fill in credentials - try data-testid first, fall back to name attribute
        try:
            await page.fill('[data-testid="email-input"]', email, timeout=1000)
        except:
            await page.fill('input[name="email"]', email)

        try:
            await page.fill('[data-testid="password-input"]', password, timeout=1000)
        except:
            await page.fill('input[name="password"]', password)

        # Click submit - try data-testid first, fall back to type attribute
        try:
            await page.click('[data-testid="submit-button"]', timeout=1000)
        except:
            await page.click('button[type="submit"]')

        # Wait for redirect to chat or dashboard
        await page.wait_for_url(
            f"{base_url}/chat*",
            timeout=5000
        )

        print(f"✅ Login successful: {email}")
        return True

    except Exception as e:
        print(f"❌ Login failed: {e}")
        return False


async def ensure_logged_in(
    page: Page,
    email: str,
    password: str,
    base_url: str = "http://localhost:8080"
) -> bool:
    """
    Ensure user is logged in, attempt login if not.

    Args:
        page: Playwright page object
        email: User email
        password: User password
        base_url: Base URL of web service

    Returns:
        True if logged in (or successfully logged in), False otherwise
    """
    # Check if already logged in
    current_url = page.url
    if "/chat" in current_url or "/dashboard" in current_url:
        print(f"✅ Already logged in: {email}")
        return True

    # Not logged in, attempt login
    return await login(page, email, password, base_url)


async def get_session_cookies(page: Page) -> dict:
    """Get current session cookies"""
    cookies = await page.context.cookies()
    return {
        cookie["name"]: cookie["value"]
        for cookie in cookies
    }


def get_test_credentials():
    """Get test user credentials from environment"""
    return {
        "email": os.getenv("TEST_EMAIL") or os.getenv("GAIA_TEST_EMAIL", "test@example.com"),
        "password": os.getenv("TEST_PASSWORD") or os.getenv("GAIA_TEST_PASSWORD", "testpass123")
    }


async def create_test_user(email: str, password: str) -> bool:
    """
    Create a test user via Supabase API.
    Requires SUPABASE_SERVICE_KEY environment variable.

    Args:
        email: User email
        password: User password

    Returns:
        True if user created successfully, False otherwise
    """
    import httpx

    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        print("⚠️  SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{supabase_url}/auth/v1/admin/users",
                headers={
                    "Authorization": f"Bearer {service_key}",
                    "apikey": service_key
                },
                json={
                    "email": email,
                    "password": password,
                    "email_confirm": True
                }
            )

            if response.status_code in [200, 201]:
                print(f"✅ Test user created: {email}")
                return True
            else:
                print(f"❌ Failed to create user: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        return False
