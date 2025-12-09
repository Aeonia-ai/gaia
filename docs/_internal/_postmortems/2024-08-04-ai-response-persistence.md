# Postmortem: AI Response Persistence Failure

**Date**: August 4, 2024  
**Duration**: ~3 hours  
**Severity**: High (user-facing data loss)  
**Status**: Resolved

## Summary

AI responses were not persisting in the database after being displayed to users. When users refreshed the page or logged back in, they could see their messages but not the AI's responses.

## Timeline

- **Week of July 28**: Architectural migration from direct database access to service-based architecture
- **August 3**: Issue reported by user: "When I log in I don't see AI's response in the chats"
- **August 4**: Investigation and fix implemented

## Root Cause

The SSE (Server-Sent Events) endpoint was attempting to save AI responses AFTER yielding the `[DONE]` signal. When the browser's EventSource received `[DONE]`, it immediately closed the connection, preventing the save operation from completing.

```python
# Before (broken):
if chunk.strip() == "[DONE]":
    yield f"data: [DONE]\n\n"  # Browser closes connection here
    break
# Save code here never executes

# After (fixed):
if chunk.strip() == "[DONE]":
    # Save BEFORE sending [DONE]
    await save_ai_response()
    yield f"data: [DONE]\n\n"
    break
```

## Contributing Factors

1. **Architectural Migration**: System moved from `database_conversation_store` (synchronous) to `chat_service_client` (async)
2. **SSE Lifecycle**: Misunderstanding of when EventSource closes connections
3. **Silent Failure**: No errors logged when save didn't execute

## Resolution

Moved save operations to execute BEFORE yielding completion signals:
- Save on receiving `[DONE]` from gateway
- Save on receiving `finish_reason: "stop"` 
- Added comprehensive logging

## Lessons Learned

### Technical
1. In streaming responses, critical operations must complete before signaling stream end
2. EventSource aggressively closes connections on receiving `[DONE]`
3. Code after `yield` in async generators may not execute if client disconnects

### Process
1. Existing tests already documented this as a known issue (TODO comment)
2. Git history is a valuable debugging tool for understanding architectural changes
3. Missing logs are as diagnostic as error logs

### Tooling
1. Always test in Docker where services actually run: `docker compose exec -T service command`
2. Use existing test suite before creating new tests
3. Simple log grep beats complex monitoring for initial diagnosis

## Prevention

1. **Code Review**: Pay special attention to streaming endpoint lifecycles
2. **Testing**: Ensure E2E tests verify data persistence, not just display
3. **Documentation**: Document SSE/streaming patterns in developer guide

## Detection

- E2E test `test_logout_and_login_again` already detected this issue
- User reports of missing AI responses after refresh

## Action Items

- [x] Fix implemented in commit a5ee082
- [x] E2E tests passing
- [ ] Add streaming best practices to developer documentation
- [ ] Consider adding health check for message save rate