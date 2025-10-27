# Supabase Setup

Authentication service configuration for the GAIA platform using Supabase.

## 📋 Overview

GAIA uses Supabase for authentication across all environments. Due to free tier limitations (2 projects per org), we use a **single Supabase project** configured for multiple environments.

**Project Name**: `gaia-platform-v2`
**Organization**: Aeonia

⚠️ **Important**: All environments (dev, staging, production) share the same authentication database. Users registered in dev can log into production with the same credentials.

## 🚀 Initial Setup

### 1. Create Supabase Project

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Create new project:
   - Name: `gaia-platform-v2`
   - Database Password: (save securely)
   - Region: US West (closest to Fly.io lax)
   - Pricing: Free tier (or Pro for production)

### 2. Get API Keys

From Project Settings → API:
```bash
# Public API key (safe for client-side)
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Service role key (server-side only, keep secret!)
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Project URL
SUPABASE_URL=https://your-project-ref.supabase.co

# JWT Secret (for token validation)
SUPABASE_JWT_SECRET=your-super-secret-jwt-token-secret
```

### 3. Configure Authentication

In Authentication → Providers:
- **Email**: Enabled (primary)
- **Confirm email**: Enabled for production
- **Secure email change**: Enabled
- **Secure password change**: Enabled

## 🌍 Multi-Environment Configuration

### Redirect URLs Configuration

In Authentication → URL Configuration, add ALL environment URLs:

```
# Local Development
http://localhost:8080
http://localhost:8080/auth/callback
http://localhost:8080/auth/confirm
http://localhost:8005
http://localhost:8005/auth/callback
http://localhost:8005/auth/confirm

# Development Environment
https://gaia-web-dev.fly.dev
https://gaia-web-dev.fly.dev/auth/callback
https://gaia-web-dev.fly.dev/auth/confirm

# Staging Environment
https://gaia-web-staging.fly.dev
https://gaia-web-staging.fly.dev/auth/callback
https://gaia-web-staging.fly.dev/auth/confirm

# Production Environment
https://gaia-web-production.fly.dev
https://gaia-web-production.fly.dev/auth/callback
https://gaia-web-production.fly.dev/auth/confirm
```

### Site URL Configuration

Set the primary Site URL based on your main environment:
- Development focus: `https://gaia-web-dev.fly.dev`
- Production focus: `https://gaia-web-production.fly.dev`

## 📧 Email Templates

### Configure Email Settings

In Authentication → Email Templates:

**Confirm Signup** template:
```html
<h2>Confirm your signup</h2>
<p>Follow this link to confirm your account:</p>
<p><a href="{{ .ConfirmationURL }}">Confirm your email</a></p>
```

**Reset Password** template:
```html
<h2>Reset your password</h2>
<p>Follow this link to reset your password:</p>
<p><a href="{{ .ConfirmationURL }}">Reset Password</a></p>
```

### SMTP Configuration (Production)

For production, configure custom SMTP in Project Settings → Auth:
```
Host: smtp.sendgrid.net (or your provider)
Port: 587
Username: apikey
Password: your-sendgrid-api-key
From Email: noreply@your-domain.com
```

## 🗄️ Database Schema

### User Tables

Supabase automatically creates:
- `auth.users` - Core user data
- `auth.identities` - OAuth identities
- `auth.sessions` - Active sessions
- `auth.refresh_tokens` - Token management

### Custom Tables (if needed)

```sql
-- User profiles extension
CREATE TABLE public.profiles (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  username TEXT UNIQUE,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own profile" ON public.profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.profiles
  FOR UPDATE USING (auth.uid() = id);
```

## 🔑 API Key Management

### In GAIA Platform

The platform uses API keys for service-to-service auth:

```sql
-- API Keys table (in GAIA's PostgreSQL, not Supabase)
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key_hash TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_used_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT true
);
```

### Validation Flow

1. Client sends API key to GAIA
2. GAIA validates key exists in local database
3. For user operations, GAIA uses Supabase service key
4. Returns JWT token for subsequent requests

## 🔒 Security Configuration

### Row Level Security (RLS)

