# SSE (Server-Sent Events) Streaming Gotchas



## The Problem

When implementing SSE endpoints, it's critical to understand the connection lifecycle. A common bug pattern:

```python
# ❌ BROKEN: Save after yielding [DONE]
async def event_generator():
    response_content = ""
    async for chunk in get_stream():
        if chunk == "[DONE]":
            yield "data: [DONE]\n\n"  # Client disconnects here!
            break
        response_content += chunk
        yield f"data: {chunk}\n\n"
    
    # This code never executes!
    await save_response(response_content)
```

## Why This Happens

1. Browser's EventSource immediately closes connection on receiving `[DONE]`
2. The async generator stops executing when the client disconnects
3. Any code after yielding the final message won't run

## The Solution

```python
# ✅ CORRECT: Save before yielding [DONE]
async def event_generator():
    response_content = ""
    async for chunk in get_stream():
        if chunk == "[DONE]":
            # Save while connection is still active
            await save_response(response_content)
            yield "data: [DONE]\n\n"
            break
        response_content += chunk
        yield f"data: {chunk}\n\n"
```

## General Pattern

For any critical operations in SSE streams:

1. **Before Final Yield**: Complete all critical operations before yielding termination signals
2. **Use Try/Finally**: For cleanup that must happen regardless
3. **Log Extensively**: Add logging to verify operations complete

```python
async def event_generator():
    try:
        # streaming logic
        pass
    finally:
        logger.info("SSE generator completed")  # Verify this appears
```

## Common Termination Signals

Watch for these patterns that typically cause client disconnection:
- `[DONE]`
- `event: close`
- `finish_reason: "stop"`
- Custom completion signals

## Testing Tips

1. Check logs for save operations: `docker compose logs service | grep "Saving"`
2. Test persistence: Send message → Refresh page → Verify message exists
3. E2E tests should verify data persistence, not just display

## Related Issues

- EventSource doesn't send cookies in Playwright tests
- Some browsers aggressively close connections
- Connection timeouts may interrupt long operations