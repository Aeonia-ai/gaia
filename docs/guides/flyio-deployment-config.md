# Fly.io Deployment Configuration



## Organization Setup
The Gaia Platform is deployed under the **aeonia-dev** organization on Fly.io:
- **Organization Name**: aeonia-dev
- **Organization Type**: SHARED
- **Primary Region**: LAX (Los Angeles)

## Database Management

> **Note**: Fly.io has migrated to Managed Postgres (`fly mpg`). The legacy `fly postgres` commands are deprecated but still functional. This guide uses the modern `fly mpg` commands.

### Modern Commands (fly mpg - Recommended)

```bash
# List managed Postgres databases
fly mpg list

# Create new managed Postgres database
fly mpg create \
  --name gaia-db-production \
  --region lax \
  --vm-size shared-cpu-1x \
  --volume-size 10 \
  --initial-cluster-size 1 \
  --org aeonia-dev

# Connect to database
fly mpg connect -a gaia-db-production

# Get connection string
fly mpg connect -a gaia-db-production --command "echo \$DATABASE_URL"
```

### Legacy Commands (Deprecated)

The following commands still work but are deprecated:
```bash
# Legacy format (still works but not recommended)
fly postgres create --name gaia-db-production
fly postgres connect -a gaia-db-production
```

## Existing Infrastructure
- **Staging Database**: Check with `fly mpg list` for existing databases
- **Production Database**: May already exist - verify before creating new one
- **Database Naming**: gaia-db-{environment} (e.g., gaia-db-staging, gaia-db-production)