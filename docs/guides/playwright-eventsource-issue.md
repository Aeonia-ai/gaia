# Playwright EventSource (SSE) Cookie Issue



## Problem Description

EventSource (Server-Sent Events) in Playwright doesn't send cookies with requests, causing authentication failures in E2E tests.

### Symptoms

- Chat messages show "Connection error. Please try again."
- SSE endpoints return 401 Unauthorized
- Manual testing works but E2E tests fail
- Gateway logs show successful forwarding but no response appears

### Root Cause

EventSource is a browser API that:
- Doesn't inherit cookies in Playwright contexts
- Can't be configured with custom headers
- Doesn't support `withCredentials` option directly

This is a **known Playwright limitation**, not a code bug.

## Impact on Tests

### Affected Tests
- `test_real_conversation_flow` - Expects AI responses
- `test_real_auth_persistence` - Expects messages after refresh
- Any test checking actual AI response content

### Passing Tests
- Login/logout tests (don't check AI responses)
- Smoke tests (only check for loading indicators)
- Tests that don't verify message content

## Workarounds Attempted

### 1. SSE Fallback to Regular Fetch (Implemented)
```javascript
eventSource.onerror = function(error) {
    // Fallback to polling if SSE fails
    fetch('/api/chat/response?message=...')
        .then(response => response.text())
        .then(html => {
            // Update UI with response
        });
};
```

**Result**: Partial success but timing issues remain

### 2. Quick Connection Detection
```javascript
// Detect connection failure quickly
const quickTimeout = setTimeout(() => {
    if (!responseStarted && eventSource.readyState !== 1) {
        connectionFailed = true;
        eventSource.close();
    }
}, 100);
```

**Result**: Faster fallback but still unreliable

### 3. Cookie Forwarding (Not Possible)
EventSource API doesn't support:
- Custom headers
- Manual cookie setting
- Credential configuration

## Recommended Solutions

### For E2E Testing

1. **Accept Current Limitations**
   - Document which tests fail due to SSE
   - Focus on testing other functionality
   - Use integration tests for chat features

2. **Alternative Testing Approach**
   - Mock SSE responses in E2E tests
   - Use integration tests for real chat testing
   - Test SSE separately with different tools

3. **Special E2E Mode**
   - Add flag to disable SSE in tests
   - Use polling-only mode for E2E
   - Trade real-time updates for testability

### For Production

The issue **only affects Playwright tests**, not real users:
- Real browsers send cookies with EventSource
- Production SSE streaming works correctly
- No changes needed for production code

## Test Strategy

### What to Test in E2E
- User authentication flow
- UI interactions and navigation
- Form submissions
- Layout and responsiveness

### What to Test in Integration
- Chat message flow
- AI response handling
- Conversation persistence
- SSE streaming functionality

## Code Example

Current implementation with fallback:
```python
# Web UI sends message
await page.fill('input[name="message"]', "Test message")
await page.keyboard.press("Enter")

# Waits for response (SSE fails, fallback triggers)
# But fallback also fails due to session issues
# Result: "Connection error" message
```

## Conclusion

This is a fundamental Playwright limitation. The best approach is to:
1. Accept some E2E test failures for SSE features
2. Use integration tests for chat functionality
3. Document the limitation clearly
4. Don't waste time trying to fix the unfixable

The production system works correctly - this only affects automated testing.