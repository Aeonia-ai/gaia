##Experience Reset Guide

**Purpose**: Reset game experiences to pristine initial state for demos, testing, or recovery.

**Use Cases**:
- 🎬 **Demo preparation** - Start with fresh world for product demos
- 🧪 **Testing** - Reset between test runs
- 🔄 **Content iteration** - Test changes from clean state
- 🚨 **Recovery** - Restore after corruption or mistakes

---

## Quick Reference

### Fastest: CLI Script
```bash
# Full reset (recommended for demos)
./scripts/reset-experience.sh wylding-woods

# Force without confirmation (be careful!)
./scripts/reset-experience.sh --force wylding-woods
```

### Most Control: Admin Command
```bash
# Via KB endpoint
curl -X POST "http://localhost:8001/experience/interact" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message":"@reset experience CONFIRM","experience":"wylding-woods"}'
```

### Manual: Direct File Operations
```bash
# Backup current state
docker exec gaia-kb-service-1 cp \
  /kb/experiences/wylding-woods/state/world.json \
  /kb/experiences/wylding-woods/state/world.backup.json

# Restore from template
docker exec gaia-kb-service-1 cp \
  /kb/experiences/wylding-woods/state/world.template.json \
  /kb/experiences/wylding-woods/state/world.json

# Clear player data
docker exec gaia-kb-service-1 rm -rf /kb/players/*/wylding-woods/
```

---

## Method 1: CLI Script (Recommended)

**Location**: `scripts/reset-experience.sh`

**Features**:
- ✅ Interactive confirmation (unless --force)
- ✅ Automatic backups
- ✅ Backup rotation (keeps last 5)
- ✅ Preview before execution
- ✅ Support for partial resets

### Basic Usage

**Full Reset** (world + all players):
```bash
./scripts/reset-experience.sh wylding-woods

# Output:
╔════════════════════════════════════╗
║   GAIA Experience Reset Tool      ║
╚════════════════════════════════════╝

Analyzing current state...

═══════════════════════════════════════
  Reset Preview: wylding-woods
═══════════════════════════════════════

State Model: shared

❗ Full reset:
   - Restore world state from template
   - Delete 5 player views
   - Clear 12 NPC conversations
   - Reset all inventories

📦 Backup will be created

═══════════════════════════════════════

Proceed with reset? [y/N]: y

Starting reset...

Creating backup...
✓ Backup created: backups/world.20251028_163045.json
Rotating old backups...
Resetting world state...
✓ World state restored from template
Resetting player data...
✓ Cleared 5 player view(s)

═══════════════════════════════════════
  Reset Complete: wylding-woods
═══════════════════════════════════════

📦 Backup: backups/world.20251028_163045.json

♻️  Reset summary:
   - World state restored
   - 5 player view(s) cleared
   - 12 NPC conversation(s) cleared

Experience is now in pristine initial state

Next steps:
  - Test: curl POST /experience/interact -d '{"message":"look around"}'
  - Stats: curl POST /experience/interact -d '{"message":"@stats"}'
  - List: curl POST /experience/interact -d '{"message":"@list waypoints"}'
```

### Advanced Options

**World Only** (keep player data):
```bash
./scripts/reset-experience.sh --world-only wylding-woods

# Restores world state but keeps:
# - Player inventories
# - NPC conversation histories
# - Player positions
```

**Single Player**:
```bash
./scripts/reset-experience.sh --player jason@aeonia.ai wylding-woods

# Only resets one player:
# - Deletes their view file
# - Clears their inventory
# - Resets NPC conversations with them
```

**Force Mode** (skip confirmation):
```bash
./scripts/reset-experience.sh --force wylding-woods

# Dangerous! No confirmation prompt.
# Use only in automated scripts.
```

**No Backup** (fastest, risky):
```bash
./scripts/reset-experience.sh --no-backup wylding-woods

# Skips backup creation.
# Only use if you have backups elsewhere!
```

