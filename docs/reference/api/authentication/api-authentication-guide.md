# API Authentication Guide



**STOP! READ THIS FIRST** to avoid breaking authentication again.

## 🚨 Critical Rules - NEVER BREAK THESE

1. **ALL services must use shared configuration**
   ```python
   # ✅ GOOD - Use shared settings
   from app.shared import settings
   api_key = settings.API_KEY
   
   # ❌ BAD - Don't create service-specific API key configs
   api_key = Field(env="WEB_API_KEY")  # DON'T DO THIS!
   ```

2. **API keys are ALWAYS validated through database**
   - Local development: .env API key is pre-configured in database
   - Production: User API keys are created and stored in database
   - Same validation code for both environments

3. **Local database initialization includes API key**
   ```sql
   -- The .env API_KEY is automatically mapped to dev@gaia.local user
   -- SHA256 hash is stored in api_keys table
   -- This ensures local-remote parity
   ```

## How Authentication Works - SAME CODE EVERYWHERE

### The Key Principle: Database-Based Authentication
All API keys are validated through the database - no special cases:

1. **Local Development**
   - `.env` contains: `API_KEY=FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE`
   - Database initialization script automatically:
     - Creates user: `dev@gaia.local`
     - Hashes the API key: SHA256
     - Stores in `api_keys` table
   - Result: API key works exactly like production

2. **Production Deployment**
   - Users create API keys through auth service
   - Keys are hashed and stored in database
   - Same validation code as local

### Authentication Flow (IDENTICAL for local/remote)
```python
# This is the ONLY authentication flow - no special cases
async def validate_user_api_key(api_key: str, db: Session):
    key_hash = hash_api_key(api_key)
    
    # Check Redis cache first
    cached = redis_client.get_json(cache_key)
    if cached:
        return cached
    
    # Validate in database
    result = db.execute(
        "SELECT * FROM api_keys WHERE key_hash = :hash",
        {"hash": key_hash}
    )
    
    # Cache successful validation
    redis_client.set_json(cache_key, result)
    return result
```

### Why This Approach is Better
- **100% code parity** - no environment-specific branches
- **Database required** - ensures consistency
- **Same security model** - API keys always hashed
- **Testing confidence** - local behaves exactly like production
- **No surprises** - what works locally works remotely

## Common Mistakes That Break Authentication

### Mistake 1: Creating Service-Specific API Keys
```python
# ❌ WRONG - Don't do this in service configs
class WebSettings(BaseSettings):
    api_key: str = Field(env="WEB_API_KEY")  # NO!
    
# ✅ CORRECT - Use shared settings
from app.shared import settings
api_key = settings.API_KEY
```

### Mistake 2: Assuming Database is Always Available
```python
# ❌ WRONG - Don't require database for .env API key
if not validate_in_database(api_key):
    raise HTTPException(403)  # Breaks local dev!

# ✅ CORRECT - Check .env key first
if api_key == settings.API_KEY:
    return valid_auth()  # Works without database
```

### Mistake 3: Using Different Environment Variables
```bash
# ❌ WRONG - Don't create new env vars
WEB_API_KEY=xxx
GATEWAY_API_KEY=xxx
AUTH_API_KEY=xxx

# ✅ CORRECT - One API_KEY to rule them all
API_KEY=FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE
```

### Mistake 4: Overcomplicating Configuration
```python
# ❌ WRONG - Complex Pydantic configs
class WebSettings(BaseSettings):
    class Config:
        env_prefix = "WEB_"  # Now looking for WEB_API_KEY!
        
# ✅ CORRECT - Simple shared config
from app.shared import settings  # Just use this!
```

## Testing Authentication

### Quick Test Commands
```bash
# Test gateway directly
curl -H "X-API-Key: $API_KEY" http://localhost:8666/health

# Test chat endpoint
curl -X POST http://localhost:8666/api/v0.2/chat \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'

# Check if services can read API key
docker compose exec web-service python -c \
  "from app.shared import settings; print(settings.API_KEY[:10])"
```

### Debugging Checklist
- [ ] Is `API_KEY` in `.env`?
- [ ] Are services using `app.shared.settings`?
- [ ] Is gateway checking .env key first?
- [ ] Are there any service-specific API key configs?

## Pre-commit Check for API Changes

Add this to your pre-commit routine:
```bash
# Check for service-specific API keys
grep -r "WEB_API_KEY\|GATEWAY_API_KEY\|SERVICE_API_KEY" app/

# Check all services use shared settings
grep -r "from app.shared import settings" app/services/

# Verify .env API key works
./scripts/test.sh --local auth
```

## Architecture Decision Records

### ADR-001: Single API_KEY Environment Variable
**Decision**: Use one `API_KEY` environment variable across all services
**Reason**: Simplicity, consistency, fewer configuration errors
**Consequences**: All services share the same config source

### ADR-002: .env API Key for Local Development
**Decision**: Support .env API key without database validation
**Reason**: Fast local development, no database setup required
**Consequences**: Must check .env key before database

### ADR-003: Shared Configuration Module
**Decision**: All services import from `app.shared.settings`
**Reason**: Single source of truth, prevents divergence
**Consequences**: Services can't have conflicting configs

## Emergency Fixes

### If Authentication Breaks:
1. **Check shared settings first**
   ```bash
   docker compose exec [service] python -c \
     "from app.shared import settings; print(settings.API_KEY)"
   ```

2. **Verify .env is loaded**
   ```bash
   docker compose exec [service] env | grep API_KEY
   ```

3. **Check gateway auth logic**
   - Look at `app/shared/security.py`
   - Ensure .env key check comes FIRST

4. **Remove service-specific configs**
   - Delete any `WEB_API_KEY`, etc.
   - Update service to use shared settings

## Golden Rules

1. **One API_KEY to rule them all** - Don't create service-specific keys
2. **Shared settings are sacred** - All services use `app.shared.settings`
3. **.env works without database** - Essential for local development
4. **Don't overcomplicate** - The simple solution is usually correct
5. **Test before changing** - If auth works, don't "fix" it

## Remember

> "Is there some reason why the .env method isn't good enough?" - The User

The answer is: **No, the .env method IS good enough!** Don't overcomplicate it.