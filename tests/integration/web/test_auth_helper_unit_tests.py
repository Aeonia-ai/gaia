"""
Simplified tests for AuthMockHelper that focus on the mock behavior.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from .auth_mock_helper import AuthMockHelper


@pytest.mark.asyncio
async def test_auth_handler_regular_request():
    """Test auth handler for regular (non-HTMX) requests"""
    handler = AuthMockHelper.create_auth_route_handler(success=True)
    
    # Mock route object
    route = Mock()
    route.request = Mock()
    route.request.all_headers = AsyncMock(return_value={
        "content-type": "application/x-www-form-urlencoded"
    })
    route.fulfill = AsyncMock()
    
    # Call handler
    await handler(route)
    
    # Should return 303 redirect
    route.fulfill.assert_called_once()
    call_args = route.fulfill.call_args[1]
    assert call_args['status'] == 303
    assert call_args['headers']['Location'] == '/chat'


@pytest.mark.asyncio
async def test_auth_handler_htmx_request():
    """Test auth handler for HTMX requests"""
    handler = AuthMockHelper.create_auth_route_handler(success=True)
    
    # Mock route object with HTMX header
    route = Mock()
    route.request = Mock()
    route.request.all_headers = AsyncMock(return_value={
        "content-type": "application/x-www-form-urlencoded",
        "hx-request": "true"
    })
    route.fulfill = AsyncMock()
    
    # Call handler
    await handler(route)
    
    # Should return 200 with HX-Redirect
    route.fulfill.assert_called_once()
    call_args = route.fulfill.call_args[1]
    assert call_args['status'] == 200
    assert call_args['headers']['HX-Redirect'] == '/chat'


@pytest.mark.asyncio
async def test_auth_handler_failure():
    """Test auth handler for failed login"""
    handler = AuthMockHelper.create_auth_route_handler(
        success=False,
        error_message="Invalid credentials"
    )
    
    # Mock route object
    route = Mock()
    route.request = Mock()
    route.request.all_headers = AsyncMock(return_value={})
    route.fulfill = AsyncMock()
    
    # Call handler
    await handler(route)
    
    # Should return error page
    route.fulfill.assert_called_once()
    call_args = route.fulfill.call_args[1]
    assert call_args['status'] == 200
    assert "Invalid credentials" in call_args['body']


@pytest.mark.asyncio
async def test_conversations_handler():
    """Test conversations API handler"""
    test_convs = [{"id": "1", "title": "Test"}]
    handler = AuthMockHelper.create_conversations_api_handler(test_convs)
    
    # Mock route with auth
    route = Mock()
    route.request = Mock()
    route.request.all_headers = AsyncMock(return_value={
        "authorization": "Bearer test-token"
    })
    route.fulfill = AsyncMock()
    
    # Call handler
    await handler(route)
    
    # Should return conversations
    route.fulfill.assert_called_once()
    call_args = route.fulfill.call_args[1]
    assert call_args['status'] == 200
    assert "application/json" in call_args['headers']['Content-Type']
    
    # Check body contains conversations
    import json
    body_data = json.loads(call_args['body'])
    assert body_data['conversations'] == test_convs
    assert body_data['has_more'] == False


@pytest.mark.asyncio
async def test_conversations_handler_unauthorized():
    """Test conversations API handler without auth"""
    handler = AuthMockHelper.create_conversations_api_handler([])
    
    # Mock route without auth
    route = Mock()
    route.request = Mock()
    route.request.all_headers = AsyncMock(return_value={})
    route.fulfill = AsyncMock()
    
    # Call handler
    await handler(route)
    
    # Should return 401
    route.fulfill.assert_called_once()
    call_args = route.fulfill.call_args[1]
    assert call_args['status'] == 401