### Script Options Summary

```
Options:
  --world-only        Reset world state only (keep player data)
  --player <user_id>  Reset specific player only
  --no-backup         Skip backup creation (dangerous!)
  --force             Skip confirmation prompt
  -h, --help          Show help message
```

---

## Method 2: Admin Command

**Location**: `@reset-experience.md` admin command

**Features**:
- ✅ Works through API (no shell access needed)
- ✅ Integrated with chat interface
- ✅ Same safety as CLI script
- ✅ Can be used by content creators

### Via Direct API

```bash
# Step 1: Preview reset (no CONFIRM)
curl -X POST "http://localhost:8001/experience/interact" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "message": "@reset experience",
    "experience": "wylding-woods"
  }'

# Response shows preview:
{
  "success": false,
  "requires_confirmation": true,
  "narrative": "⚠️ Reset Experience: wylding-woods\n\n...\n\nTo confirm: @reset experience CONFIRM"
}

# Step 2: Execute reset
curl -X POST "http://localhost:8001/experience/interact" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "message": "@reset experience CONFIRM",
    "experience": "wylding-woods"
  }'

# Response confirms completion:
{
  "success": true,
  "narrative": "✅ Experience reset: wylding-woods\n\n📦 Backup created: ..."
}
```

### Via Chat Interface

```bash
# Through Game Master persona
curl -X POST "http://localhost:8666/api/v0.3/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "message": "@reset experience CONFIRM",
    "persona_id": "7b197909-8837-4ed5-a67a-a05c90e817f1"
  }'
```

### Admin Command Variations

**Full reset**:
```bash
"@reset experience CONFIRM"
"@reset experience wylding-woods CONFIRM"
```

**World only**:
```bash
"@reset world CONFIRM"
"@reset world wylding-woods CONFIRM"
```

**Single player**:
```bash
"@reset player jason@aeonia.ai CONFIRM"
```

---

## Method 3: Manual Reset

**When to use**:
- Script/command not available
- Emergency recovery
- Custom reset scenarios

### Shared Model (wylding-woods)

**Step 1: Backup Current State**
```bash
docker exec gaia-kb-service-1 bash -c '
  mkdir -p /kb/experiences/wylding-woods/state/backups
  cp /kb/experiences/wylding-woods/state/world.json \
     /kb/experiences/wylding-woods/state/backups/world.$(date +%Y%m%d_%H%M%S).json
'
```

**Step 2: Restore from Template**
```bash
docker exec gaia-kb-service-1 cp \
  /kb/experiences/wylding-woods/state/world.template.json \
  /kb/experiences/wylding-woods/state/world.json
```

**Step 3: Clear Player Data**
```bash
# All players
docker exec gaia-kb-service-1 rm -rf /kb/players/*/wylding-woods/

# Single player
docker exec gaia-kb-service-1 rm -rf /kb/players/jason@aeonia.ai/wylding-woods/
```

**Step 4: Verify Reset**
```bash
curl -X POST "http://localhost:8001/experience/interact" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message":"@stats","experience":"wylding-woods"}'
```

### Isolated Model (west-of-house)

**For isolated model, each player has their own world copy.**

**Step 1: Delete Player Views**
```bash
# All players
docker exec gaia-kb-service-1 rm -rf /kb/players/*/west-of-house/

# Single player
docker exec gaia-kb-service-1 rm -rf /kb/players/jason@aeonia.ai/west-of-house/
```

**Step 2: Auto-Bootstrap on Next Play**

Players will automatically get fresh world copy from template on next login:
- Template: `/kb/experiences/west-of-house/state/world.template.json`
- Copied to: `/kb/players/{user}/west-of-house/view.json`

---

## What Gets Reset

