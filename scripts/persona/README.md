# Persona Management Guide

This directory contains persona definition files and scripts for managing AI personas in the GAIA platform.

## 📁 Directory Structure

```
scripts/persona/
├── README.md                       # This file
├── update_persona.sh               # Automated update script
├── *.txt                           # Persona system prompt files
├── update_game_master_example.sql  # Example SQL update script
└── *-backup-*.txt                  # Timestamped backups
```

## 🎭 Available Personas

### Database Personas (ID-based)
These personas are stored in the `personas` table and referenced by UUID:

- **Game Master** (`7b197909-8837-4ed5-a67a-a05c90e817f1`) - Game command processor for MMOIRL experiences
- **Louisa** - Character persona for Wylding Woods
- **Mu** - Character persona
- **GAIA-MMOIRL** - Primary platform persona

### File-based Personas
Persona definition files in this directory:

- `game-master-strict.txt` - Strict game command processor (no creative embellishment)
- `game-master.txt` - Standard game master persona
- `louisa-*.txt` - Louisa character variations
- `mu-*.txt` - Mu character variations

## 🔄 Updating Personas in the Database

### Automated Method (Recommended)

Use the `update_persona.sh` script for safe, automated updates:

```bash
# Usage: ./update_persona.sh <persona-file> <persona-uuid>
./update_persona.sh game-master-strict.txt 7b197909-8837-4ed5-a67a-a05c90e817f1
```

**What the script does:**
1. ✅ Validates inputs (file exists, valid UUID format)
2. ✅ Creates timestamped backup automatically
3. ✅ Verifies persona exists in database before updating
4. ✅ Escapes SQL quotes automatically
5. ✅ Generates and executes SQL script
6. ✅ Verifies update succeeded
7. ✅ Cleans up temporary files
8. ✅ Asks for confirmation before making changes

**Example output:**
```
════════════════════════════════════════════════════════════
  Persona Database Update Script
════════════════════════════════════════════════════════════

→ Persona file: game-master-strict.txt
→ Persona UUID: 7b197909-8837-4ed5-a67a-a05c90e817f1

✓ Backup created
✓ Found persona: Game Master
✓ Quotes escaped
✓ SQL script generated

Continue with update? [y/N] y

✓ Database update successful
✓ Update verified
```

### Manual Process (Advanced)

1. **Backup the persona file** (always!)
   ```bash
   cp game-master-strict.txt game-master-strict-backup-$(date +%Y%m%d-%H%M%S).txt
   ```

2. **Edit the persona file**
   ```bash
   # Make your changes to the .txt file
   vim game-master-strict.txt
   ```

3. **Generate SQL with proper escaping**
   ```bash
   # Escape single quotes (SQL requirement: ' becomes '')
   cat game-master-strict.txt | sed "s/'/''/g" > /tmp/persona_escaped.txt

   # Create UPDATE SQL script
   cat > /tmp/update_persona.sql << 'EOF'
   UPDATE personas
   SET system_prompt = '<paste escaped content here>',
       updated_at = NOW()
   WHERE id = '<persona-uuid>';

   -- Verify the update
   SELECT id, name, LEFT(system_prompt, 150) as prompt_preview
   FROM personas
   WHERE id = '<persona-uuid>';
   EOF
   ```

4. **Execute the update**
   ```bash
   docker exec -i gaia-db-1 psql -U postgres -d llm_platform < /tmp/update_persona.sql
   ```

5. **Verify the update**
   ```bash
   docker exec gaia-db-1 psql -U postgres -d llm_platform -c \
     "SELECT name, updated_at, LENGTH(system_prompt) as prompt_length FROM personas WHERE id = '<persona-uuid>';"
   ```

### Example SQL Script

See `update_game_master_example.sql` for a complete working example.

## 🔑 Critical Lessons

### 1. SQL Quote Escaping is Mandatory
PostgreSQL requires single quotes in text to be doubled:
- ❌ **Wrong**: `'You can't do that'`
- ✅ **Correct**: `'You can''t do that'`

Use `sed "s/'/''/g"` to automatically escape quotes in persona files.

### 2. Always Backup Before Updating
Create timestamped backups to preserve persona evolution:
```bash
cp persona.txt persona-backup-$(date +%Y%m%d-%H%M%S).txt
```

### 3. Verify Updates Immediately
Always run verification queries after UPDATE to confirm:
- Row was updated (`UPDATE 1`)
- Timestamp changed (`updated_at`)
- Content length is correct
- Preview shows expected changes

### 4. Test with Trivial Changes First
Before major persona rewrites:
1. Add a small marker like `[Test Update - Version 1.1]`
2. Execute the full update process
3. Verify the marker appears in the database
4. Confirms your process works before risking important changes

### 5. Persona Schema Reference
```sql
CREATE TABLE personas (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    system_prompt TEXT NOT NULL,        -- This is what you update
    personality_traits JSONB DEFAULT '{}',
    capabilities JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()  -- Auto-updated
);
```

## 📋 Persona IDs Quick Reference

| Persona | UUID | File |
|---------|------|------|
| Game Master | `7b197909-8837-4ed5-a67a-a05c90e817f1` | `game-master-strict.txt` |

To find persona IDs:
```bash
docker exec gaia-db-1 psql -U postgres -d llm_platform -c \
  "SELECT id, name, description FROM personas ORDER BY name;"
```

## 🛠️ Troubleshooting

### "Syntax error near '" in UPDATE
**Problem**: Single quotes not properly escaped
**Solution**: Use `sed "s/'/''/g"` to double all single quotes

### "UPDATE 0" (no rows updated)
**Problem**: Wrong UUID or persona doesn't exist
**Solution**: Verify UUID with `SELECT id, name FROM personas;`

### Changes don't appear in chat
**Problem**: Redis cache or service not reloaded
**Solution**:
```bash
# Clear Redis cache
docker exec gaia-redis-1 redis-cli FLUSHALL

# Or restart chat service
docker compose restart chat-service
```

## 📚 Related Documentation

- [Database Initialization Guide](../../docs/current/development/database-initialization-guide.md)
- [Persona System Architecture](../../docs/current/architecture/persona-system.md) (if exists)
- [Testing Guide](../../docs/testing/TESTING_GUIDE.md)

## 🎯 Best Practices

1. **Version your personas**: Add version markers in comments (e.g., `[Version 1.1 - 2025-10-28]`)
2. **Document changes**: Keep backup files with timestamps
3. **Test in isolation**: Update one persona at a time
4. **Verify in chat**: Test persona behavior after updates
5. **Use transactions**: Wrap multiple updates in `BEGIN; ... COMMIT;` blocks

## 🔐 Security Notes

- Persona system prompts are stored as plain text in PostgreSQL
- Sensitive instructions should not be placed in persona prompts
- All persona updates are logged with `updated_at` timestamps
- Database access requires PostgreSQL credentials (see `.env`)
