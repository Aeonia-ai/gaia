# Gateway Authentication Proxying Patterns


**Last Updated**: September 2025  
**Status**: Production Validated  
**Related**: Conversation Context Preservation Fix

## Overview

This document describes the authentication injection patterns used by the GAIA gateway when proxying requests to backend services. These patterns ensure proper authentication flow while maintaining service separation.

## The `_auth` Injection Pattern

### Problem Statement

When the gateway proxies authenticated requests to backend services:
1. **Frontend authentication** happens at the gateway (API keys, JWTs)
2. **Backend services** need authentication info to process requests
3. **Direct header forwarding** doesn't work for modified request bodies
4. **Service separation** requires clean authentication boundaries

### Solution: Body Authentication Injection

The gateway injects authentication information directly into the request body using the `_auth` field:

```python
# Gateway authentication proxying pattern
@app.post("/api/v1/conversations")
async def create_conversation_v1(
    request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Proxy conversation creation to chat service with auth injection"""
    body = await request.json() if request.body else {}
    
    # STEP 1: Inject authentication into request body
    body["_auth"] = auth
    
    # STEP 2: Remove content-length header (CRITICAL!)
    headers = dict(request.headers)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)
    
    # STEP 3: Proxy to backend service
    return await forward_request_to_service(
        service_name="chat",
        path="/conversations",
        method="POST",
        json_data=body,
        headers=headers
    )
```

## Backend Service Dual Auth Support

Backend services must support both direct requests (with auth headers) and proxied requests (with `_auth` in body):

```python
# Chat service dual authentication pattern
@router.post("/conversations")
async def create_conversation(
    http_request: Request,
    auth: dict = Depends(get_current_auth_legacy)
):
    """Handle both direct and gateway-proxied requests"""
    body = await http_request.json()
    
    # Handle both gateway format (_auth in body) and direct format
    if "_auth" in body:
        # Gateway format - use auth from body
        auth = body.get("_auth", {})
        title = body.get("title", "New Conversation")
    else:
        # Direct format - use auth from dependency injection
        title = body.get("title", "New Conversation")
        # auth already populated from Depends(get_current_auth_legacy)
    
    # Process with authentication context
    user_id = auth.get("sub") or auth.get("user_id") or "unknown"
    # ... rest of implementation
```

## Critical HTTP Protocol Compliance

### ⚠️ **Content-Length Header Management**

**Problem**: When modifying request bodies, the original `content-length` header becomes incorrect, causing HTTP protocol errors:

```
h11._util.LocalProtocolError: Too much data for declared Content-Length
```

**Solution**: Always remove content-length headers after modifying request bodies:

```python
# ❌ WRONG - Will cause protocol errors
body["_auth"] = auth
return await forward_request_to_service(
    json_data=body,
    headers=dict(request.headers)  # Includes incorrect content-length
)

# ✅ CORRECT - Remove content-length after modification
body["_auth"] = auth
headers = dict(request.headers)
headers.pop("content-length", None)
headers.pop("Content-Length", None)
return await forward_request_to_service(
    json_data=body,
    headers=headers
)
```

### Why This Matters

1. **FastAPI/httpx** will calculate the correct content-length for the modified body
2. **Original content-length** reflects the body size before adding `_auth`
3. **HTTP/1.1 protocol** requires accurate content-length for proper parsing
4. **Proxy middleware** must handle this correctly to avoid 500 errors

## Implementation Checklist

When implementing gateway authentication proxying:

### ✅ Gateway Side
- [ ] Extract authentication using `Depends(get_current_auth_legacy)`
- [ ] Parse request body with `await request.json()`
- [ ] Inject auth with `body["_auth"] = auth`
- [ ] Remove content-length headers after body modification
- [ ] Use `forward_request_to_service` with modified headers

### ✅ Backend Service Side
- [ ] Add `Request` parameter to endpoint
- [ ] Parse request body with `await request.json()`
- [ ] Check for `_auth` in body for gateway requests
- [ ] Fall back to dependency injection for direct requests
- [ ] Extract user identity consistently (`sub`, `user_id`, etc.)

### ✅ Testing
- [ ] Test direct service calls (with auth headers)
- [ ] Test gateway-proxied calls (with `_auth` injection)
- [ ] Verify content-length handling doesn't cause 500 errors
- [ ] Validate end-to-end authentication flow

## Production Examples

### Gateway Conversation Endpoints

All conversation endpoints use this pattern:

```python
# POST /api/v1/conversations
# GET /api/v1/conversations/{id}
# GET /api/v1/conversations
# DELETE /api/v1/conversations/{id}

# Each follows the same pattern:
body["_auth"] = auth  # For POST requests
headers.pop("content-length", None)  # Always remove
return await forward_request_to_service(...)
```

### Chat Service Integration

The unified chat endpoint (`/chat/unified`) already supported this pattern:

```python
# Handle both gateway format (_auth in body) and direct format
if "_auth" in body:
    auth_principal = body.get("_auth", {})
    message = body.get("message", "")
else:
    # auth_principal from dependency injection
    message = body.get("message", "")
```

## Architecture Benefits

### 🎯 **Service Separation**
- Gateway handles authentication concerns
- Backend services focus on business logic
- Clean service boundaries maintained

### 🔒 **Security**
- Authentication information travels with request
- No shared session state between services
- Consistent user context across service calls

### 🚀 **Performance**
- No additional authentication round-trips
- Minimal overhead (just JSON field injection)
- HTTP protocol compliance prevents errors

### 🧪 **Testability**
- Services can be tested independently
- Gateway proxying can be mocked
- Authentication can be injected for testing

## Common Pitfalls

### ❌ **Forgetting Content-Length Removal**
```python
# This WILL cause 500 errors in production
body["_auth"] = auth
return await forward_request_to_service(
    json_data=body,
    headers=dict(request.headers)  # Still has wrong content-length
)
```

### ❌ **Inconsistent Auth Extraction**
```python
# Backend service only handles one format
user_id = auth.get("user_id")  # Fails for some auth types
# Should be: auth.get("sub") or auth.get("user_id") or "unknown"
```

### ❌ **Missing Request Parameter**
```python
# Can't parse body without Request parameter
@router.post("/endpoint")
async def handler(auth: dict = Depends(get_current_auth_legacy)):
    # body = await request.json()  # request not available!
```

## Future Considerations

### Potential Improvements
1. **Standardized auth extraction** helper function
2. **Middleware automation** for content-length handling
3. **Type safety** for `_auth` structure
4. **Debug headers** for tracing authentication flow

### Alternative Patterns
1. **Custom headers** instead of body injection (less reliable)
2. **Service tokens** for inter-service authentication (more complex)
3. **Shared authentication service** (additional network calls)

## Conclusion

The `_auth` injection pattern provides a robust, testable, and performant solution for gateway authentication proxying. The critical requirement is proper HTTP protocol compliance through content-length header management.

This pattern has been production-validated through the conversation context preservation fix and is now the standard approach for GAIA gateway authentication proxying.