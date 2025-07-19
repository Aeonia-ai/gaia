# FastHTML FT Async Error Prevention Guide

## 🚨 CRITICAL: The "FT can't be used in 'await' expression" Error

### What is this error?
```
TypeError: object FT can't be used in 'await' expression
```

This error occurs when FastHTML tries to await an FT object (FastHTML's HTML component objects) which are NOT awaitable.

## ❌ The Problem

FastHTML route handlers that return FT objects (like `Div`, `Button`, or any UI component) **MUST NOT** be async functions.

### Bad Example (Causes the Error)
```python
@app.post("/auth/register")
async def register(request):  # ❌ ASYNC + FT RETURN = ERROR!
    # ... some logic ...
    return gaia_error_message("Error")  # Returns FT object
```

### Good Example (Correct)
```python
@app.post("/auth/register")
def register(request):  # ✅ SYNC function returning FT
    # ... some logic ...
    return gaia_error_message("Error")  # Returns FT object
```

## 📋 Rules to Prevent This Error

### Rule 1: Sync vs Async Route Handlers

**Use SYNC handlers when:**
- Returning FT objects (UI components)
- Returning HTML content
- No async operations needed

**Use ASYNC handlers when:**
- Returning JSON data
- Making async API calls
- NOT returning FT objects

### Rule 2: Handling Async Operations in Sync Handlers

If you need async operations in a sync handler:

```python
@app.post("/some-route")
def handler(request):
    import asyncio
    
    async def _async_work():
        # Do async stuff here
        result = await some_async_function()
        return result
    
    # Run async function in sync context
    result = asyncio.run(_async_work())
    
    # Return FT object
    return Div(f"Result: {result}")
```

### Rule 3: Check Return Types

Before making a handler async, check what it returns:

```python
# Check these functions - they return FT objects:
- gaia_layout()
- gaia_error_message()
- gaia_success_message()
- gaia_auth_form()
- Div(), Button(), Form(), etc.
- Any FastHTML component

# These can be in async handlers:
- JSONResponse()
- RedirectResponse()
- HTMLResponse() with string content
- Plain dictionaries (auto-converted to JSON)
```

## 🛡️ Prevention Checklist

1. **Lint Check**: Search for `async def` in route handlers
   ```bash
   grep -n "async def" app/services/web/routes/*.py
   ```

2. **Verify Return Types**: For each async handler, verify it doesn't return FT
   ```bash
   # Look for potential FT returns in async functions
   grep -A10 "async def" app/services/web/routes/*.py | grep -E "(gaia_|Div|Button|Form)"
   ```

3. **Test Pattern**: Add this test to catch the issue
   ```python
   def test_no_async_ft_handlers():
       """Ensure no async handlers return FT objects"""
       # Parse route files and check async handlers
       pass
   ```

## 🔧 Quick Fix Guide

If you encounter this error:

1. **Find the problematic handler** - Look for the route in the stack trace
2. **Check if it's async** - Look for `async def`
3. **Check what it returns** - Does it return FT objects?
4. **Remove async** - Change `async def` to `def`
5. **Handle async operations** - Use `asyncio.run()` pattern if needed

## 📚 Examples from Our Codebase

### Correct: Auth Login (Mixed Return Types)
```python
@app.post("/auth/login")
async def login(request):  # Can be async - returns different types
    # ...
    if is_htmx:
        # Returns HTMLResponse (string content) - OK for async
        response = HTMLResponse(content=str(gaia_success_message("...")))
        return response
    else:
        # Returns RedirectResponse - OK for async
        return RedirectResponse(url="/chat", status_code=303)
```

### Correct: Register (FT Returns)
```python
@app.post("/auth/register")
def register(request):  # MUST be sync - returns FT objects
    import asyncio
    
    async def _handle_register():
        # Async operations here
        result = await gateway_client.register(...)
        # Return FT object
        return gaia_error_message("...")
    
    return asyncio.run(_handle_register())
```

### Correct: API Endpoints (JSON Returns)
```python
@app.get("/api/health")
async def health(request):  # Can be async - returns dict/JSON
    return {"status": "healthy"}
```

## 🚀 Golden Rule

**If it returns HTML components (FT objects), it CANNOT be async!**

Remember: FastHTML automatically converts FT objects to HTML strings, but this conversion is synchronous. Making the handler async breaks this conversion process.