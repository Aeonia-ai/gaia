"""
HTMX-aware authentication mock helper for browser tests.

This helper provides correct mock responses based on whether the request
is a regular form submission or an HTMX request.
"""
from typing import Dict, Optional, Any
import json
import os


class AuthMockHelper:
    """Helper for mocking authentication in browser tests"""
    
    @staticmethod
    def create_auth_route_handler(success: bool = True, 
                                  redirect_to: str = "/chat",
                                  error_message: str = "Invalid credentials"):
        """
        Create a route handler for auth endpoints that handles both regular and HTMX requests.
        
        Args:
            success: Whether the login should succeed
            redirect_to: Where to redirect on success
            error_message: Error message to show on failure
            
        Returns:
            A function that can be used with page.route()
        """
        async def auth_handler(route):
            """Handle auth route with HTMX awareness"""
            request = route.request
            headers = await request.all_headers()
            
            # Check if this is an HTMX request
            is_htmx = headers.get("hx-request") == "true"
            
            if success:
                # Successful login
                if is_htmx:
                    # HTMX expects HX-Redirect header
                    await route.fulfill(
                        status=200,
                        headers={
                            "HX-Redirect": redirect_to,
                            "Content-Type": "text/html"
                        },
                        body=""  # Can be empty or contain success message
                    )
                else:
                    # Regular form expects 303 redirect
                    await route.fulfill(
                        status=303,
                        headers={"Location": redirect_to},
                        body=""
                    )
            else:
                # Failed login
                if is_htmx:
                    # Return error HTML fragment
                    await route.fulfill(
                        status=200,
                        headers={"Content-Type": "text/html"},
                        body=f'<div class="error">⚠️ {error_message}</div>'
                    )
                else:
                    # Return full page with error
                    await route.fulfill(
                        status=200,
                        headers={"Content-Type": "text/html"},
                        body=f'''
                        <html>
                        <body>
                            <div class="error">⚠️ {error_message}</div>
                            <form method="post" action="/auth/login">
                                <input name="email" type="email" />
                                <input name="password" type="password" />
                                <button type="submit">Sign In</button>
                            </form>
                        </body>
                        </html>
                        '''
                    )
        
        return auth_handler
    
    @staticmethod
    def create_test_login_handler(test_email_suffix: str = "@test.local"):
        """
        Create a handler for test mode login (/auth/test-login).
        Only works when TEST_MODE=true.
        
        Args:
            test_email_suffix: Email suffix that's accepted in test mode
            
        Returns:
            A function that can be used with page.route()
        """
        async def test_login_handler(route):
            """Handle test login route"""
            # Check if test mode is enabled
            if os.getenv("TEST_MODE") != "true":
                await route.fulfill(
                    status=400,
                    body="Test mode not enabled"
                )
                return
            
            request = route.request
            headers = await request.all_headers()
            
            # Parse form data
            post_data = await request.post_data()
            form_data = {}
            if post_data:
                for pair in post_data.split("&"):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        form_data[key] = value
            
            email = form_data.get("email", "")
            
            # Check if email has correct suffix
            if email.endswith(test_email_suffix):
                # Success - handle like regular auth
                is_htmx = headers.get("hx-request") == "true"
                
                if is_htmx:
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
            else:
                # Failure
                await route.fulfill(
                    status=200,
                    body=f"Invalid test credentials - use email ending with {test_email_suffix}"
                )
        
        return test_login_handler
    
    @staticmethod
    def create_conversations_api_handler(conversations: Optional[list] = None):
        """
        Create a handler for /api/conversations endpoint.
        
        Args:
            conversations: List of conversations to return (empty list if None)
            
        Returns:
            A function that can be used with page.route()
        """
        async def conversations_handler(route):
            """Handle conversations API endpoint"""
            request = route.request
            headers = await request.all_headers()
            
            # Check for authorization
            auth_header = headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                await route.fulfill(
                    status=401,
                    headers={"Content-Type": "application/json"},
                    body=json.dumps({"detail": "Unauthorized"})
                )
                return
            
            # Return conversations
            response_data = {
                "conversations": conversations or [],
                "has_more": False
            }
            
            await route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body=json.dumps(response_data)
            )
        
        return conversations_handler
    
    @staticmethod
    async def mock_auth_for_chat_page(page, email: str = "test@test.local"):
        """
        Set up all necessary mocks for a user to access the chat page.
        
        Args:
            page: Playwright page object
            email: Email of the test user
        """
        # Mock successful login
        await page.route("**/auth/login", AuthMockHelper.create_auth_route_handler(success=True))
        
        # Mock test login (if using test mode)
        await page.route("**/auth/test-login", AuthMockHelper.create_test_login_handler())
        
        # Mock conversations API (empty for new user)
        await page.route("**/api/conversations", AuthMockHelper.create_conversations_api_handler([]))
        
        # Mock chat completion endpoint
        async def chat_handler(route):
            request = route.request
            headers = await request.all_headers()
            
            # Simple echo response
            await route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body=json.dumps({
                    "choices": [{
                        "message": {
                            "content": "This is a test response"
                        }
                    }],
                    "conversation_id": "test-conv-123"
                })
            )
        
        await page.route("**/api/v1/chat", chat_handler)
        await page.route("**/api/v0.3/chat", chat_handler)
    
    @staticmethod
    def mock_session_cookie(context, jwt_token: str = "test-jwt-token", user_id: str = "test-user-id"):
        """
        Add session cookie to browser context to simulate logged-in state.
        
        Args:
            context: Playwright browser context
            jwt_token: JWT token for the session
            user_id: User ID for the session
        """
        # This would need to match your actual session cookie format
        # Example for a typical session cookie
        context.add_cookies([{
            "name": "session",
            "value": f"jwt={jwt_token}&user={user_id}",
            "domain": "localhost",
            "path": "/",
            "httpOnly": True,
            "secure": False,
            "sameSite": "Lax"
        }])