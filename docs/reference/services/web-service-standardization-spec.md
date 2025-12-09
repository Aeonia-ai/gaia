# Web Service Standardization Specification



## Overview

This specification outlines standardization improvements for the GAIA web service to enhance accessibility, testability, and user experience. These recommendations are based on integration test analysis and validated against FastHTML/HTMX best practices.

## Related Documentation

- [Web Testing Strategy Post-Standardization](./web-testing-strategy-post-standardization.md) - How testing will be transformed after implementing these standards
- [HTMX + FastHTML Debugging Guide](./current/web-ui/htmx-fasthtml-debugging-guide.md) - Current debugging patterns and issues
- [Testing Guide](./testing/TESTING_GUIDE.md) - Current testing infrastructure and patterns

## Current State Analysis

### Issues Identified Through Integration Testing

1. **Inconsistent Error Display**: Errors use generic divs with color classes, lacking semantic HTML
2. **Missing Loading States**: No clear indicators during form submission or API calls
3. **Test Brittleness**: Tests rely on CSS classes and text content instead of stable selectors
4. **Mixed Response Patterns**: Inconsistent use of SSE, HTMX, and JavaScript for updates
5. **Form State Management**: Client-side JavaScript handles form clearing instead of server

## Standardization Requirements

### 1. Semantic HTML and Accessibility

#### Error Messages
```python
# Current
def gaia_error_message(message):
    return Div(
        f"⚠️ {message}",
        cls="bg-red-500/10 text-red-200 px-4 py-3 rounded-lg"
    )

# Standardized
def gaia_error_message(message, error_id=None):
    return Div(
        f"⚠️ {message}",
        id=error_id or f"error-{int(time.time())}",
        role="alert",
        aria_live="assertive",
        cls="error-message bg-red-500/10 text-red-200 px-4 py-3 rounded-lg",
        data_testid="error-message"
    )
```

#### Form Controls
```python
# Add ARIA labels and descriptions
def gaia_chat_input():
    return Textarea(
        name="message",
        placeholder="Type your message...",
        aria_label="Chat message input",
        aria_describedby="message-help",
        data_testid="message-input",
        required=True
    )
```

### 2. Loading State Management

#### Button States
```python
def gaia_submit_button(text="Send", loading_text="Sending..."):
    return Button(
        Span(text, cls="htmx-hide-on-request"),
        Span(loading_text, cls="htmx-indicator"),
        type="submit",
        data_testid="send-button",
        cls="btn-primary htmx-disable-on-request"
    )
```

#### Form Loading States
```python
# Add to chat form
Form(
    ...,
    hx_indicator="#form-loading",
    hx_disabled_elt="this",
    aria_busy="false",
    data_loading="false"
)
```

### 3. Consistent Error Handling

#### API Error Responses
```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    is_htmx = request.headers.get("hx-request") == "true"
    
    error_component = gaia_error_message(
        exc.detail,
        error_id=f"error-{exc.status_code}"
    )
    
    if is_htmx:
        return HTMLResponse(
            content=str(error_component),
            status_code=exc.status_code,
            headers={"HX-Retarget": "#error-area"}
        )
    else:
        return gaia_layout(
            main_content=error_component,
            page_class="error-page"
        )
```

#### Toast Notifications
```python
def gaia_toast_oob(message, variant="info"):
    """Server-rendered toast with out-of-band swap"""
    return gaia_toast(
        message,
        variant=variant,
        hx_swap_oob="afterbegin:#toast-container"
    )

# Usage in response
return Div(
    chat_response,
    gaia_toast_oob("Message sent!", "success")
)
```

### 4. Testing Attributes

#### Standard Test IDs
```python
# Define standard test IDs
TEST_IDS = {
    # Authentication
    "login-form": "login-form",
    "email-input": "email-input",
    "password-input": "password-input",
    "submit-button": "submit-button",
    
    # Chat Interface
    "chat-form": "chat-form",
    "message-input": "message-input",
    "send-button": "send-button",
    "messages-container": "messages-container",
    "new-chat-button": "new-chat-button",
    
    # Navigation
    "sidebar": "sidebar",
    "conversation-list": "conversation-list",
    "logout-button": "logout-button"
}
```

### 5. SSE Response Standardization

```python
# Standard SSE event types
class SSEEventType:
    START = "start"
    CONTENT = "content"
    ERROR = "error"
    END = "end"
    HEARTBEAT = "heartbeat"

# Standard SSE response format
async def send_sse_event(event_type, data):
    return f"data: {json.dumps({'type': event_type, 'timestamp': time.time(), **data})}\n\n"

# Usage
yield await send_sse_event(SSEEventType.START, {"message_id": message_id})
yield await send_sse_event(SSEEventType.CONTENT, {"content": chunk})
yield await send_sse_event(SSEEventType.ERROR, {"error": "Service unavailable"})
yield await send_sse_event(SSEEventType.END, {"message_id": message_id})
```

