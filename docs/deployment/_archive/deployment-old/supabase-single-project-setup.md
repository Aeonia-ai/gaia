# Supabase Single Project Multi-Environment Setup

This guide explains how to use a single Supabase project to support multiple deployment environments due to the free tier limitation of 2 projects per organization.

## Background

Supabase's free tier limits organizations to 2 projects. Since we already have:
1. `aeonia-gaia` (project ID: jbxghtpqbiyttjzdjpti)
2. `gaia-platform-v2` (project ID: lbaohvnusingoztdzlmj)

We cannot create additional projects for dev/staging/production environments. Instead, we configure `gaia-platform-v2` to support all environments.

## Configuration Strategy

### 1. Single Supabase Instance
- **Project**: `gaia-platform-v2`
- **Project ID**: `lbaohvnusingoztdzlmj`
- **URL**: `https://lbaohvnusingoztdzlmj.supabase.co`

### 2. Environment Detection
The application determines its environment from the `ENVIRONMENT` variable:
- `local` - Local development
- `dev` - Cloud development
- `staging` - Staging deployment
- `production` - Production deployment

### 3. Redirect URL Configuration
Configure ALL redirect URLs in the Supabase dashboard to support all environments:

```
# Local Development
http://localhost:8080/auth/confirm
http://localhost:8080/auth/callback
http://localhost:8080/

# Dev Environment
https://gaia-web-dev.fly.dev/auth/confirm
https://gaia-web-dev.fly.dev/auth/callback
https://gaia-web-dev.fly.dev/

# Staging Environment
https://gaia-web-staging.fly.dev/auth/confirm
https://gaia-web-staging.fly.dev/auth/callback
https://gaia-web-staging.fly.dev/

# Production Environment
https://gaia-web-production.fly.dev/auth/confirm
https://gaia-web-production.fly.dev/auth/callback
https://gaia-web-production.fly.dev/
```

## Setup Instructions

### Step 1: Configure Supabase Dashboard

1. Go to: https://supabase.com/dashboard/project/lbaohvnusingoztdzlmj
2. Navigate to: Authentication → Settings
3. Set **Site URL** to: `http://localhost:8080` (primary development URL)
4. Add ALL redirect URLs listed above

### Step 2: Local Environment Setup

Your `.env` file should contain:
```bash
# Environment
ENVIRONMENT=local

# Supabase Configuration (same for all environments)
SUPABASE_URL=https://lbaohvnusingoztdzlmj.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxiYW9odm51c2luZ296dGR6bG1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIwNzc3MTksImV4cCI6MjA2NzY1MzcxOX0.HPv55m2XpO4RRxYQKg3C1Zt_96qh54YI-aleSTSsGuI
SUPABASE_JWT_SECRET=o+Q9utTVdfHlP8IMApRnlT7uOn/QUQ5Z584Hd+iVm7GqK1YK+IdLY3PtgKPp1PuqL7JLI13w8FmYn7d9ccVAqQ==
```

### Step 3: Deploy Environment Setup

For each deployment environment, set the `ENVIRONMENT` variable:

```bash
# Dev environment
fly secrets set -a gaia-web-dev "ENVIRONMENT=dev"

# Staging environment
fly secrets set -a gaia-web-staging "ENVIRONMENT=staging"

# Production environment
fly secrets set -a gaia-web-production "ENVIRONMENT=production"
```

The Supabase credentials remain the same across all environments.

## How It Works

### Authentication Flow
1. User registers/logs in via web interface
2. Supabase sends confirmation email
3. Email contains redirect URL based on the Site URL setting
4. Application handles the redirect based on its configured environment
5. The `get_web_service_base_url()` function returns the correct URL for the environment

### Code Configuration
The `app/shared/config.py` file contains:
```python
def get_web_service_base_url() -> str:
    """Get the base URL for the web service based on environment."""
    if settings.WEB_SERVICE_BASE_URL:
        return settings.WEB_SERVICE_BASE_URL
    elif settings.ENVIRONMENT in ["production", "prod"]:
        return "https://gaia-web-production.fly.dev"
    elif settings.ENVIRONMENT in ["staging", "stage"]:
        return "https://gaia-web-staging.fly.dev"
    elif settings.ENVIRONMENT in ["dev", "development"]:
        return "https://gaia-web-dev.fly.dev"
    else:
        return "http://localhost:8080"
```

## Benefits

1. **Cost Effective**: No additional Supabase projects needed
2. **Simplified Management**: Single Supabase configuration
3. **Environment Isolation**: Code handles environment-specific behavior
4. **Easy Migration**: Can upgrade to multiple projects later if needed

## Limitations

1. **Shared User Database**: All environments share the same user pool
2. **No Data Isolation**: Test data exists alongside production data
3. **Email Configuration**: Site URL affects all environments

## Best Practices

1. **User Email Prefixes**: Consider using email prefixes for non-production:
   - Dev: `dev+username@example.com`
   - Staging: `staging+username@example.com`
   - Production: `username@example.com`

2. **Database Tables**: Use environment-specific prefixes if needed:
   - `dev_custom_table`
   - `staging_custom_table`
   - `prod_custom_table`

3. **Testing**: Always test authentication flow after deployment

## Troubleshooting

### Issue: Confirmation emails go to wrong URL
**Solution**: The Site URL in Supabase affects email templates. Users may need to manually adjust the URL based on their environment.

### Issue: Login works locally but not in deployment
**Solution**: Verify the redirect URLs are configured in Supabase dashboard and the `ENVIRONMENT` variable is set correctly.

### Issue: Need to separate user data
**Solution**: Consider upgrading to Supabase Pro plan for additional projects or implement application-level data separation.

## Future Migration Path

When ready to use separate Supabase projects:
1. Export users from shared project
2. Create environment-specific projects
3. Import users to appropriate projects
4. Update environment variables
5. Remove shared redirect URLs