### World State
- ✅ **Item placements** - All items return to original locations
- ✅ **Item states** - Collectible items become uncollected
- ✅ **NPC positions** - NPCs return to initial locations
- ✅ **Door states** - Locked/unlocked reset to defaults
- ✅ **Quest progress** - Quest states cleared
- ✅ **World variables** - Custom flags/counters reset

### Player State
- ✅ **Inventories** - All items removed
- ✅ **Positions** - Players start at initial location
- ✅ **NPC relationships** - Conversation histories cleared
- ✅ **Trust levels** - NPC trust reset to defaults
- ✅ **Achievements** - Progress reset
- ✅ **Visited locations** - All marked unvisited

### What Doesn't Change
- ❌ **Waypoint definitions** - GPS coordinates unchanged
- ❌ **NPC templates** - Personality/quests unchanged
- ❌ **Item definitions** - Properties unchanged
- ❌ **Location structure** - Sublocations unchanged
- ❌ **Game logic** - Commands unchanged

---

## State Models

### Shared Model (Multiplayer)

**Example**: wylding-woods

**File Structure**:
```
/kb/experiences/wylding-woods/
  state/
    world.json           # Current shared world state
    world.template.json  # Pristine template
    backups/             # Timestamped backups
      world.20251028_163045.json
      world.20251028_145230.json
      ...

/kb/players/{user_id}/wylding-woods/
  view.json              # Player's view (position, inventory refs)
  npcs/                  # NPC conversation histories
    louisa.json
    woander.json
```

**Reset Process**:
1. Backup `world.json`
2. Copy `world.template.json` → `world.json`
3. Delete all `/kb/players/*/wylding-woods/` directories
4. Players bootstrap fresh views on next login

**Result**: Fresh shared world, all players start clean

### Isolated Model (Single-Player)

**Example**: west-of-house

**File Structure**:
```
/kb/experiences/west-of-house/
  state/
    world.template.json  # Template for player copies

/kb/players/{user_id}/west-of-house/
  view.json              # Player's own world copy
```

**Reset Process**:
1. Delete `/kb/players/{user}/west-of-house/view.json`
2. On next login: Auto-copy from template

**Result**: Each player gets fresh isolated world

---

## Recovery from Backup

### List Available Backups

```bash
docker exec gaia-kb-service-1 ls -lh \
  /kb/experiences/wylding-woods/state/backups/

# Output:
world.20251028_163045.json  # Most recent
world.20251028_145230.json
world.20251027_093012.json
...
```

### Restore Specific Backup

```bash
# Choose backup by timestamp
docker exec gaia-kb-service-1 cp \
  /kb/experiences/wylding-woods/state/backups/world.20251028_163045.json \
  /kb/experiences/wylding-woods/state/world.json
```

### Emergency: Create Template from Current

If you need to save current state as new template:

```bash
docker exec gaia-kb-service-1 cp \
  /kb/experiences/wylding-woods/state/world.json \
  /kb/experiences/wylding-woods/state/world.template.json
```

---

## Demo Preparation Workflow

**Best practice for demo preparation:**

### 1. Test Your Demo Flow
```bash
# Play through your demo scenario
# - Create waypoints
# - Interact with NPCs
# - Collect items
# - Test all features
```

### 2. Save as Template (Optional)
```bash
# If you want to start demos from this state
docker exec gaia-kb-service-1 cp \
  /kb/experiences/wylding-woods/state/world.json \
  /kb/experiences/wylding-woods/state/world.template.json
```

### 3. Before Each Demo
```bash
# Quick reset
./scripts/reset-experience.sh --force wylding-woods

# Or via API
curl -X POST "http://localhost:8001/experience/interact" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message":"@reset experience CONFIRM","experience":"wylding-woods"}'
```

### 4. Verify Clean State
```bash
curl -X POST "http://localhost:8001/experience/interact" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message":"@stats","experience":"wylding-woods"}'

# Should show:
# - All items in original locations
# - 0 active players
# - 0 NPC conversations
```

---

## Troubleshooting

### Template File Missing

