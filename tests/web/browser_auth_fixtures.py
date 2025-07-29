"""
Browser authentication fixtures for Playwright tests.

Provides various authentication strategies for browser testing.
"""
import pytest
import uuid
import os
from typing import Dict, Any
from playwright.async_api import Page, BrowserContext

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fixtures.test_auth import TestUserFactory, JWTTestAuth


@pytest.fixture
async def mock_authenticated_page(page: Page) -> Page:
    """
    Provide a page with mocked authentication.
    Fastest option for unit tests.
    """
    # Setup auth mock
    await page.route("**/auth/login", lambda route: route.fulfill(
        status=303,
        headers={"Location": "/chat"},
        body=""
    ))
    
    # Mock common API endpoints
    await page.route("**/api/conversations", lambda route: route.fulfill(
        json={"conversations": [], "has_more": False}
    ))
    
    await page.route("**/api/auth/session", lambda route: route.fulfill(
        json={
            "user": {
                "id": "test-123",
                "email": "test@test.local",
                "created_at": "2025-01-01T00:00:00Z"
            }
        }
    ))
    
    # Perform mock login
    await page.goto("/login")
    await page.fill('input[name="email"]', 'test@test.local')
    await page.fill('input[name="password"]', 'test123')
    await page.click('button[type="submit"]')
    await page.wait_for_url("**/chat")
    
    return page


@pytest.fixture
async def real_authenticated_page(page: Page) -> Page:
    """
    Provide a page with real Supabase authentication.
    Requires SUPABASE_SERVICE_KEY environment variable.
    """
    if not os.getenv("SUPABASE_SERVICE_KEY"):
        pytest.skip("Real authentication requires SUPABASE_SERVICE_KEY")
    
    factory = TestUserFactory()
    test_email = f"test-{uuid.uuid4()}@test.local"
    test_password = "Test123!@#"
    
    # Create verified test user
    user = factory.create_verified_test_user(
        email=test_email,
        password=test_password
    )
    
    try:
        # Perform real login
        await page.goto("/login")
        await page.fill('input[name="email"]', test_email)
        await page.fill('input[name="password"]', test_password)
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/chat", timeout=10000)
        
        yield page
    finally:
        # Cleanup test user
        factory.cleanup()


@pytest.fixture
async def session_authenticated_context(browser) -> BrowserContext:
    """
    Provide a browser context with pre-injected session cookie.
    Good for testing protected routes without login flow.
    """
    context = await browser.new_context()
    
    # Create JWT token
    jwt_auth = JWTTestAuth()
    token = jwt_auth.create_token(
        user_id="test-user-123",
        email="test@example.com",
        role="user"
    )
    
    # Inject session cookie
    await context.add_cookies([{
        'name': 'session',
        'value': token,
        'domain': 'web-service',
        'path': '/',
        'httpOnly': True,
        'secure': False  # Set to True in production
    }])
    
    yield context
    await context.close()


@pytest.fixture
async def multi_user_contexts(browser) -> Dict[str, BrowserContext]:
    """
    Provide multiple authenticated browser contexts for testing multi-user scenarios.
    """
    contexts = {}
    jwt_auth = JWTTestAuth()
    
    # Create contexts for different users
    users = [
        {"id": "user-1", "email": "alice@test.local", "role": "user"},
        {"id": "user-2", "email": "bob@test.local", "role": "user"},
        {"id": "admin-1", "email": "admin@test.local", "role": "admin"}
    ]
    
    for user in users:
        context = await browser.new_context()
        
        token = jwt_auth.create_token(
            user_id=user["id"],
            email=user["email"],
            role=user["role"]
        )
        
        await context.add_cookies([{
            'name': 'session',
            'value': token,
            'domain': 'web-service',
            'path': '/',
            'httpOnly': True,
            'secure': False
        }])
        
        contexts[user["email"]] = context
    
    yield contexts
    
    # Cleanup all contexts
    for context in contexts.values():
        await context.close()