Enable RLS on all public tables:
```sql
-- Enable RLS
ALTER TABLE public.your_table ENABLE ROW LEVEL SECURITY;

-- Example policy
CREATE POLICY "Users can only see own data"
  ON public.your_table
  FOR SELECT
  USING (auth.uid() = user_id);
```

### JWT Configuration

In `.env` for GAIA services:
```bash
# Required for all services
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret

# Required for auth service only
SUPABASE_SERVICE_KEY=eyJ...  # Keep this secret!
```

### CORS Settings

In Project Settings → API:
- Add all deployment domains
- Include `http://localhost:*` for development

## 🧪 Testing Authentication

### Local Testing
```bash
# Test signup
curl -X POST http://localhost:8666/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123!"}'

# Test login
curl -X POST http://localhost:8666/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123!"}'
```

### Verify Supabase Connection
```bash
# Check if Supabase is reachable
curl -H "apikey: $SUPABASE_ANON_KEY" \
     -H "Content-Type: application/json" \
     "$SUPABASE_URL/rest/v1/"

# Should return: {"message":"Success"}
```

## 🚨 Troubleshooting

### Common Issues

**"Invalid API key" during registration**
- Cause: Outdated SUPABASE_ANON_KEY
- Fix: Update secret in Fly.io
```bash
fly secrets set SUPABASE_ANON_KEY="new-key" -a gaia-auth-dev
```

**"JWT secret mismatch"**
- Cause: Wrong SUPABASE_JWT_SECRET
- Fix: Get correct secret from Supabase dashboard → Settings → API

**"Redirect URL not allowed"**
- Cause: Missing URL in Supabase config
- Fix: Add URL to Authentication → URL Configuration

**Email not sending**
- Cause: Using free tier (limited emails)
- Fix: Configure SMTP or upgrade to Pro

### Testing Auth Flow
```bash
# 1. Check auth service health
curl https://gaia-auth-dev.fly.dev/health | jq '.supabase'

# 2. Test registration
./scripts/test.sh --dev auth-register test@example.com pass123

# 3. Check Supabase logs
# Go to Supabase Dashboard → Logs → Auth
```

## 📊 Monitoring

### Supabase Dashboard

Monitor in real-time:
- Authentication → Users: See registrations
- Logs → Auth: Authentication attempts
- Database → Tables: View user data
- Reports → API: Request metrics

### Metrics to Watch
- Failed login attempts
- Registration rate
- Token refresh frequency
- API rate limits (free tier: 500 req/min)

## 🔄 Migration from Other Auth

### From Local Auth to Supabase

1. Export existing users
2. Create accounts in Supabase
3. Migrate passwords (if possible) or trigger reset
4. Update GAIA configuration:
```bash
AUTH_BACKEND=supabase  # Changed from 'local'
```

### Data Migration Script
```python
# Example migration script
import asyncio
from supabase import create_client

async def migrate_users():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Get existing users from old system
    old_users = get_old_users()

    for user in old_users:
        # Create in Supabase
        result = supabase.auth.admin.create_user({
            "email": user.email,
            "password": generate_temp_password(),
            "email_confirm": True
        })

        # Trigger password reset
        supabase.auth.reset_password_email(user.email)
```

## 🎯 Best Practices

1. **Never expose SERVICE_KEY** - Server-side only
2. **Use RLS** - Enable on all public tables
3. **Validate JWTs** - Check expiration and signature
4. **Rate limit** - Implement in GAIA gateway
5. **Monitor usage** - Watch free tier limits
6. **Backup regularly** - Export user data weekly
7. **Test auth flow** - After each deployment

## 📈 Scaling Considerations

### Free Tier Limits
- 50,000 monthly active users
- 200 concurrent connections
- 500 requests/minute
- 2GB database
- 1GB file storage

### When to Upgrade
- > 10,000 active users
- Need custom SMTP
- Require daily backups
- Need phone auth
- Want priority support

### Pro Tier Benefits
- No rate limits
- Daily backups
- Custom SMTP
- Priority support
- SLA guarantee

## 🔗 Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Auth Documentation](https://supabase.com/docs/guides/auth)
- [JavaScript Client](https://supabase.com/docs/reference/javascript)
- [Status Page](https://status.supabase.com)

---

*For deployment instructions, see [deployment-guide.md](./deployment-guide.md)*