**Problem**: `world.template.json` not found

**Solution**: Create from current state
```bash
docker exec gaia-kb-service-1 bash -c '
  if [ ! -f /kb/experiences/wylding-woods/state/world.template.json ]; then
    cp /kb/experiences/wylding-woods/state/world.json \
       /kb/experiences/wylding-woods/state/world.template.json
    echo "Template created"
  fi
'
```

### Container Not Running

**Problem**: `gaia-kb-service-1` container not found

**Solution**: Start services
```bash
docker compose up -d
```

### Permission Denied

**Problem**: Cannot write to backup directory

**Solution**: Check container permissions
```bash
docker exec gaia-kb-service-1 ls -la /kb/experiences/wylding-woods/state/
```

### Items Not Resetting

**Problem**: Items still in wrong locations after reset

**Solution**: Verify template has correct placements
```bash
docker exec gaia-kb-service-1 cat \
  /kb/experiences/wylding-woods/state/world.template.json | jq '.locations'
```

### Players Still Have Progress

**Problem**: Players still have inventory after reset

**Solution**: Ensure player directories were deleted
```bash
docker exec gaia-kb-service-1 ls /kb/players/*/wylding-woods/
# Should return: No such file or directory
```

---

## Safety Best Practices

### Always Backup Before Reset

The script and command do this automatically, but for manual:
```bash
# Timestamped backup
docker exec gaia-kb-service-1 bash -c '
  mkdir -p /kb/experiences/wylding-woods/state/backups
  cp /kb/experiences/wylding-woods/state/world.json \
     /kb/experiences/wylding-woods/state/backups/world.$(date +%Y%m%d_%H%M%S).json
'
```

### Test Reset in Dev First

Never reset production without testing:
```bash
# Test in dev
./scripts/reset-experience.sh wylding-woods

# Verify works
curl "http://localhost:8001/experience/interact" -d '{"message":"look around"}'

# Then deploy to production
```

### Keep Multiple Backups

Script rotates and keeps last 5 automatically:
```bash
docker exec gaia-kb-service-1 ls -1 \
  /kb/experiences/wylding-woods/state/backups/ | head -5

# Manually clean old backups if needed
docker exec gaia-kb-service-1 bash -c '
  cd /kb/experiences/wylding-woods/state/backups
  ls -t world.*.json | tail -n +6 | xargs rm
'
```

### Document Your Template

Add notes to template about what state it represents:
```json
{
  "metadata": {
    "version": "1.0.0",
    "state_model": "shared",
    "template_notes": "Demo state: All items at original locations, Louisa quest available",
    "created_at": "2025-10-28T16:30:00Z"
  }
}
```

---

## Related Documentation

- [033-admin-command-system.md](./033-admin-command-system.md) - Admin commands overview
- [030-unified-state-model-implementation.md](./030-unified-state-model-implementation.md) - State model architecture
- [035-product-demo-guide.md](./035-product-demo-guide.md) - Demo preparation and execution

---

## Quick Command Reference

```bash
# CLI Script
./scripts/reset-experience.sh wylding-woods
./scripts/reset-experience.sh --world-only wylding-woods
./scripts/reset-experience.sh --player jason@aeonia.ai wylding-woods
./scripts/reset-experience.sh --force wylding-woods

# Admin Command
curl -X POST "http://localhost:8001/experience/interact" \
  -d '{"message":"@reset experience CONFIRM","experience":"wylding-woods"}'

# Manual
docker exec gaia-kb-service-1 cp \
  /kb/experiences/wylding-woods/state/world.template.json \
  /kb/experiences/wylding-woods/state/world.json
docker exec gaia-kb-service-1 rm -rf /kb/players/*/wylding-woods/

# Verify
curl -X POST "http://localhost:8001/experience/interact" \
  -d '{"message":"@stats","experience":"wylding-woods"}'
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-28
**Author**: GAIA Platform Team