@pytest.fixture
def auth_page_objects():
    """
    Provide page object classes for authentication flows.
    """
    class LoginPage:
        def __init__(self, page: Page):
            self.page = page
            self.email_input = 'input[name="email"]'
            self.password_input = 'input[name="password"]'
            self.submit_button = 'button[type="submit"]'
            self.error_message = '[role="alert"]'
        
        async def goto(self):
            await self.page.goto("/login")
        
        async def login(self, email: str, password: str):
            await self.fill_email(email)
            await self.fill_password(password)
            await self.submit()
        
        async def fill_email(self, email: str):
            await self.page.fill(self.email_input, email)
        
        async def fill_password(self, password: str):
            await self.page.fill(self.password_input, password)
        
        async def submit(self):
            await self.page.click(self.submit_button)
        
        async def get_error_message(self) -> str:
            error_elem = await self.page.query_selector(self.error_message)
            if error_elem:
                return await error_elem.inner_text()
            return ""
    
    class RegisterPage:
        def __init__(self, page: Page):
            self.page = page
            self.email_input = 'input[name="email"]'
            self.password_input = 'input[name="password"]'
            self.submit_button = 'button[type="submit"]'
        
        async def goto(self):
            await self.page.goto("/register")
        
        async def register(self, email: str, password: str):
            await self.page.fill(self.email_input, email)
            await self.page.fill(self.password_input, password)
            await self.page.click(self.submit_button)
    
    class ChatPage:
        def __init__(self, page: Page):
            self.page = page
            self.message_input = 'textarea[name="message"]'
            self.send_button = 'button[type="submit"]'
            self.messages_container = '#messages'
            self.sidebar = '#sidebar'
            self.logout_button = 'button:has-text("Logout")'
        
        async def send_message(self, message: str):
            await self.page.fill(self.message_input, message)
            await self.page.keyboard.press("Enter")
        
        async def wait_for_response(self, timeout: int = 30000):
            await self.page.wait_for_selector(
                f'{self.messages_container} .assistant-message:last-child',
                timeout=timeout
            )
        
        async def get_last_message(self) -> str:
            last_msg = await self.page.query_selector(
                f'{self.messages_container} > div:last-child'
            )
            if last_msg:
                return await last_msg.inner_text()
            return ""
        
        async def logout(self):
            await self.page.click(self.logout_button)
    
    return {
        "LoginPage": LoginPage,
        "RegisterPage": RegisterPage,
        "ChatPage": ChatPage
    }


@pytest.fixture
async def authenticated_page_with_mocks(page: Page) -> Page:
    """
    Provide a fully mocked authenticated page with all common API responses.
    """
    # Auth mocks
    await page.route("**/auth/login", lambda route: route.fulfill(
        status=303,
        headers={"Location": "/chat"},
        body=""
    ))
    
    await page.route("**/auth/logout", lambda route: route.fulfill(
        status=303,
        headers={"Location": "/login"},
        body=""
    ))
    
    # API mocks
    await page.route("**/api/conversations", lambda route: route.fulfill(
        json={
            "conversations": [
                {
                    "id": "conv-1",
                    "title": "Test Conversation",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z"
                }
            ],
            "has_more": False
        }
    ))
    
    await page.route("**/api/v1/chat", lambda route: route.fulfill(
        json={
            "id": "msg-123",
            "model": "gpt-4",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a mocked AI response for testing."
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
    ))
    
    await page.route("**/api/auth/session", lambda route: route.fulfill(
        json={
            "user": {
                "id": "test-123",
                "email": "test@test.local",
                "created_at": "2025-01-01T00:00:00Z"
            }
        }
    ))
    
    # Perform login
    await page.goto("/login")
    await page.fill('input[name="email"]', 'test@test.local')
    await page.fill('input[name="password"]', 'test123')
    await page.click('button[type="submit"]')
    await page.wait_for_url("**/chat")
    
    return page