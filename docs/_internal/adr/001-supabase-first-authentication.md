# ADR-001: Supabase-First Authentication

**Date**: January 2025  
**Status**: Implemented  
**Decision**: Remove PostgreSQL fallback when using Supabase authentication

## Context

The Gaia Platform initially supported dual authentication backends:
- PostgreSQL for legacy API keys
- Supabase for modern JWT authentication

This created confusion about where authentication data lived and complicated the codebase with fallback logic.

## Decision

When `AUTH_BACKEND=supabase` is configured, the system will:
1. Use Supabase exclusively for all authentication
2. Store API keys in Supabase, not PostgreSQL
3. Remove all PostgreSQL fallback logic
4. Maintain API compatibility for existing clients

## Rationale

1. **Clarity**: Single source of truth for authentication data
2. **Simplicity**: Removes complex fallback logic
3. **Performance**: Leverages Supabase's optimized auth infrastructure
4. **Consistency**: Same authentication flow for all environments

## Consequences

### Positive
- Clearer mental model for developers
- Reduced code complexity
- Better performance with Supabase's infrastructure
- Easier debugging with single auth source

### Negative
- Required migration of existing API keys to Supabase
- All environments must have Supabase configured
- Dependency on external service for authentication

### Neutral
- API compatibility maintained - no client changes required
- Redis caching still provides performance benefits

## Implementation

```python
# Before: Complex fallback logic
if supabase_enabled:
    try:
        result = check_supabase()
        if not result:
            result = check_postgresql()  # Fallback
    except:
        result = check_postgresql()  # Fallback

# After: Clear, simple logic
if auth_backend == "supabase":
    result = check_supabase()
    if not result:
        raise HTTPException(403, "Invalid credentials")
```

## Lessons Learned

"There should be no fallback, I am thinking" - This user feedback was key to simplifying the architecture. Sometimes the "safe" approach of having fallbacks actually creates more complexity than it prevents.

## References

- [Supabase Auth Migration Learnings](../supabase-auth-migration-learnings.md)
- [Authentication Guide](../authentication-guide.md)