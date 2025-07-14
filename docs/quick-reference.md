# Gaia Platform Quick Reference

## 🚀 Development Environments

### Local Docker Development
```bash
# Start full stack
docker compose up

# Test endpoints
curl http://localhost:8666/health
curl -H "X-API-Key: FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE" http://localhost:8666/api/v0.2/providers

# User: dev@gaia.local
# Database auto-initialized with schema
```

### Cloud Dev Environment
```bash
# Test endpoints
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev providers
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev models

# User: admin@gaia.dev
# API Key: FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE
```

## 🔑 Authentication System

### User-Associated API Keys
- **Local**: `dev@gaia.local` → API key auto-created in Docker
- **Cloud**: `admin@gaia.dev` → API key created during database init
- **Storage**: PostgreSQL `api_keys` table with SHA256 hashing
- **Header**: `X-API-Key: your-key-here`

### Database Schema
```sql
users (id, email, name, created_at, updated_at)
api_keys (id, user_id, key_hash, name, permissions, is_active, expires_at)
chat_messages (id, user_id, conversation_id, role, content, model, provider)
assets (id, user_id, type, name, description, url, metadata, status)
```

## 🏗️ Service Architecture

### Ports & URLs
- **Gateway**: `localhost:8666` (local) / `https://gaia-gateway-dev.fly.dev` (cloud)
- **Auth**: Internal service communication only
- **Chat**: Internal service communication only  
- **Asset**: Internal service communication only

### Core API Endpoints
```bash
GET  /health                    # Service health (no auth)
GET  /api/v0.2/providers       # List LLM providers (auth required)
GET  /api/v0.2/models          # List available models (auth required)
POST /api/v0.2/chat            # Chat with LLMs (auth required)
POST /api/v1/chat              # Alternative chat endpoint (auth required)
```

## 🗃️ Database Management

### Initialize New Environment
```bash
# Portable script for any environment
./scripts/init-database-portable.sh --env dev --user admin@gaia.dev --provider fly
./scripts/init-database-portable.sh --env staging --user admin@gaia.com --provider aws
```

### Apply Schema Changes
```bash
# Version-controlled migrations
./scripts/migrate-database.sh --env dev --migration migrations/001_add_feature.sql
./scripts/migrate-database.sh --env prod --migration migrations/001_add_feature.sql --dry-run
```

### Monitor Database
```bash
# Health and performance monitoring
./scripts/monitor-database.sh --env dev --report health
./scripts/monitor-database.sh --env prod --report performance
```

## 🧪 Testing

### Smart Test Scripts (Preferred)
```bash
# Environment-aware testing
./scripts/test.sh --local providers        # Local Docker
./scripts/test.sh --staging health         # Staging environment  
./scripts/test.sh --prod models           # Production environment

# LLM Platform compatibility
./scripts/test_llm_platform_compatibility.sh --api-key your-key
```

### Manual Testing (When Needed)
```bash
# Health check (no auth)
curl https://gaia-gateway-dev.fly.dev/health

# Authenticated endpoints
curl -H "X-API-Key: your-key" https://gaia-gateway-dev.fly.dev/api/v0.2/providers
```

## 🚁 Deployment

### Local Development
```bash
docker compose up              # Start all services
docker compose down -v        # Clean restart
```

### Cloud Deployment
```bash
# Deploy all services to environment
./scripts/deploy.sh --env dev --services all
./scripts/deploy.sh --env staging --services all

# Deploy specific service
./scripts/deploy.sh --env dev --services gateway
```

## 📁 Key Files

### Configuration
- `.env` - Local environment variables
- `fly.*.dev.toml` - Fly.io deployment configs
- `docker-compose.yml` - Local development stack

### Scripts
- `scripts/test.sh` - Smart testing (use this!)
- `scripts/deploy.sh` - Multi-environment deployment
- `scripts/init-database-portable.sh` - Database initialization
- `scripts/migrate-database.sh` - Schema migrations

### Documentation  
- `CLAUDE.md` - AI assistant instructions
- `docs/dev-environment-setup.md` - Complete setup guide
- `docs/lessons-learned.md` - Error prevention knowledge
- `docs/portable-database-architecture.md` - Database design

## ⚡ Common Tasks

### Start Fresh Local Development
```bash
docker compose down -v        # Clean slate
docker compose up            # Start with fresh database
# Database auto-initializes with dev@gaia.local user
```

### Deploy Changes to Dev
```bash
# If shared code changed, deploy all services
./scripts/deploy.sh --env dev --services all

# Test the deployment
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev providers
```

### Add New Environment
```bash
# 1. Create database
fly postgres create --name gaia-db-staging --region lax

# 2. Initialize with admin user
./scripts/init-database-portable.sh --env staging --user admin@gaia.com

# 3. Deploy services
./scripts/deploy.sh --env staging --services all

# 4. Test
./scripts/test.sh --url https://gaia-gateway-staging.fly.dev health
```

## 🏆 Success Criteria

A working environment should have:
- ✅ Gateway health returns 200
- ✅ Providers API returns Claude + OpenAI data
- ✅ Models API returns available models
- ✅ Authentication works with user-associated API keys
- ✅ All services show healthy database connections

## 🆘 Troubleshooting

### Authentication Fails
1. Check API key is user-associated in database
2. Verify all services deployed with same shared code
3. Confirm database contains users and api_keys tables

### Service 503 Errors
1. Check logs: `fly logs -a service-name`
2. Look for import errors in shared code
3. Redeploy all services if shared code changed

### Database Connection Issues
1. Restart database: `fly machine restart machine-id -a db-name`
2. Check connection strings in service configs
3. Verify postgres:// vs postgresql:// URL format