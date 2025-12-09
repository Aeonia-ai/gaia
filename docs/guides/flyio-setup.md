# Fly.io Setup

Platform-specific configuration for deploying GAIA to Fly.io.

## 🏢 Organization Setup

- **Organization**: aeonia-dev
- **Type**: SHARED
- **Primary Region**: LAX (Los Angeles)
- **Billing**: Credit card on file

## 🚀 Initial Setup

### 1. Install Fly CLI
```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Verify installation
fly version
```

### 2. Authenticate
```bash
fly auth login
# Opens browser for authentication
```

### 3. Select Organization
```bash
fly orgs list
fly orgs switch aeonia-dev
```

## 📦 Application Setup

### Create Apps for Each Service
```bash
# Development environment
for service in gateway auth chat kb asset web; do
  fly apps create gaia-${service}-dev --org aeonia-dev
done

# Production environment
for service in gateway auth chat kb asset web; do
  fly apps create gaia-${service}-production --org aeonia-dev
done
```

### Application Naming Convention
- Pattern: `gaia-{service}-{environment}`
- Services: gateway, auth, chat, kb, asset, web
- Environments: dev, staging, production

## 🗄️ Database Configuration

### Managed Postgres (Current)
Fly.io uses Managed Postgres (mpg) for databases:

```bash
# List existing databases
fly postgres list

# Create new database
fly postgres create \
  --name gaia-db-dev \
  --region lax \
  --vm-size shared-cpu-1x \
  --volume-size 10 \
  --initial-cluster-size 1 \
  --org aeonia-dev

# Get connection string
fly postgres connect -a gaia-db-dev --command "echo \$DATABASE_URL"

# Connect to database
fly postgres connect -a gaia-db-dev

# Attach to an app
fly postgres attach gaia-db-dev --app gaia-gateway-dev
```

### Database Specifications
- **Dev/Staging**: shared-cpu-1x, 10GB volume
- **Production**: shared-cpu-2x, 50GB volume, 2-node cluster
- **Backups**: Daily automated backups
- **Region**: Same as application (lax)

## 💾 Volume Management

### Create Volumes for Persistent Storage
```bash
# KB service needs volume for Git repositories
fly volumes create gaia_kb_data \
  --size 10 \
  --region lax \
  -a gaia-kb-dev

# List volumes
fly volumes list -a gaia-kb-dev

# Expand volume if needed
fly volumes expand {volume-id} --size 20 -a gaia-kb-dev
```

### Volume Mount Configuration
In `fly.toml`:
```toml
[mounts]
  source = "gaia_kb_data"
  destination = "/data"
```

## 🔑 Secrets Management

### Setting Secrets
```bash
# Set single secret
fly secrets set API_KEY="value" -a gaia-gateway-dev

# Set multiple secrets at once
fly secrets set -a gaia-auth-dev \
  SUPABASE_URL="https://project.supabase.co" \
  SUPABASE_ANON_KEY="eyJ..." \
  SUPABASE_JWT_SECRET="secret" \
  SUPABASE_SERVICE_KEY="eyJ..." \
  ANTHROPIC_API_KEY="sk-ant-..." \
  ENVIRONMENT="dev"

# Import from .env file
fly secrets import < .env -a gaia-gateway-dev
```

### Listing and Managing Secrets
```bash
# List secrets (names only, not values)
fly secrets list -a gaia-gateway-dev

# Remove a secret
fly secrets unset API_KEY -a gaia-gateway-dev

# Sync secrets across services
./scripts/sync-secrets.sh --env dev --services all
```

## 🌍 Region Configuration

### Available Regions
```bash
# List all regions
fly regions list

# Recommended regions for GAIA
- lax (Los Angeles) - Primary
- sjc (San Jose) - Secondary
- sea (Seattle) - Backup
```

### Set Application Regions
```bash
# Set primary region
fly regions set lax -a gaia-gateway-dev

# Add backup regions
fly regions backup sjc sea -a gaia-gateway-dev

# List configured regions
fly regions list -a gaia-gateway-dev
```

## 🔧 Fly.toml Configuration

### Basic Structure
```toml
app = "gaia-gateway-dev"
primary_region = "lax"

[build]
  dockerfile = "Dockerfile.gateway"

[env]
  PORT = "8000"
  ENVIRONMENT = "dev"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true

[[services]]
  http_checks = []
  internal_port = 8000
  protocol = "tcp"
  script_checks = []

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

  [[services.http_checks]]
    interval = 10000
    grace_period = "30s"
    method = "GET"
    path = "/health"
    protocol = "http"
    timeout = 2000
```

