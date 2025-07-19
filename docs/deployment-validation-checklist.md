# Deployment Validation Checklist

This document provides a comprehensive checklist to prevent and quickly diagnose deployment issues, especially around secret management and service configuration.

## Pre-Deployment Validation

### 1. Secret Management Verification

**Before deploying any service, verify secrets are up to date:**

```bash
# Check local .env file has latest values
grep "SUPABASE_URL\|SUPABASE_ANON_KEY\|SUPABASE_JWT_SECRET" .env

# Compare with what's currently deployed (for auth service)
fly secrets list -a gaia-auth-dev

# Check when secrets were last updated
fly secrets list -a gaia-auth-dev --json | jq '.[] | {name: .name, created_at: .created_at}'
```

**Critical Check**: Ensure SUPABASE_ANON_KEY and SUPABASE_JWT_SECRET were updated recently (within 24h of SUPABASE_URL changes).

### 2. Environment Consistency

```bash
# Verify all services in an environment use same secret values
./scripts/validate-secrets.sh --env dev

# Check for secret drift between environments
./scripts/validate-secrets.sh --compare dev staging
```

## Post-Deployment Validation

### 1. Health Check Verification

```bash
# Check overall system health
./scripts/test.sh --dev health

# Check individual service health with detailed secrets validation
curl https://gaia-auth-dev.fly.dev/health | jq '.secrets'
```

**Expected Response for Healthy Auth Service:**
```json
{
  "secrets": {
    "status": "healthy",
    "secrets_configured": 3,
    "last_checked": "2025-07-19T00:15:00Z"
  }
}
```

**Warning Signs:**
- `"status": "warning"` - Secrets may be misconfigured
- `"status": "unhealthy"` - Missing or invalid secrets
- Missing `secrets` field - Old auth service version

### 2. Authentication Flow Testing

```bash
# Test registration API (should return proper JSON, not HTML)
./scripts/test.sh --dev auth-register test@example.com testpass123

# Should get JSON response like:
# {"detail": "Registration failed: Email address \"test@example.com\" is invalid"}
# NOT: "object FT can't be used in 'await' expression"
```

### 3. Gateway Integration Testing

```bash
# Verify gateway can communicate with auth service
./scripts/test.sh --dev health
# Look for auth service status: "healthy"

# Check for specific error patterns
curl https://gaia-gateway-dev.fly.dev/health | jq '.services.auth'
```

## Common Issues and Solutions

### Issue 1: "Invalid API key" errors during registration

**Symptoms:**
- Registration fails with "Invalid API key"
- Auth service health shows "unhealthy" 
- Web service returns 500 errors for API calls

**Root Cause:** Outdated Supabase credentials on auth service

**Diagnosis:**
```bash
# Check auth service health
curl https://gaia-auth-dev.fly.dev/health | jq '.secrets'

# Look for warnings about invalid JWT format or Supabase connection issues
```

**Solution:**
```bash
# Update Supabase secrets to match .env file
fly secrets set SUPABASE_ANON_KEY="$(grep SUPABASE_ANON_KEY .env | cut -d'=' -f2-)" -a gaia-auth-dev
fly secrets set SUPABASE_JWT_SECRET="$(grep SUPABASE_JWT_SECRET .env | cut -d'=' -f2-)" -a gaia-auth-dev

# Verify fix
curl https://gaia-auth-dev.fly.dev/health | jq '.secrets.status'
# Should return: "healthy"
```

### Issue 2: "object FT can't be used in 'await' expression"

**Symptoms:**
- Web service returns 500 errors for API endpoints
- Browser console shows FastHTML component errors
- API calls return HTML instead of JSON

**Root Cause:** Missing API routes in web service, causing form handlers to process API requests

**Diagnosis:**
```bash
# Check if API routes exist
curl -I https://gaia-web-dev.fly.dev/api/v1/auth/register
# Should return 200 OK, not 404
```

**Solution:**
- Add proper API proxy routes in `app/services/web/routes/api.py`
- Ensure routes return JSONResponse, not FastHTML components
- Deploy web service with updated routes

### Issue 3: Database connection issues

**Symptoms:**
- Services show "degraded" health status
- Database health checks fail
- Authentication works but data operations fail

**Diagnosis:**
```bash
# Check database connectivity
curl https://gaia-gateway-dev.fly.dev/health | jq '.database'

# Check individual service database health
curl https://gaia-auth-dev.fly.dev/health | jq '.database'
```

**Solution:**
```bash
# Check Fly.io database status
fly postgres list
fly postgres connect -a gaia-db-dev --command "SELECT 1"

# Restart services if database is healthy
fly restart -a gaia-auth-dev
```

## Prevention Strategies

### 1. Automated Secret Synchronization

Create a script to automatically validate and sync secrets:

```bash
# scripts/sync-secrets.sh
#!/bin/bash
./scripts/validate-secrets.sh --env dev --fix
./scripts/validate-secrets.sh --env staging --fix
./scripts/validate-secrets.sh --env production --check-only
```

### 2. Enhanced Deploy Script

Always use the enhanced deploy script that validates secrets:

```bash
# Deploy with validation
./scripts/deploy.sh --env dev --services auth

# Script now automatically:
# 1. Sets secrets from .env
# 2. Validates secret configuration after deployment
# 3. Reports any issues clearly
```

### 3. Monitoring and Alerting

Set up monitoring for:
- Auth service secrets health endpoint
- Gateway service health with service status
- API endpoint response format validation

### 4. Documentation in CLAUDE.md

Keep CLAUDE.md updated with:
- Current secret management patterns
- Known issue symptoms and solutions
- Commands for quick diagnosis

## Quick Reference Commands

```bash
# Deploy with full validation
./scripts/deploy.sh --env dev --services auth

# Check secrets health
curl https://gaia-auth-dev.fly.dev/health | jq '.secrets'

# Test API endpoints
./scripts/test.sh --dev auth-register test@example.com testpass123

# Compare secret timestamps
fly secrets list -a gaia-auth-dev --json | jq '.[] | {name: .name, created_at: .created_at}' | sort

# Emergency secret sync
fly secrets set SUPABASE_ANON_KEY="$(grep SUPABASE_ANON_KEY .env | cut -d'=' -f2-)" -a gaia-auth-dev
fly secrets set SUPABASE_JWT_SECRET="$(grep SUPABASE_JWT_SECRET .env | cut -d'=' -f2-)" -a gaia-auth-dev
```

## Success Indicators

✅ **Healthy Deployment:**
- All health checks return "healthy" status
- Auth service secrets status is "healthy"
- API endpoints return proper JSON responses
- Gateway shows all services as "healthy"
- No "Invalid API key" or async/await errors

⚠️ **Warning Signs:**
- Health checks show "degraded" status
- Secrets status shows "warning"
- API endpoints return HTML instead of JSON
- Services return 500 errors intermittently

❌ **Failed Deployment:**
- Health checks return "unhealthy"
- Services return consistent 500 errors
- Auth service cannot connect to Supabase
- Database connections fail