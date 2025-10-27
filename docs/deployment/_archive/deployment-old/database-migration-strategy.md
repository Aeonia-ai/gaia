# Database Migration Strategy

## Overview

This document outlines the strategy for keeping database schemas synchronized between local development and remote environments (dev, staging, production) for the Gaia Platform.

## Current Issues

1. **No Migration Tracking**: Currently no system to track which migrations have been applied
2. **Manual Application**: Migrations are applied manually and inconsistently
3. **Mixed Approaches**: Some tables created via scripts (`scripts/create_persona_tables.sql`), others via migrations
4. **Number Conflicts**: Duplicate migration numbers (003, 004, 005)

## Proposed Solution

### 1. Migration Tracking Table

Create a `schema_migrations` table to track applied migrations:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(255),
    checksum VARCHAR(64),
    execution_time_ms INTEGER
);
```

### 2. Migration Naming Convention

Use timestamp-based naming to avoid conflicts:
```
YYYYMMDDHHMMSS_description.sql
Example: 20250813140000_create_conversations_table.sql
```

### 3. Migration Structure

Each migration file should include:
```sql
-- Migration: 20250813140000_create_conversations_table.sql
-- Description: Creates conversations table for chat organization

BEGIN;

-- Migration logic here
CREATE TABLE conversations (...);

-- Record migration
INSERT INTO schema_migrations (version, applied_by) 
VALUES ('20250813140000_create_conversations_table', 'migration_script');

COMMIT;
```

### 4. Migration Script

Create `scripts/migrate.py`:
```python
#!/usr/bin/env python3
"""Database migration runner"""

import os
import hashlib
import psycopg2
from datetime import datetime

class MigrationRunner:
    def __init__(self, database_url):
        self.conn = psycopg2.connect(database_url)
        self.ensure_migration_table()
    
    def ensure_migration_table(self):
        """Create schema_migrations table if it doesn't exist"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_by VARCHAR(255) DEFAULT 'migration_script',
                checksum VARCHAR(64),
                execution_time_ms INTEGER
            )
        """)
        self.conn.commit()
    
    def get_applied_migrations(self):
        """Get list of already applied migrations"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
        return [row[0] for row in cursor.fetchall()]
    
    def apply_migration(self, filepath):
        """Apply a single migration file"""
        filename = os.path.basename(filepath)
        version = filename.replace('.sql', '')
        
        # Check if already applied
        if version in self.get_applied_migrations():
            print(f"⏭️  Skipping {filename} (already applied)")
            return
        
        # Read migration content
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Calculate checksum
        checksum = hashlib.sha256(content.encode()).hexdigest()
        
        # Apply migration
        cursor = self.conn.cursor()
        start_time = datetime.now()
        
        try:
            cursor.execute(content)
            
            # Record migration
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            cursor.execute(
                "INSERT INTO schema_migrations (version, checksum, execution_time_ms) VALUES (%s, %s, %s)",
                (version, checksum, execution_time)
            )
            
            self.conn.commit()
            print(f"✅ Applied {filename} ({execution_time}ms)")
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Failed {filename}: {e}")
            raise
    
    def run_migrations(self, migrations_dir='migrations'):
        """Run all pending migrations"""
        migrations = sorted([
            f for f in os.listdir(migrations_dir) 
            if f.endswith('.sql') and not f.startswith('_')
        ])
        
        print(f"Found {len(migrations)} migration files")
        
        for migration in migrations:
            filepath = os.path.join(migrations_dir, migration)
            self.apply_migration(filepath)
        
        print("\n✅ All migrations completed!")

if __name__ == "__main__":
    import sys
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    runner = MigrationRunner(database_url)
    runner.run_migrations()
```

### 5. Seed Data Management

Keep seed data separate from schema migrations:

```
migrations/
  ├── schema/           # Schema changes only
  │   └── 20250813140000_create_tables.sql
  └── seeds/            # Data that should exist in all environments
      ├── 001_default_personas.sql
      └── 002_system_users.sql
```

### 6. CI/CD Integration

Add to deployment pipeline:
```bash
# Deploy script snippet
echo "🔄 Running database migrations..."
fly ssh console -a $APP_NAME -C 'cd /app && python scripts/migrate.py'

# Verify migrations
fly ssh console -a $APP_NAME -C 'psql $DATABASE_URL -c "SELECT version, applied_at FROM schema_migrations ORDER BY version DESC LIMIT 5;"'
```

### 7. Rollback Strategy

Each migration should have a corresponding rollback:
```
migrations/
  ├── up/
  │   └── 20250813140000_create_conversations.sql
  └── down/
      └── 20250813140000_create_conversations.sql
```

### 8. Local Development Workflow

```bash
# Pull latest code
git pull

# Run migrations locally
DATABASE_URL=postgresql://localhost/gaia_dev python scripts/migrate.py

# Create new migration
./scripts/create-migration.sh "add_user_settings_table"
```

## Implementation Steps

1. **Clean up existing migrations**: Rename with timestamps to avoid conflicts
2. **Create migration runner**: Implement the Python script above
3. **Add to deployment**: Update deployment scripts to run migrations
4. **Document process**: Update developer onboarding docs
5. **Monitor**: Add alerts for migration failures

## Benefits

- **Consistency**: Same schema across all environments
- **Auditability**: Track who applied what and when
- **Safety**: Prevent duplicate applications
- **Automation**: Integrate with CI/CD pipeline
- **Rollback**: Easy to revert problematic changes

## Next Steps

1. Implement migration tracking table
2. Rename existing migrations with timestamps
3. Create migration runner script
4. Test on dev environment
5. Roll out to staging and production