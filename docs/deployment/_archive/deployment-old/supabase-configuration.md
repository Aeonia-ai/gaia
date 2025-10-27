# Supabase Environment Configuration

This document explains how to configure Supabase Site URL and redirect URLs for different deployment environments.

## Overview

Due to Supabase's free tier limitation of 2 projects per organization, we use a single Supabase project (`gaia-platform-v2`) configured to support all environments. The redirect URLs must be configured to accept requests from all deployment environments:

- **Local Development**: `http://localhost:8080`
- **Dev (Cloud)**: `https://gaia-web-dev.fly.dev`
- **Staging**: `https://gaia-web-staging.fly.dev` 
- **Production**: `https://gaia-web-production.fly.dev`

## Important: Shared Authentication Limitation

**⚠️ All environments share the same Supabase authentication database.** This means:
- A user registered in dev can log into production with the same credentials
- Test accounts have access to all environments
- There is no built-in environment isolation for authentication

## Configuration per Environment

The Gaia Platform follows a 4-environment deployment pipeline: **local → dev → staging → production**

Each environment has its own PostgreSQL database for application data, but all share the same Supabase authentication.

### Local Development

For local development, configure Supabase with:

**Site URL**: `http://localhost:8080`

**Redirect URLs**:
```
http://localhost:8080/auth/confirm
http://localhost:8080/auth/callback
http://localhost:8080/
```

### Development (Cloud)

For cloud development environment, configure Supabase with:

**Site URL**: `https://gaia-web-dev.fly.dev`

**Redirect URLs**:
```
https://gaia-web-dev.fly.dev/auth/confirm
https://gaia-web-dev.fly.dev/auth/callback
https://gaia-web-dev.fly.dev/
```

**Environment Variables**:
```bash
ENVIRONMENT=dev
WEB_SERVICE_BASE_URL=https://gaia-web-dev.fly.dev
```

### Staging Deployment

For staging environment, configure Supabase with:

**Site URL**: `https://gaia-web-staging.fly.dev`

**Redirect URLs**:
```
https://gaia-web-staging.fly.dev/auth/confirm
https://gaia-web-staging.fly.dev/auth/callback
https://gaia-web-staging.fly.dev/
```

**Environment Variables**:
```bash
ENVIRONMENT=staging
WEB_SERVICE_BASE_URL=https://gaia-web-staging.fly.dev
```

### Production Deployment

For production environment, configure Supabase with:

**Site URL**: `https://gaia-web-production.fly.dev`

**Redirect URLs**:
```
https://gaia-web-production.fly.dev/auth/confirm
https://gaia-web-production.fly.dev/auth/callback
https://gaia-web-production.fly.dev/
```

**Environment Variables**:
```bash
ENVIRONMENT=production
WEB_SERVICE_BASE_URL=https://gaia-web-production.fly.dev
```

## How to Configure Supabase Dashboard

1. **Login to Supabase Dashboard**: https://supabase.com/dashboard
2. **Select Project**: gaia-platform-v2
3. **Go to Settings**: Authentication → Settings
4. **Update Site URL**: Set to the environment-specific base URL
5. **Update Redirect URLs**: Add all three redirect URLs for the environment

## Configuration Helper

The Gaia Platform includes helper functions to get the correct URLs:

```python
from app.shared.config import get_web_service_base_url, get_supabase_redirect_urls

# Get current environment's base URL
base_url = get_web_service_base_url()  # http://localhost:8080 or https://...

# Get all redirect URLs for current environment
redirect_config = get_supabase_redirect_urls()
print(redirect_config["site_url"])       # Site URL
print(redirect_config["redirect_urls"])  # List of redirect URLs
```

## Environment Variable Override

You can override the default URL patterns using the `WEB_SERVICE_BASE_URL` environment variable:

```bash
# Custom domain for production
WEB_SERVICE_BASE_URL=https://gaia.yourdomain.com

# Custom staging URL
WEB_SERVICE_BASE_URL=https://staging.gaia.yourdomain.com
```

## Deployment Script Integration

The deployment scripts should automatically configure Supabase redirect URLs:

```bash
# Example for Fly.io deployment
./scripts/deploy.sh --env staging --configure-supabase

# Or manually set the environment variable
fly secrets set -a gaia-web-staging WEB_SERVICE_BASE_URL=https://gaia-web-staging.fly.dev
```

## Testing Email Confirmation

After configuring Supabase for your environment:

1. **Register a new user** in the web interface
2. **Check email** for verification link
3. **Click confirmation link** - should redirect to your environment's URL
4. **Verify redirect** goes to `/auth/confirm` endpoint
5. **Test login** with confirmed email address

## Troubleshooting

### Wrong Redirect URL
**Problem**: Confirmation link redirects to wrong environment (e.g., localhost:3000)
**Solution**: Update Supabase Site URL in the dashboard

### Confirmation Fails
**Problem**: Confirmation endpoint returns error
**Solution**: Verify `/auth/confirm` endpoint is deployed and accessible

### Local Testing Issues
**Problem**: Email confirmation doesn't work in local development
**Solution**: Ensure Supabase Site URL is set to `http://localhost:8080`

## Security Notes

- Always use HTTPS for staging and production environments
- Verify redirect URLs are exact matches in Supabase dashboard
- Don't add wildcard or overly permissive redirect URLs
- Test email confirmation flow after each deployment