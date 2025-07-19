# HTMX + FastHTML Debugging Guide

## Overview

This guide documents critical lessons learned while debugging HTMX issues in the Gaia FastHTML web interface. These insights will save hours of debugging time.

## 🚨 Critical Issues and Solutions

### 1. Loading Indicator Placement

**❌ WRONG: Loading indicator inside swap target**
```python
# This will break - indicator gets replaced during swap!
return Div(
    Div(id="loading-indicator", cls="hidden"),  # ❌ Inside main-content
    # ... other content
    id="main-content"
)
```

**✅ CORRECT: Loading indicator outside swap target**
```python
# In layout component - indicator persists across swaps
return Div(
    Div(
        gaia_loading_spinner(),
        id="loading-indicator",
        cls="htmx-indicator fixed inset-0 bg-black/50 z-50",
        style="display: none;"
    ),
    # ... main content that gets swapped
    Div(id="main-content", ...)
)
```

### 2. CSS for HTMX Indicators

**❌ WRONG: Using opacity**
```css
.htmx-indicator { opacity: 0; }
.htmx-request .htmx-indicator { opacity: 1; }
```

**✅ CORRECT: Using display**
```css
.htmx-indicator { display: none !important; }
.htmx-request .htmx-indicator { display: flex !important; }
.htmx-request.htmx-indicator { display: flex !important; }
```

### 3. HTMX Swap Types

**❌ WRONG: Using innerHTML when replacing container**
```python
hx_swap="innerHTML"  # Only replaces inner content
```

**✅ CORRECT: Using outerHTML for full replacement**
```python
hx_swap="outerHTML"  # Replaces entire element including container
```

### 4. Route Response Structure

**❌ WRONG: Missing container ID in response**
```python
# Response doesn't include the target ID
return Div(
    messages_container,
    chat_input
)
```

**✅ CORRECT: Include target ID in response**
```python
return Div(
    messages_container,
    chat_input,
    id="main-content",  # Must match hx-target
    cls="flex-1 flex flex-col h-screen overflow-hidden"
)
```

### 5. Auth Form Replacement Bug (CRITICAL)

**❌ WRONG: Form targets sibling element with innerHTML**
```python
# Form structure that causes form+message mixing bug
Form(
    # ... form fields
    hx_post="/auth/register",
    hx_target="#auth-message",  # Targets sibling div
    hx_swap="innerHTML"         # Adds content, doesn't replace form
),
Div(id="auth-message", cls="mt-4")  # Sibling div for messages
```

**✅ CORRECT: Form targets container with outerHTML**
```python
# Wrap form in container for proper replacement
Div(
    Form(
        # ... form fields
        hx_post="/auth/register",
        hx_target="#auth-form-container",  # Targets the wrapper
        hx_swap="outerHTML"                # Replaces entire container
    ),
    id="auth-form-container"  # Container that gets replaced
)

# Server response must return new container with same ID
def auth_page_replacement(title, content, actions=None):
    return Div(
        H1(title),
        *content_paragraphs,
        *action_buttons,
        id="auth-form-container"  # Same ID for replacement
    )
```

**Why this matters:** The auth form replacement bug caused registration forms to show alongside verification messages instead of being replaced. This was the #1 recurring layout bug.

## 🔍 Debugging Techniques

### 1. Enable Comprehensive HTMX Logging

Add this to your main chat page:

```javascript
// Enable HTMX debug logging
htmx.config.logger = function(elt, event, data) {
    console.debug("[HTMX]", event, elt, data);
};

// Add event listeners for request lifecycle
document.body.addEventListener('htmx:beforeRequest', function(evt) {
    console.log('[HTMX] Before Request:', evt.detail);
});

document.body.addEventListener('htmx:afterRequest', function(evt) {
    console.log('[HTMX] After Request:', evt.detail);
});

document.body.addEventListener('htmx:responseError', function(evt) {
    console.error('[HTMX] Response Error:', evt.detail);
});

// Check if HTMX is loaded
console.log('[HTMX] Loaded:', typeof htmx);
```

### 2. Server-Side Request Logging

```python
@app.get("/chat/{conversation_id}")
async def chat_conversation(request, conversation_id: str):
    logger.info(f"=== ROUTE CALLED ===")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Is HTMX: {request.headers.get('hx-request')}")
    # ... route logic
```

### 3. Test with Minimal Example

Create a simple test endpoint to isolate issues:

```python
@app.get("/test/htmx")
async def test_htmx(request):
    return Div(
        H2("HTMX Test Success!"),
        P(f"Time: {datetime.now()}"),
        P(f"HTMX Request: {request.headers.get('hx-request') == '1'}"),
        id="main-content"
    )
```

## 🎯 Common Issues and Causes

### Loading Spinner Shows but Request Hangs

1. **Check Network Tab**: Is the request actually being sent?
2. **Server Response**: Is the server returning a complete response?
3. **JavaScript Errors**: Check console for errors that might halt execution
4. **Response Format**: Ensure response HTML matches expected structure

### Conversation Switching Fails

1. **Target ID Mismatch**: Response must include the target element ID
2. **Duplicate IDs**: Ensure no duplicate IDs after swap
3. **Event Binding**: HTMX might not bind to dynamically added elements

### Logout/Navigation Issues

1. **HTMX Intercepting Links**: Use onclick handlers for non-HTMX navigation
   ```python
   A("Logout", href="/logout", onclick="window.location.href='/logout'; return false;")
   ```

2. **Form vs Link Behavior**: Forms with hx-post work differently than links with hx-get

## 🏗️ FastHTML Best Practices

### 1. Attribute Naming

FastHTML uses Python naming (underscores) that converts to HTML (hyphens):
- `hx_get` → `hx-get`
- `hx_target` → `hx-target`
- `hx_swap` → `hx-swap`

### 2. Request Detection

FastHTML automatically detects HTMX requests:
```python
if request.headers.get('hx-request') == '1':
    # Return partial HTML
else:
    # Return full page
```

### 3. Error Handling

Return proper error responses for HTMX:
```python
try:
    # ... process request
except Exception as e:
    return Div(
        gaia_error_message(str(e)),
        id="error-area",
        hx_swap_oob="true"  # Out-of-band swap
    ), 400
```

## 📋 Debugging Checklist

When HTMX requests fail:

- [ ] Check browser Network tab - is request sent?
- [ ] Check server logs - is request received?
- [ ] Check JavaScript console - any errors?
- [ ] Verify loading indicator is outside swap target
- [ ] Confirm response includes target element ID
- [ ] Test with curl/Postman - does endpoint work?
- [ ] Verify HTMX is loaded: `typeof htmx`
- [ ] Check for duplicate element IDs
- [ ] Ensure proper CSS for indicators
- [ ] Look for JavaScript that might interfere

## 🔗 References

- [HTMX Documentation](https://htmx.org/)
- [FastHTML Documentation](https://www.fastht.ml/)
- [HTMX Debugging Guide](https://htmx.org/docs/#debugging)

## 💡 Key Takeaways

1. **Loading indicators must be outside swap targets**
2. **Use display properties, not opacity, for HTMX indicators**
3. **Always include target IDs in response HTML**
4. **Use outerHTML swap for replacing containers**
5. **Enable comprehensive logging during development**
6. **Test with minimal examples to isolate issues**