### Service-Specific Configurations

**Gateway** (`fly.gateway.dev.toml`):
```toml
[env]
  SERVICE_NAME = "gateway"
  AUTH_SERVICE_URL = "https://gaia-auth-dev.fly.dev"
  CHAT_SERVICE_URL = "https://gaia-chat-dev.fly.dev"
```

**Auth** (`fly.auth.dev.toml`):
```toml
[env]
  SERVICE_NAME = "auth"
  AUTH_BACKEND = "supabase"
```

**Chat** (`fly.chat.dev.toml`):
```toml
[env]
  SERVICE_NAME = "chat"
  MODEL_PROVIDER = "anthropic"
```

## 🚀 Deployment Process

### Deploy with Fly CLI
```bash
# Deploy specific service
fly deploy --config fly.gateway.dev.toml --remote-only

# Deploy with specific Dockerfile
fly deploy --dockerfile Dockerfile.gateway --remote-only

# Deploy without cache
fly deploy --no-cache --remote-only
```

### Deploy with Script
```bash
# Recommended: Use deployment script
./scripts/deploy.sh --env dev --services all --remote-only
```

### Deployment Flags
- `--remote-only`: Build on Fly.io (avoids Docker Hub limits)
- `--local-only`: Build locally (faster if Docker Hub authenticated)
- `--no-cache`: Force rebuild
- `--strategy`: Deployment strategy (rolling, immediate, canary)

## 📊 Monitoring & Logs

### View Logs
```bash
# Stream logs
fly logs -a gaia-gateway-dev

# Follow logs
fly logs -a gaia-gateway-dev --tail

# Filter by instance
fly logs -a gaia-gateway-dev --instance {instance-id}
```

### Monitor Status
```bash
# Application status
fly status -a gaia-gateway-dev

# Machine status
fly machine list -a gaia-gateway-dev

# Check metrics
fly dashboard metrics -a gaia-gateway-dev
```

## 🔄 Scaling

### Horizontal Scaling
```bash
# Scale to 2 instances
fly scale count 2 -a gaia-gateway-dev

# Scale by region
fly scale count lax=2 sjc=1 -a gaia-gateway-dev
```

### Vertical Scaling
```bash
# Change VM size
fly scale vm shared-cpu-2x -a gaia-gateway-dev

# Set memory
fly scale memory 512 -a gaia-gateway-dev
```

### Auto-scaling Configuration
In `fly.toml`:
```toml
[http_service]
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 1
  max_machines_running = 3
```

## 🛠️ Troubleshooting

### Common Issues

**DNS Resolution Failures**
- Problem: `.internal` domains don't resolve
- Solution: Use public URLs (`https://gaia-{service}-{env}.fly.dev`)

**Deployment Timeouts**
- Problem: Deploy hangs at "Monitoring deployment"
- Solution: Check secrets, especially Redis URL

**Health Check Failures**
- Problem: Service won't start
- Solution: SSH in and check logs
```bash
fly ssh console -a gaia-gateway-dev
cat /app/logs/error.log
```

**Machine Won't Start**
```bash
# Get machine ID
fly machine list -a gaia-gateway-dev

# Check machine logs
fly machine status {machine-id} -a gaia-gateway-dev

# Restart machine
fly machine restart {machine-id} -a gaia-gateway-dev
```

## 🔒 Security Best Practices

1. **Use secrets for sensitive data** - Never hardcode in fly.toml
2. **Enable force_https** - All traffic over HTTPS
3. **Set up health checks** - Detect issues early
4. **Use private networking** - When .internal DNS works
5. **Regular secret rotation** - Update keys periodically

## 📚 Useful Commands

```bash
# SSH into container
fly ssh console -a gaia-gateway-dev

# Run command in container
fly ssh console -a gaia-gateway-dev -C "ls -la /app"

# Open app in browser
fly open -a gaia-gateway-dev

# Show app configuration
fly config show -a gaia-gateway-dev

# Export configuration
fly config save -a gaia-gateway-dev

# Destroy app (careful!)
fly apps destroy gaia-gateway-dev
```

## 🔗 Resources

- [Fly.io Documentation](https://fly.io/docs)
- [Fly.io Status Page](https://status.fly.io)
- [Pricing Calculator](https://fly.io/pricing)
- [Community Forum](https://community.fly.io)

---

*For general deployment instructions, see [deployment-guide.md](./deployment-guide.md)*