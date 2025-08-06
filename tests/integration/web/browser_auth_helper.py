"""
Simplified auth helper for browser tests based on our discoveries.
"""
import json
from typing import Optional, Dict, Any


class BrowserAuthHelper:
    """Helper to set up authentication for browser tests"""
    
    @staticmethod
    async def setup_authenticated_context(context, user_id: str = "test-user-id", 
                                        email: str = "test@test.local"):
        """Set up an authenticated browser context with session cookie"""
        # The session cookie needs to match what Starlette expects
        # For testing, we can use a simple session token
        await context.add_cookies([{
            "name": "session",
            "value": "test-session-token",
            "domain": "localhost",
            "path": "/",
            "httpOnly": True
        }])
    
    @staticmethod
    async def mock_auth_endpoints(page, user_id: str = "test-user-id",
                                email: str = "test@test.local"):
        """Mock authentication-related endpoints"""
        
        # Mock session API
        async def session_handler(route):
            await route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body=json.dumps({
                    "authenticated": True,
                    "jwt_token": "test-jwt-token",
                    "user": {
                        "id": user_id,
                        "email": email,
                        "full_name": "Test User"
                    }
                })
            )
        
        # Mock auth validation
        async def validate_handler(route):
            await route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body=json.dumps({
                    "user_id": user_id,
                    "email": email,
                    "is_authenticated": True,
                    "full_name": "Test User"
                })
            )
        
        # Mock conversations API (empty by default)
        async def conversations_handler(route):
            await route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body=json.dumps({
                    "conversations": [],
                    "has_more": False
                })
            )
        
        # Mock user info endpoint
        async def user_info_handler(route):
            await route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body=json.dumps({
                    "id": user_id,
                    "email": email,
                    "full_name": "Test User"
                })
            )
        
        # Set up routes
        await page.route("**/api/session", session_handler)
        await page.route("**/auth/validate", validate_handler)
        await page.route("**/api/v1/auth/validate", validate_handler)
        await page.route("**/api/conversations", conversations_handler)
        await page.route("**/api/user/me", user_info_handler)
        await page.route("**/api/v1/user/me", user_info_handler)
    
    @staticmethod
    async def mock_chat_endpoints(page, conversations: Optional[list] = None):
        """Mock chat-related endpoints"""
        
        # Mock chat completion
        async def chat_handler(route):
            request = route.request
            if request.method == "POST":
                await route.fulfill(
                    status=200,
                    headers={"Content-Type": "application/json"},
                    body=json.dumps({
                        "choices": [{
                            "message": {
                                "content": "This is a test response from the assistant."
                            }
                        }],
                        "conversation_id": "test-conv-123",
                        "message_id": "test-msg-456"
                    })
                )
            else:
                await route.continue_()
        
        # Mock streaming endpoint
        async def streaming_handler(route):
            await route.fulfill(
                status=200,
                headers={"Content-Type": "text/event-stream"},
                body="data: {\"choices\":[{\"delta\":{\"content\":\"Test\"}}]}\n\ndata: [DONE]\n\n"
            )
        
        # Update conversations handler if provided
        if conversations is not None:
            async def custom_conversations_handler(route):
                await route.fulfill(
                    status=200,
                    headers={"Content-Type": "application/json"},
                    body=json.dumps({
                        "conversations": conversations,
                        "has_more": len(conversations) > 10
                    })
                )
            await page.route("**/api/conversations", custom_conversations_handler)
        
        # Set up routes
        await page.route("**/api/v1/chat", chat_handler)
        await page.route("**/api/v0.3/chat", chat_handler)
        await page.route("**/api/v1/chat/streaming", streaming_handler)
    
    @staticmethod
    async def setup_full_auth_mocking(page, context=None, **kwargs):
        """Convenience method to set up all auth mocking at once"""
        if context:
            await BrowserAuthHelper.setup_authenticated_context(context, **kwargs)
        await BrowserAuthHelper.mock_auth_endpoints(page, **kwargs)
        await BrowserAuthHelper.mock_chat_endpoints(page)