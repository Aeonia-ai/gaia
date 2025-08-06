"""
Base class for browser tests with proper authentication setup.
"""
import pytest
from playwright.async_api import async_playwright, Page, BrowserContext, expect
import os


class BrowserTestBase:
    """Base class providing authentication setup for browser tests"""
    
    WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://web-service:8000")
    
    async def setup_authenticated_context(self, browser):
        """Create a browser context with authentication cookie"""
        context = await browser.new_context()
        
        # Add session cookie for authentication
        await context.add_cookies([{
            "name": "session",
            "value": "test-session-token",
            "domain": "web-service",
            "path": "/",
            "httpOnly": True
        }])
        
        return context
    
    async def setup_auth_mocks(self, page: Page):
        """Setup standard authentication mocks"""
        # Mock session validation endpoint
        await page.route("**/api/session", lambda route: route.fulfill(
            status=200,
            json={
                "authenticated": True,
                "user": {
                    "id": "test-user-123",
                    "email": "test@test.local"
                },
                "jwt_token": "mock-jwt-token"
            }
        ))
        
        # Mock authentication endpoints with HTMX support
        async def handle_auth(route):
            if 'hx-request' in route.request.headers:
                await route.fulfill(
                    status=200,
                    headers={"HX-Redirect": "/chat"},
                    body=""
                )
            else:
                await route.fulfill(
                    status=303,
                    headers={"Location": "/chat"},
                    body=""
                )
        
        await page.route("**/auth/login", handle_auth)
        await page.route("**/auth/register", handle_auth)
        
        # Mock conversations endpoint (empty by default)
        await page.route("**/api/conversations", lambda route: route.fulfill(
            json={"conversations": [], "has_more": False}
        ))
    
    async def setup_chat_page_mock(self, page: Page):
        """Mock a basic chat page"""
        await page.route("**/chat", lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="""
            <!DOCTYPE html>
            <html>
            <head><title>Chat</title></head>
            <body>
                <div id="chat-container">
                    <div id="sidebar">
                        <button id="new-chat">New Chat</button>
                        <div id="conversations"></div>
                    </div>
                    <div id="messages"></div>
                    <form id="chat-form">
                        <textarea name="message" placeholder="Type a message..."></textarea>
                        <button type="submit">Send</button>
                    </form>
                </div>
                <script>
                    // Check session on load
                    fetch('/api/session')
                        .then(r => r.json())
                        .then(data => {
                            if (!data.authenticated) {
                                window.location.href = '/login';
                            }
                        });
                        
                    // Load conversations
                    fetch('/api/conversations')
                        .then(r => r.json())
                        .then(data => {
                            const convDiv = document.getElementById('conversations');
                            data.conversations.forEach(c => {
                                const div = document.createElement('div');
                                div.textContent = c.title;
                                div.className = 'conversation';
                                div.onclick = () => console.log('Selected:', c.id);
                                convDiv.appendChild(div);
                            });
                        });
                        
                    // Handle form submission
                    document.getElementById('chat-form').onsubmit = function(e) {
                        e.preventDefault();
                        const textarea = this.querySelector('textarea');
                        const messages = document.getElementById('messages');
                        
                        if (!textarea.value.trim()) return;
                        
                        // Add user message
                        const userMsg = document.createElement('div');
                        userMsg.className = 'user-message';
                        userMsg.textContent = textarea.value;
                        messages.appendChild(userMsg);
                        
                        // Make API call
                        fetch('/api/v1/chat', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                messages: [{role: 'user', content: textarea.value}]
                            })
                        })
                        .then(r => r.json())
                        .then(data => {
                            const assistMsg = document.createElement('div');
                            assistMsg.className = 'assistant-message';
                            assistMsg.setAttribute('data-role', 'assistant');
                            assistMsg.textContent = data.choices[0].message.content;
                            messages.appendChild(assistMsg);
                        })
                        .catch(err => {
                            const errorMsg = document.createElement('div');
                            errorMsg.className = 'error';
                            errorMsg.setAttribute('role', 'alert');
                            errorMsg.textContent = 'Error: ' + err.message;
                            messages.appendChild(errorMsg);
                        });
                        
                        textarea.value = '';
                        return false;
                    };
                    
                    // New chat button
                    document.getElementById('new-chat').onclick = function() {
                        document.getElementById('messages').innerHTML = '';
                    };
                </script>
            </body>
            </html>
            """
        ))
    
    async def setup_login_page_mock(self, page: Page):
        """Mock a basic login page"""
        await page.route("**/login", lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="""
            <!DOCTYPE html>
            <html>
            <head><title>Login</title></head>
            <body>
                <h1>Login</h1>
                <form action="/auth/login" method="post">
                    <input type="email" name="email" placeholder="Email" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Sign In</button>
                </form>
            </body>
            </html>
            """
        ))
    
    async def navigate_to_chat(self, page: Page):
        """Navigate to chat page with session validation"""
        await page.goto(f'{self.WEB_SERVICE_URL}/chat')
        await page.wait_for_timeout(500)  # Let session check complete
    
    async def login_user(self, page: Page, email="test@test.local", password="test123"):
        """Perform login flow"""
        await page.goto(f'{self.WEB_SERVICE_URL}/login')
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
        # Wait for redirect or HTMX response
        try:
            await page.wait_for_url('**/chat', timeout=3000)
        except:
            # May have been HTMX redirect
            pass