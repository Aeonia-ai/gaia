# Security Improvements

This document tracks planned security improvements for the Gaia platform.

## 1. Remove Dev Login (HIGH PRIORITY)

**Current State**: 
- Dev login exists in `/auth/dev-login` endpoint
- Hardcoded credentials: `dev@gaia.local` / `testtest`
- Only active when `settings.debug = True`

**Security Concerns**:
- Even with debug check, this is a security risk if debug mode is accidentally enabled in production
- Hardcoded credentials in source code
- Bypasses all authentication mechanisms

**Action Items**:
1. Remove `/auth/dev-login` endpoint from `app/services/web/routes/auth.py`
2. Remove hardcoded dev account check in `/auth/login` endpoint (lines 52-60)
3. Remove any UI elements that show "Dev Login" button
4. Update tests to use proper test authentication mechanisms instead

**Alternative for Development**:
- Use test user factory with Supabase service key
- Create development accounts through proper registration flow
- Use environment-specific test accounts

## 2. Additional Security Improvements

### API Key Security
- Implement API key rotation mechanism
- Add API key expiration dates
- Audit logging for API key usage

### Session Security
- Implement session timeout
- Add "remember me" functionality with separate longer-lived tokens
- Implement secure session storage

### Authentication Improvements
- Add rate limiting to login attempts
- Implement account lockout after failed attempts
- Add 2FA support
- Implement password strength requirements

### Audit and Monitoring
- Log all authentication events
- Monitor for suspicious login patterns
- Alert on multiple failed login attempts

## Implementation Timeline

1. **Immediate** (Before Production):
   - Remove dev login
   - Implement rate limiting

2. **Short Term** (1-2 weeks):
   - API key rotation
   - Session timeout
   - Basic audit logging

3. **Medium Term** (1-2 months):
   - 2FA support
   - Advanced monitoring
   - Full audit trail