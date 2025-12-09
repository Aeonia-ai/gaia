# Portable Database Architecture for Gaia Platform

## Overview

This document defines the portable database architecture that enables consistent deployment across dev, staging, and production environments while maintaining flexibility for different cloud providers and scaling requirements.

## Core Principles

### 1. One Database Per Environment
- **Dev**: `gaia-db-dev` → All dev services share this database
- **Staging**: `gaia-db-staging` → All staging services share this database  
- **Production**: `gaia-db-prod` → All production services share this database

### 2. Environment Isolation
- Complete data isolation between environments
- No cross-environment database connections
- Independent backup/restore cycles per environment

### 3. Provider Agnostic Design
- Use standard PostgreSQL features only
- Avoid cloud-specific extensions
- Connection strings as the only provider-specific element

## Database Schema Structure

### Core Tables (Shared Across All Services)

```sql
-- Users table: Central user identity
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API Keys: User-associated authentication
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256 hash
    name VARCHAR(255),
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);
```

### Service-Specific Tables

```sql
-- Chat Service Tables
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    conversation_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    model VARCHAR(100),
    provider VARCHAR(50),
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_messages_user_id ON chat_messages(user_id);
CREATE INDEX idx_chat_messages_conversation_id ON chat_messages(conversation_id);

-- Asset Service Tables
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    url TEXT,
    metadata JSONB DEFAULT '{}',
    generation_params JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_assets_user_id ON assets(user_id);
CREATE INDEX idx_assets_type ON assets(type);
CREATE INDEX idx_assets_status ON assets(status);
```

## Connection Architecture

### 1. Connection String Pattern
```
postgresql://[username]@[host]:[port]/[database]?sslmode=[mode]
```

### 2. Environment-Specific Connection Examples

**Fly.io Pattern** (Current Implementation):
```bash
# Dev
DATABASE_URL="postgresql://postgres@gaia-db-dev.internal:5432/postgres"

# Staging
DATABASE_URL="postgresql://postgres@gaia-db-staging.internal:5432/postgres"

# Production
DATABASE_URL="postgresql://postgres@gaia-db-prod.internal:5432/postgres"
```

**AWS RDS Pattern**:
```bash
# Dev
DATABASE_URL="postgresql://gaia_dev:password@gaia-dev.region.rds.amazonaws.com:5432/llm_platform"

# Staging  
DATABASE_URL="postgresql://gaia_staging:password@gaia-staging.region.rds.amazonaws.com:5432/llm_platform"

# Production
DATABASE_URL="postgresql://gaia_prod:password@gaia-prod.region.rds.amazonaws.com:5432/llm_platform"
```

**Google Cloud SQL Pattern**:
```bash
# Dev
DATABASE_URL="postgresql://gaia_dev:password@/llm_platform?host=/cloudsql/project:region:gaia-dev"

# Staging
DATABASE_URL="postgresql://gaia_staging:password@/llm_platform?host=/cloudsql/project:region:gaia-staging"

# Production
DATABASE_URL="postgresql://gaia_prod:password@/llm_platform?host=/cloudsql/project:region:gaia-prod"
```

## Portability Features

### 1. Automatic URL Conversion
Already implemented in `app/shared/database.py`:
```python
# Convert postgres:// to postgresql:// for SQLAlchemy compatibility
raw_database_url = os.getenv("DATABASE_URL", "postgresql://...")
DATABASE_URL = raw_database_url.replace("postgres://", "postgresql://", 1) if raw_database_url.startswith("postgres://") else raw_database_url
```

### 2. Connection Pooling
```python
# Portable connection pooling configuration
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # Adjust based on environment
    max_overflow=20,        # Adjust based on load
    pool_pre_ping=True,     # Verify connections before use
    pool_recycle=3600      # Recycle connections after 1 hour
)
```

### 3. Migration Management
```bash
# Using Alembic for database migrations
alembic init migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

## Deployment Process

### 1. Database Initialization Script
```bash
#!/bin/bash
# scripts/init-database-portable.sh

ENVIRONMENT=$1
ADMIN_EMAIL=$2
PROVIDER=$3  # fly, aws, gcp, local

case $PROVIDER in
  fly)
    DATABASE_CMD="fly postgres connect -a gaia-db-${ENVIRONMENT}"
    ;;
  aws)
    DATABASE_CMD="psql $DATABASE_URL"
    ;;
  gcp)
    DATABASE_CMD="gcloud sql connect gaia-${ENVIRONMENT} --user=postgres"
    ;;
  local)
    DATABASE_CMD="psql postgresql://postgres:postgres@localhost:5432/gaia_${ENVIRONMENT}"
    ;;
esac

# Run initialization SQL
cat <<EOF | $DATABASE_CMD
-- Create tables
$(cat schemas/core_tables.sql)
$(cat schemas/service_tables.sql)

-- Initialize admin user
INSERT INTO users (email, name) VALUES ('$ADMIN_EMAIL', 'Admin');

-- Create admin API key
INSERT INTO api_keys (user_id, key_hash, name, permissions)
SELECT id, SHA256('admin-key-${ENVIRONMENT}'), 'Admin Key', '{"admin": true}'::jsonb
FROM users WHERE email = '$ADMIN_EMAIL';
EOF
```

### 2. Environment Configuration
```yaml
# config/database.yaml
dev:
  provider: fly
  host: gaia-db-dev.internal
  port: 5432
  database: postgres
  pool_size: 5
  max_overflow: 10

