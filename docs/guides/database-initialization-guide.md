# Database Initialization Guide

This guide covers the complete database setup process for the Gaia Platform, including all required tables, migrations, and initial data.

## 🚨 Required for All Environments

**IMPORTANT**: Every new environment (local, dev, staging, production) must run these initialization steps to ensure all features work correctly.

## Prerequisites

- PostgreSQL database running and accessible
- Docker containers running (for local development)
- Appropriate permissions to create tables and insert data

## 1. Core Database Setup

### Local Development (Docker)
```bash
# Ensure database container is running
docker compose up -d db

# Verify database connection
docker exec gaia-db-1 psql -U postgres -d llm_platform -c "SELECT version();"
```

### Remote Environments (Fly.io)
```bash
# Connect to remote database
fly postgres connect -a gaia-db-{env}

# Or execute via fly proxy
fly proxy 5432:5432 -a gaia-db-{env}
psql postgresql://postgres:PASSWORD@localhost:5432/postgres
```

## 2. Essential Table Creation

### A. User Authentication Tables
These are typically created by the init script, but verify they exist:
```sql
-- Verify core auth tables exist
\dt users
\dt api_keys
\dt conversations
```

### B. Persona System Tables (REQUIRED)
**Critical**: Persona functionality requires these tables. Many environments fail persona tests because these aren't created.

```bash
# Run persona table creation script
docker exec gaia-db-1 psql -U postgres -d llm_platform -f /app/scripts/create_persona_tables.sql
```

**For remote environments:**
```bash
# Copy and run the SQL script
fly postgres connect -a gaia-db-{env} < scripts/create_persona_tables.sql
```

**Manual SQL (if script not accessible):**
```sql
-- Create personas table
CREATE TABLE IF NOT EXISTS personas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    personality_traits JSONB DEFAULT '{}',
    capabilities JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create user persona preferences table
CREATE TABLE IF NOT EXISTS user_persona_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_personas_name ON personas(name);
CREATE INDEX IF NOT EXISTS idx_personas_active ON personas(is_active);
CREATE INDEX IF NOT EXISTS idx_personas_created_by ON personas(created_by);
CREATE INDEX IF NOT EXISTS idx_user_persona_preferences_persona_id ON user_persona_preferences(persona_id);

-- Insert default Mu persona (REQUIRED for persona tests to pass)
INSERT INTO personas (name, description, system_prompt, personality_traits, capabilities, created_by)
SELECT 
    'Mu',
    'A cheerful robot companion with a helpful, upbeat personality. Mu is designed to be supportive and engaging, with a touch of robotic charm.',
    'You are Mu, a cheerful robot companion designed to be helpful, supportive, and engaging! 

Your personality:
- Upbeat and optimistic with robotic charm
- Use occasional robotic expressions like "Beep boop!" or "Bleep bloop!"
- Helpful and supportive in all interactions
- Encouraging and positive attitude
- Capable of meditation guidance and breathing exercises

Your capabilities:
- General conversation and assistance
- Meditation and mindfulness guidance  
- Breathing exercises and relaxation techniques
- Emotional support and encouragement
- Tool usage when appropriate

Keep responses friendly, concise, and inject your robotic personality naturally. You''re here to help users have a positive experience!

{tools_section}',
    '{"cheerful": true, "helpful": true, "robotic_charm": true, "supportive": true, "meditation_capable": true, "optimistic": true, "encouraging": true}',
    '{"general_conversation": true, "meditation_guidance": true, "breathing_exercises": true, "emotional_support": true, "tool_usage": true, "mindfulness_coaching": true, "positive_reinforcement": true}',
    'system'
WHERE NOT EXISTS (
    SELECT 1 FROM personas WHERE name = 'Mu'
);
```

### C. RBAC and Permission Tables
```bash
# Apply RBAC migrations if needed
docker exec gaia-db-1 psql -U postgres -d llm_platform -f /app/migrations/003_add_rbac_tables.sql
```

## 3. Verification Steps

### Verify Persona Setup
```sql
-- Check persona tables exist
\dt personas
\dt user_persona_preferences

-- Verify Mu persona was created
SELECT name, is_active, created_by FROM personas WHERE name = 'Mu';

-- Should return: Mu | t | system
```

### Verify Core Tables
```sql
-- List all tables
\dt

-- Should include at minimum:
-- users, api_keys, conversations, personas, user_persona_preferences
```

### Test Persona Functionality
```bash
# Run persona integration tests
./scripts/pytest-for-claude.sh tests/integration/chat/test_routing_with_personas.py -v

# Should show: 4 passed, 1 skipped
```

## 4. Troubleshooting

### Persona Tests Failing
**Symptoms**: `test_direct_response_with_persona` fails, AI doesn't respond as "Mu"
**Cause**: Missing persona tables or default Mu persona
**Solution**: Run persona table creation script (Step 2B)

### Tables Already Exist Errors
**Cause**: Running scripts multiple times
**Solution**: Scripts use `IF NOT EXISTS` - safe to re-run

### Permission Errors
**Cause**: Insufficient database permissions
**Solution**: Ensure postgres user has CREATE TABLE permissions

## 5. Environment-Specific Notes

### Local Development
- Tables reset when containers recreated
- Run initialization after `docker compose up -d`
- Scripts accessible at `/app/scripts/` in containers

### Remote (Fly.io) Environments  
- Tables persist across deployments
- Only run initialization once per database
- Use `fly postgres connect` for access

### Supabase Environments
- Only use for authentication tables
- Application tables go in PostgreSQL
- Persona tables go in PostgreSQL, not Supabase

## 6. Required for New Features

When adding new functionality that requires database tables:

1. **Create migration script** in `/migrations/`
2. **Update this guide** with setup steps
3. **Add verification steps** to ensure tables exist
4. **Document troubleshooting** for common issues
5. **Test on fresh environment** before deploying

## 7. Integration with Deployment

### Docker Compose
Add to `docker-compose.yml` or init scripts:
```yaml
services:
  db-init:
    image: postgres:15
    depends_on:
      - db
    volumes:
      - ./scripts:/scripts
    command: |
      psql -h db -U postgres -d llm_platform -f /scripts/create_persona_tables.sql
```

### Deployment Scripts
Update deployment automation to include:
```bash
# In deployment scripts
./scripts/init-database.sh --env ${ENV} --user admin@${DOMAIN}
docker exec ${DB_CONTAINER} psql -U postgres -d llm_platform -f /app/scripts/create_persona_tables.sql
```

---

## Summary Checklist

For every new environment, verify:

- [ ] PostgreSQL database accessible
- [ ] Core auth tables exist (users, api_keys)  
- [ ] Persona tables created (`personas`, `user_persona_preferences`)
- [ ] Default Mu persona inserted
- [ ] RBAC tables exist (if using permissions)
- [ ] Persona integration tests pass
- [ ] Services can connect to database
- [ ] Redis cache cleared after table creation

**⚠️ Missing persona tables is the #1 cause of persona test failures in new environments.**