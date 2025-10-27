# Supabase Multi-Environment Setup

This guide explains how to set up separate Supabase projects for dev, staging, and production environments.

## Overview

**Environment Strategy:**
- **Local Development**: Uses dev Supabase project with localhost URLs
- **Dev (Cloud)**: Dedicated Supabase project for cloud development
- **Staging**: Dedicated Supabase project for staging deployment  
- **Production**: Dedicated Supabase project for production

## Supabase Projects to Create

### 1. Development Project
**Project Name**: `gaia-dev`
**Use Cases**: Local development and cloud dev environment

**Configuration:**
```
Site URL: http://localhost:8080
Redirect URLs:
- http://localhost:8080/auth/confirm
- http://localhost:8080/auth/callback
- http://localhost:8080/
- https://gaia-web-dev.fly.dev/auth/confirm
- https://gaia-web-dev.fly.dev/auth/callback
- https://gaia-web-dev.fly.dev/
```

### 2. Staging Project  
**Project Name**: `gaia-staging`
**Use Cases**: Staging deployment and testing

**Configuration:**
```
Site URL: https://gaia-web-staging.fly.dev
Redirect URLs:
- https://gaia-web-staging.fly.dev/auth/confirm
- https://gaia-web-staging.fly.dev/auth/callback
- https://gaia-web-staging.fly.dev/
```

### 3. Production Project
**Project Name**: `gaia-production`
**Use Cases**: Production deployment

**Configuration:**
```
Site URL: https://gaia-web-production.fly.dev
Redirect URLs:
- https://gaia-web-production.fly.dev/auth/confirm
- https://gaia-web-production.fly.dev/auth/callback
- https://gaia-web-production.fly.dev/
```

## Environment Variables Configuration

### Local Development (.env)
```bash
# Use dev Supabase project for local development
ENVIRONMENT=local
SUPABASE_URL=https://[dev-project-id].supabase.co
SUPABASE_ANON_KEY=[dev-anon-key]
SUPABASE_JWT_SECRET=[dev-jwt-secret]
```

### Dev Environment (Cloud)
```bash
# Fly.io secrets for dev
fly secrets set -a gaia-web-dev \
  "ENVIRONMENT=dev" \
  "SUPABASE_URL=https://[dev-project-id].supabase.co" \
  "SUPABASE_ANON_KEY=[dev-anon-key]" \
  "SUPABASE_JWT_SECRET=[dev-jwt-secret]"
```

### Staging Environment
```bash
# Fly.io secrets for staging
fly secrets set -a gaia-web-staging \
  "ENVIRONMENT=staging" \
  "SUPABASE_URL=https://[staging-project-id].supabase.co" \
  "SUPABASE_ANON_KEY=[staging-anon-key]" \
  "SUPABASE_JWT_SECRET=[staging-jwt-secret]"
```

### Production Environment
```bash
# Fly.io secrets for production
fly secrets set -a gaia-web-production \
  "ENVIRONMENT=production" \
  "SUPABASE_URL=https://[production-project-id].supabase.co" \
  "SUPABASE_ANON_KEY=[production-anon-key]" \
  "SUPABASE_JWT_SECRET=[production-jwt-secret]"
```

## Setup Steps

### Step 1: Create Supabase Projects

1. **Go to Supabase Dashboard**: https://supabase.com/dashboard
2. **Create three new projects:**
   - `gaia-dev`
   - `gaia-staging` 
   - `gaia-production`

### Step 2: Configure Each Project

For each project, go to **Authentication → Settings**:

1. **Update Site URL** (as specified above)
2. **Add Redirect URLs** (as specified above)
3. **Copy the credentials:**
   - Project URL
   - Anon/Public Key
   - JWT Secret (from API Settings)

### Step 3: Update Environment Configurations

#### Update Local .env
```bash
# Replace current Supabase config with dev project
SUPABASE_URL=https://[YOUR-DEV-PROJECT-ID].supabase.co
SUPABASE_ANON_KEY=[YOUR-DEV-ANON-KEY]
SUPABASE_JWT_SECRET=[YOUR-DEV-JWT-SECRET]
```

#### Update Cloud Deployments
```bash
# Dev environment
fly secrets set -a gaia-web-dev \
  "SUPABASE_URL=https://[dev-project-id].supabase.co" \
  "SUPABASE_ANON_KEY=[dev-anon-key]" \
  "SUPABASE_JWT_SECRET=[dev-jwt-secret]"

# Staging environment  
fly secrets set -a gaia-web-staging \
  "SUPABASE_URL=https://[staging-project-id].supabase.co" \
  "SUPABASE_ANON_KEY=[staging-anon-key]" \
  "SUPABASE_JWT_SECRET=[staging-jwt-secret]"

# Production environment
fly secrets set -a gaia-web-production \
  "SUPABASE_URL=https://[production-project-id].supabase.co" \
  "SUPABASE_ANON_KEY=[production-anon-key]" \
  "SUPABASE_JWT_SECRET=[production-jwt-secret]"
```

### Step 4: Test Each Environment

#### Test Local Development
```bash
# Restart services to pick up new config
docker compose restart

# Test registration
curl -X POST http://localhost:8080/auth/register \
  -d "email=test@example.com&password=password123"

# Should redirect to localhost:8080 now
```

#### Test Cloud Environments
```bash
# Test dev environment
curl -X POST https://gaia-web-dev.fly.dev/auth/register \
  -d "email=test@example.com&password=password123"

# Test staging environment  
curl -X POST https://gaia-web-staging.fly.dev/auth/register \
  -d "email=test@example.com&password=password123"
```

## Benefits of Multi-Environment Setup

### 1. **Environment Isolation**
- Dev users don't interfere with staging/production
- Can test auth flows without affecting production data
- Safe to experiment with Supabase settings

### 2. **Proper URL Configuration**
- Each environment has correct redirect URLs
- No more localhost:3000 vs localhost:8080 issues
- Email verification works properly in each environment

### 3. **Data Separation**
- Development testing doesn't pollute production user base
- Staging can have realistic test data
- Production data stays clean

### 4. **Configuration Management**
- Clear environment-specific settings
- Easy to manage secrets per environment
- Follows DevOps best practices

## Configuration Template

Save this template for future reference:

```bash
# Environment: [ENV_NAME]
# Supabase Project: gaia-[ENV_NAME]

ENVIRONMENT=[ENV_NAME]
SUPABASE_URL=https://[PROJECT_ID].supabase.co
SUPABASE_ANON_KEY=[ANON_KEY]
SUPABASE_JWT_SECRET=[JWT_SECRET]

# Site URL: [SITE_URL]
# Redirect URLs:
# - [SITE_URL]/auth/confirm  
# - [SITE_URL]/auth/callback
# - [SITE_URL]/
```

## Troubleshooting

### Issue: Wrong redirect URL
**Solution**: Check Site URL and Redirect URLs in Supabase dashboard match your environment

### Issue: JWT validation fails
**Solution**: Ensure JWT_SECRET matches the one from Supabase API settings

### Issue: Email verification goes to wrong URL
**Solution**: Update Site URL in Supabase Authentication settings

## Migration Strategy

1. **Create dev project first** - test with local development
2. **Update local .env** - verify everything works
3. **Create staging project** - deploy and test
4. **Create production project** - final deployment
5. **Update documentation** - ensure team knows new URLs

This setup provides proper environment isolation and eliminates the localhost:3000 vs localhost:8080 confusion!