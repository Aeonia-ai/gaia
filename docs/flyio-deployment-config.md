# Fly.io Deployment Configuration

## Organization Setup
The Gaia Platform is deployed under the **aeonia-dev** organization on Fly.io:
- **Organization Name**: aeonia-dev
- **Organization Type**: SHARED
- **Primary Region**: LAX (Los Angeles)

## Database Management
Fly.io has migrated to Managed Postgres (mpg). Key commands:

```bash
# List managed Postgres databases
fly mpg list

# Create new managed Postgres database
fly postgres create \
  --name gaia-db-production \
  --region lax \
  --vm-size shared-cpu-1x \
  --volume-size 10 \
  --initial-cluster-size 1 \
  --org aeonia-dev

# Connect to database
fly postgres connect -a gaia-db-production

# Get connection string
fly postgres connect -a gaia-db-production --command "echo \$DATABASE_URL"
```

## Existing Infrastructure
- **Staging Database**: Check with `fly mpg list` for existing databases
- **Production Database**: May already exist - verify before creating new one
- **Database Naming**: gaia-db-{environment} (e.g., gaia-db-staging, gaia-db-production)