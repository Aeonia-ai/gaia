# Critical Secrets & Dependencies Guide

This document outlines all critical secrets and their dependencies for the Gaia Platform, helping with deployment validation and troubleshooting.

## 🔑 Core Authentication Secrets

### Supabase Configuration
**Required for all environments when `AUTH_BACKEND=supabase`**

| Secret | Purpose | Format | Example | Required |
|--------|---------|--------|---------|----------|
| `SUPABASE_URL` | Supabase project endpoint | URL | `https://abc123.supabase.co` | ✅ |
| `SUPABASE_ANON_KEY` | Public API key for client auth | JWT | `eyJhbGciOiJIUzI1NiIsInR5cCI6...` | ✅ |
| `SUPABASE_JWT_SECRET` | JWT signature verification | Base64 | `o+Q9utTVdfHlP8IMApRn...` | ✅ |
| `SUPABASE_SERVICE_KEY` | Service role for admin ops | JWT | `eyJhbGciOiJIUzI1NiIsInR5cCI6...` | 🟡* |

**\*Note:** `SUPABASE_SERVICE_KEY` is required for:
- E2E tests that create/manage users
- Admin operations like user management
- API key validation in Supabase RPC functions

### Legacy Database (PostgreSQL)
**Only required when `AUTH_BACKEND=postgresql`**

| Secret | Purpose | Format | Example | Required |
|--------|---------|--------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection | URL | `postgresql://user:pass@host:5432/db` | 🟡 |

## 🤖 AI Provider Keys

### Anthropic (Claude)
| Secret | Purpose | Required | Notes |
|--------|---------|----------|-------|
| `ANTHROPIC_API_KEY` | Claude API access | ✅ | Primary LLM provider |

### OpenAI (Optional)
| Secret | Purpose | Required | Notes |
|--------|---------|----------|-------|
| `OPENAI_API_KEY` | GPT API access | 🟡 | Secondary provider |

## 🗃️ Knowledge Base Integration

### Git Repository Access
**Required for KB service with Git sync**

| Secret | Purpose | Format | Required |
|--------|---------|--------|----------|
| `KB_GIT_REPO_URL` | Git repository URL | URL | 🟡 |
| `KB_GIT_AUTH_TOKEN` | Git authentication | Token | 🟡 |

Example configuration:
```bash
KB_GIT_REPO_URL=https://github.com/username/knowledge-base.git
KB_GIT_AUTH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

## 🏗️ Infrastructure Secrets

### Messaging & Caching
| Secret | Purpose | Format | Required | Default |
|--------|---------|--------|----------|---------|
| `NATS_URL` | Event messaging | URL | 🟡 | `nats://nats:4222` |
| `REDIS_URL` | Caching layer | URL | 🟡 | `redis://redis:6379` |

### Application Configuration
| Secret | Purpose | Values | Required | Default |
|--------|---------|--------|----------|---------|
| `AUTH_BACKEND` | Authentication method | `supabase`, `postgresql` | ✅ | `postgresql` |
| `ENVIRONMENT` | Deployment environment | `local`, `dev`, `staging`, `prod` | ✅ | `local` |

## 🚨 Secret Validation Patterns

### JWT Format Validation
```bash
# Valid JWT starts with eyJ (base64 encoded JSON header)
if [[ "$SUPABASE_ANON_KEY" =~ ^eyJ ]]; then
    echo "Valid JWT format"
fi
```

### URL Format Validation
```bash
# Valid URLs start with http:// or https://
if [[ "$SUPABASE_URL" =~ ^https?:// ]]; then
    echo "Valid URL format"
fi
```

### UUID Format Validation
```bash
# Valid UUIDs follow 8-4-4-4-12 hexadecimal pattern
if [[ "$USER_ID" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
    echo "Valid UUID format"
fi
```

## 🔍 Troubleshooting Common Issues

### Authentication Failures

**Issue:** `Authentication failed` or `Invalid API key`
```bash
# Check if secrets are properly set
./scripts/validate-deployment-env.sh local

# Verify Supabase connection
curl -H "apikey: $SUPABASE_ANON_KEY" "$SUPABASE_URL/rest/v1/"
```

**Issue:** `No provider found for model`
```bash
# Check if AI provider key is set
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:10}..."
```

### Service Communication Failures

**Issue:** Services can't communicate
```bash
# Check if all required services are running
docker compose ps

# Verify service health
./scripts/test.sh --local health
```

**Issue:** Supabase RPC failures
```bash
# Verify service role key is set
echo "SUPABASE_SERVICE_KEY: ${SUPABASE_SERVICE_KEY:0:10}..."

# Test RPC function directly
curl -X POST "$SUPABASE_URL/rest/v1/rpc/validate_api_key" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"key_hash_input": "test_hash"}'
```

## 🛠️ Environment-Specific Setup

### Local Development
```bash
# Copy example environment
cp .env.example .env

# Set required secrets
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret
ANTHROPIC_API_KEY=sk-ant-...
AUTH_BACKEND=supabase
ENVIRONMENT=local
```

### Fly.io Deployment
```bash
# Set secrets for specific app
fly secrets set -a gaia-auth-dev \
  SUPABASE_URL="https://your-project.supabase.co" \
  SUPABASE_ANON_KEY="eyJ..." \
  SUPABASE_JWT_SECRET="your-jwt-secret" \
  ANTHROPIC_API_KEY="sk-ant-..." \
  AUTH_BACKEND="supabase" \
  ENVIRONMENT="dev"

# Verify secrets are set
fly secrets list -a gaia-auth-dev
```

## 📊 Secret Dependencies Matrix

| Service | Supabase Keys | AI Keys | Git Keys | Infrastructure |
|---------|---------------|---------|----------|----------------|
| Gateway | ✅ All | ✅ ANTHROPIC | ❌ | 🟡 NATS, REDIS |
| Auth    | ✅ All | ❌ | ❌ | 🟡 NATS |
| Chat    | 🟡 JWT_SECRET | ✅ ANTHROPIC | ❌ | 🟡 NATS, REDIS |
| KB      | 🟡 JWT_SECRET | ❌ | 🟡 Git tokens | 🟡 NATS |
| Asset   | 🟡 JWT_SECRET | ❌ | ❌ | 🟡 NATS |
| Web     | ✅ All | ❌ | ❌ | ❌ |

## 🔧 Automated Validation

Use the deployment validation script to check all secrets:

```bash
# Local environment
./scripts/validate-deployment-env.sh local

# Remote environment with fix suggestions
./scripts/validate-deployment-env.sh dev --fix
```

## 🚨 Security Best Practices

### Secret Rotation
1. **Rotate regularly**: AI provider keys, Git tokens
2. **Never commit**: Secrets to version control
3. **Use environment-specific**: Different keys per environment
4. **Monitor usage**: Track API key usage and costs

### Access Control
1. **Principle of least privilege**: Only grant necessary permissions
2. **Service isolation**: Each service only gets required secrets
3. **Audit access**: Regularly review who has access to secrets

### Backup & Recovery
1. **Document recovery procedures**: How to regenerate each secret
2. **Test backup keys**: Ensure secondary keys work
3. **Emergency contacts**: Know who to contact for provider support

## 📚 Related Documentation

- [Authentication Guide](authentication-guide.md) - Complete auth setup
- [Deployment Best Practices](deployment-best-practices.md) - Deployment strategies  
- [Troubleshooting Guide](troubleshooting-api-key-auth.md) - Common issues
- [Supabase Configuration](supabase-configuration.md) - Supabase-specific setup