staging:
  provider: fly
  host: gaia-db-staging.internal
  port: 5432
  database: postgres
  pool_size: 10
  max_overflow: 20

production:
  provider: fly
  host: gaia-db-prod.internal
  port: 5432
  database: postgres
  pool_size: 20
  max_overflow: 40
  read_replicas:
    - host: gaia-db-prod-replica1.internal
    - host: gaia-db-prod-replica2.internal
```

## Scaling Strategies

### 1. Vertical Scaling (Single Database)
- **Dev**: 1 CPU, 256MB RAM, 10GB storage
- **Staging**: 2 CPUs, 1GB RAM, 50GB storage
- **Production**: 8 CPUs, 16GB RAM, 500GB storage

### 2. Horizontal Scaling (Read Replicas)
```python
# app/shared/database.py enhancement
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

class DatabaseManager:
    def __init__(self, environment: str):
        self.write_engine = create_engine(WRITE_DATABASE_URL)
        self.read_engines = [
            create_engine(url) for url in READ_DATABASE_URLS
        ]
    
    def get_read_session(self):
        # Load balance across read replicas
        engine = random.choice(self.read_engines)
        return SessionLocal(bind=engine)
    
    def get_write_session(self):
        return SessionLocal(bind=self.write_engine)
```

### 3. Sharding Strategy (Future)
```sql
-- User-based sharding for massive scale
-- Shard 1: Users with id % 4 = 0
-- Shard 2: Users with id % 4 = 1
-- Shard 3: Users with id % 4 = 2
-- Shard 4: Users with id % 4 = 3

CREATE OR REPLACE FUNCTION get_shard_for_user(user_id UUID) 
RETURNS INTEGER AS $$
BEGIN
    RETURN ('x' || substr(user_id::text, 1, 8))::bit(32)::int % 4;
END;
$$ LANGUAGE plpgsql;
```

## Backup and Recovery

### 1. Automated Backups
```bash
# scripts/backup-database.sh
#!/bin/bash
ENVIRONMENT=$1
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Provider-specific backup commands
case $PROVIDER in
  fly)
    fly postgres backup create -a gaia-db-${ENVIRONMENT}
    ;;
  aws)
    aws rds create-db-snapshot \
      --db-instance-identifier gaia-${ENVIRONMENT} \
      --db-snapshot-identifier gaia-${ENVIRONMENT}-${TIMESTAMP}
    ;;
  gcp)
    gcloud sql backups create \
      --instance=gaia-${ENVIRONMENT} \
      --description="Backup ${TIMESTAMP}"
    ;;
esac
```

### 2. Point-in-Time Recovery
- Enable transaction logs (WAL) archiving
- Maintain 7-day recovery window for production
- 3-day recovery window for staging
- Daily snapshots for dev

## Monitoring and Observability

### 1. Key Metrics
```sql
-- Connection monitoring
SELECT 
    datname,
    count(*) as connections,
    max(backend_start) as newest_connection
FROM pg_stat_activity
GROUP BY datname;

-- Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Slow queries
SELECT 
    query,
    mean_exec_time,
    calls
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### 2. Health Checks
```python
async def database_health_check():
    """Portable database health check."""
    try:
        # Test connection
        db = next(get_database_session())
        result = db.execute(text("SELECT 1"))
        
        # Check replication lag (if applicable)
        lag = db.execute(text("""
            SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::int as lag
        """)).scalar()
        
        return {
            "status": "healthy",
            "responsive": True,
            "replication_lag": lag or 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "responsive": False,
            "error": str(e)
        }
```

## Security Considerations

### 1. Connection Security
- Always use SSL/TLS for database connections
- Rotate credentials regularly
- Use connection pooling with encrypted connections

### 2. Access Control
```sql
-- Create read-only user for analytics
CREATE USER gaia_analytics WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE gaia TO gaia_analytics;
GRANT USAGE ON SCHEMA public TO gaia_analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO gaia_analytics;

-- Create service-specific users
CREATE USER gaia_chat WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON TABLE chat_messages TO gaia_chat;
```

### 3. Data Encryption
- Enable encryption at rest
- Use column-level encryption for sensitive data
- Implement field-level encryption in application layer

## Migration Path

### From Dev to Staging
```bash
# 1. Export schema from dev
pg_dump -h gaia-db-dev.internal -s > dev_schema.sql

# 2. Create staging database
fly postgres create --name gaia-db-staging --region lax

# 3. Import schema to staging
psql -h gaia-db-staging.internal < dev_schema.sql

# 4. Initialize staging data
./scripts/init-database-portable.sh staging admin@staging.gaia.com fly
```

### From Staging to Production
```bash
# 1. Review and approve schema
git tag -a v1.0.0-db -m "Production database schema v1.0.0"

# 2. Create production database with higher resources
fly postgres create --name gaia-db-prod --region lax --vm-size dedicated-cpu-2x

# 3. Apply migrations
alembic upgrade head

# 4. Initialize production data
./scripts/init-database-portable.sh production admin@gaia.com fly
```

## Summary

This portable database architecture provides:

1. **Consistency**: Same schema and patterns across all environments
2. **Flexibility**: Easy migration between cloud providers
3. **Scalability**: Clear path from single instance to sharded cluster
4. **Security**: Proper isolation and access control
5. **Maintainability**: Automated backups and monitoring

The architecture supports growth from prototype to production scale while maintaining operational simplicity.