### 6. Form State Management

```python
@app.post("/chat/send")
async def send_message(request):
    # Process message...
    
    # Return fresh form with cleared input
    return Div(
        Div(
            messages_html,
            id="messages",
            data_testid="messages-container"
        ),
        gaia_chat_input(value="", autofocus=True),
        id="chat-area",
        hx_swap="outerHTML"
    )
```

### 7. Progressive Enhancement

```python
def handle_form_submission(request, success_url):
    """Handle both HTMX and standard form submissions"""
    is_htmx = request.headers.get("hx-request") == "true"
    
    if is_htmx:
        response = HTMLResponse(content="")
        response.headers["HX-Redirect"] = success_url
        return response
    else:
        return RedirectResponse(success_url, status_code=303)
```

### 8. Navigation Patterns

```python
def gaia_nav_link(text, href, target="#main-content"):
    """Consistent HTMX navigation link"""
    return A(
        text,
        href=href,
        hx_get=href,
        hx_target=target,
        hx_push_url="true",
        hx_indicator="#page-loading",
        cls="nav-link",
        data_testid=f"nav-{text.lower().replace(' ', '-')}"
    )
```

## Implementation Plan

### Phase 1: Foundation (Week 1)
- [ ] Add semantic HTML and ARIA attributes to all components
- [ ] Implement standard test IDs across all UI elements
- [ ] Create standardized error handling functions

### Phase 2: Loading States (Week 2)
- [ ] Add loading indicators to all forms
- [ ] Implement button state management
- [ ] Add aria-busy attributes during async operations

### Phase 3: Response Patterns (Week 3)
- [ ] Standardize SSE response format
- [ ] Implement server-side form state management
- [ ] Convert client-side toasts to server-rendered

### Phase 4: Testing & Validation (Week 4)
- [ ] Update all integration tests to use data-testid
- [ ] Add accessibility testing suite
- [ ] Validate with screen readers

## Success Metrics

1. **Accessibility**: WCAG 2.1 AA compliance
2. **Test Stability**: 0% flaky tests due to selector issues
3. **User Feedback**: Clear loading and error states
4. **Performance**: No JavaScript required for core functionality
5. **Developer Experience**: Consistent patterns across codebase

## Security Considerations

1. **CSRF Protection**: Validate all form submissions include CSRF tokens
2. **XSS Prevention**: Sanitize all user input in error messages
3. **Rate Limiting**: Clear error messages for rate limit violations
4. **Session Management**: Consistent session handling for HTMX requests

## Testing Strategy

### Unit Tests
```python
def test_error_message_has_aria_attributes():
    error = gaia_error_message("Test error")
    assert 'role="alert"' in str(error)
    assert 'aria-live="assertive"' in str(error)
    assert 'data-testid="error-message"' in str(error)
```

### Integration Tests
```python
async def test_form_submission_shows_loading():
    # Submit form
    await page.fill('[data-testid="message-input"]', "Test")
    await page.click('[data-testid="send-button"]')
    
    # Check loading state
    assert await page.locator('[aria-busy="true"]').is_visible()
    assert await page.locator('.htmx-request').count() > 0
```

### Accessibility Tests
```python
async def test_error_announced_to_screen_reader():
    # Trigger error
    await trigger_api_error()
    
    # Check ARIA live region
    error = page.locator('[role="alert"][aria-live="assertive"]')
    await expect(error).to_be_visible()
    await expect(error).to_contain_text("error")
```

## Migration Guide

### For Existing Components

1. **Add ARIA attributes**: Review each component and add appropriate roles
2. **Add test IDs**: Use consistent naming from TEST_IDS dictionary
3. **Update error handling**: Replace inline errors with standardized components
4. **Convert client-side logic**: Move to server-side HTMX responses

### For New Components

1. Always include `data-testid` attribute
2. Use semantic HTML elements
3. Include appropriate ARIA labels and descriptions
4. Follow progressive enhancement principles
5. Use server-side state management

## References

- [FastHTML Best Practices](https://www.fastht.ml/docs/ref/best_practice.html)
- [HTMX Documentation](https://htmx.org/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)

## Conclusion

This standardization will transform the GAIA web service into a more accessible, testable, and maintainable application. By following FastHTML/HTMX best practices and modern web standards, we ensure a superior user experience while simplifying development and testing workflows.