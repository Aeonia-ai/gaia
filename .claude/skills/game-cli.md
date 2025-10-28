# Game CLI Skill - GAIA Platform

**Purpose**: This skill teaches you how to interface with the GAIA game system via CLI, both as a player testing gameplay and as an admin building worlds.

**Activation**: Use this skill when:
- Testing game commands and interactions
- Building or exploring game worlds
- Debugging KB-driven command processing
- Working with admin commands or player experiences

---

## Two Modes of Interaction

### Player Mode - Natural Language Gameplay

**Purpose**: Test gameplay as an end user would experience it

**Commands**: Natural language phrases
- "go north"
- "take the dream bottle"
- "look around"
- "talk to Louisa"
- "examine the fairy door"

**How it works**:
1. LLM interprets natural language → extracts intent
2. KB system loads relevant game content (markdown files)
3. Returns structured GameCommandResponse with narrative + state changes

**Response Time**: ~1.5-2s (includes LLM parsing)

**Use cases**:
- Testing player experience
- Verifying quest logic
- Exploring game narrative
- Debugging natural language understanding

---

### Admin Mode - Structured World Building

**Purpose**: Build and manage game worlds with zero latency

**Commands**: Structured @ prefix commands
- `@stats` - World statistics
- `@list waypoints` - List all waypoints
- `@create location waypoint_28a forest_path Forest Path`
- `@connect waypoint_28a clearing center shelf_1 north`
- `@inspect sublocation waypoint_28a clearing center`
- `@edit waypoint waypoint_28a description A mystical forest`
- `@delete sublocation waypoint_28a clearing old_spot CONFIRM`
- `@where louisa` - Find NPC/item by name
- `@find dream_bottle` - Find all instances of template

**How it works**:
1. Direct file access (no LLM)
2. Atomic JSON operations
3. Instant response

**Response Time**: <30ms (zero LLM latency)

**Use cases**:
- Building new areas
- Managing navigation graphs
- Debugging world structure
- Rapid iteration during development

---

## CLI Tool: `scripts/gaia_client.py`

### Basic Usage

**Interactive mode:**
```bash
# Connect to local dev environment
python scripts/gaia_client.py --env local

# Connect to dev/staging/prod
python scripts/gaia_client.py --env dev
```

**Batch mode (single command):**
```bash
# Send one command and exit
python scripts/gaia_client.py --env local --batch "look around"

# With logging
python scripts/gaia_client.py --env local --batch "take bottle" --log
```

### Chat Commands (/ prefix)

While in interactive mode, use `/` commands for client operations:

```bash
/help                    # Show all commands
/new [title]            # Start new conversation
/list                   # List conversations
/personas               # List available personas
/persona <id>           # Switch persona
/status                 # Check system status
/login <email> <pass>   # JWT authentication
/logout                 # Clear session
/quit                   # Exit
```

### Game Commands

**Player commands** - Natural language:
```
You: look around
Assistant: You're in the center of a magical clearing...

You: take the bottle from shelf_1
Assistant: You carefully lift the dream bottle...
```

**Admin commands** - Structured @ prefix:
```
You: @stats
Assistant: World Statistics (wylding-woods):
  Waypoints: 2
  Locations: 3
  Sublocations: 11
  Items: 5
  NPCs: 1

You: @list locations waypoint_28a
Assistant: Locations in waypoint_28a:
  1. clearing (Forest Clearing) - 6 sublocations
  2. woander_store (Woander Store) - 4 sublocations
```

---

## Direct API Testing (Python Scripts)

### Quick Test Pattern

**File**: `test_quick_game.py`

```python
#!/usr/bin/env python3
import requests

BASE_URL = "http://localhost:8001"
API_KEY = "your-api-key-here"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def game_cmd(command, role="player"):
    """Execute game command."""
    response = requests.post(
        f"{BASE_URL}/game/command",
        headers=HEADERS,
        json={
            "command": command,
            "experience": "wylding-woods",
            "user_context": {
                "role": role,
                "user_id": f"{role}@test.com"
            }
        },
        timeout=30
    )
    result = response.json()
    print(f"\n{result.get('narrative', result)}\n")
    return result

# Test player command
game_cmd("look around", role="player")

# Test admin command
game_cmd("@stats", role="admin")
```

### Key Request Structure

```json
{
  "command": "look around" or "@list waypoints",
  "experience": "wylding-woods",
  "user_context": {
    "role": "admin" or "player",
    "user_id": "your-user-id"
  }
}
```

**Critical**:
- `role: "admin"` - Required for @ commands
- `role: "player"` - For natural language commands
- `experience` - Determines which KB content is loaded

---

## Complete Command Reference

### Admin Commands (23 commands)

**Read Operations:**
```bash
@stats                                          # World statistics
@list waypoints                                 # All waypoints
@list locations <waypoint>                      # Locations in waypoint
@list sublocations <waypoint> <location>        # Sublocations (shows graph)
@list items                                     # All items
@list items at <waypoint> <location> <subloc>   # Items at location
@list templates [type]                          # Templates (all/items/npcs)
@inspect waypoint <id>                          # Detailed waypoint info
@inspect location <waypoint> <id>               # Detailed location info
@inspect sublocation <waypoint> <location> <id> # Sublocation + graph
@inspect item <instance_id>                     # Item instance details
```

**Create Operations:**
```bash
@create waypoint <id> <name>
@create location <waypoint> <id> <name>
@create sublocation <waypoint> <location> <id> <name>
@connect <waypoint> <location> <from> <to> [direction]  # Bidirectional
@disconnect <waypoint> <location> <from> <to>           # Remove connection
```

**Update Operations:**
```bash
@edit waypoint <id> name <value>
@edit waypoint <id> description <text>
@edit location <waypoint> <id> name <value>
@edit location <waypoint> <id> description <text>
@edit location <waypoint> <id> default_sublocation <id>
@edit sublocation <waypoint> <location> <id> name <value>
@edit sublocation <waypoint> <location> <id> description <text>
@edit sublocation <waypoint> <location> <id> interactable <true|false>
```

**Delete Operations (require CONFIRM):**
```bash
@delete waypoint <id> CONFIRM
@delete location <waypoint> <id> CONFIRM
@delete sublocation <waypoint> <location> <id> CONFIRM
```

**Search Operations:**
```bash
@where <id_or_name>        # Find item/NPC by ID or name
@find <template_name>      # Find all instances of template
```

**Reset Operations (require CONFIRM):**
```bash
@reset instance <instance_id> CONFIRM    # Reset single item to uncollected
@reset player <user_id> CONFIRM          # Clear player progress
@reset experience CONFIRM                 # Reset entire experience (nuclear)
```

### Player Commands (Natural Language)

**Navigation:**
- "go north" / "move north"
- "go to <sublocation>"
- "enter <location>"
- "leave" / "exit"
- "back"

**Observation:**
- "look" / "look around"
- "examine <target>"
- "where am I?"
- "exits"

**Interaction:**
- "take <item>"
- "drop <item>"
- "give <item> to <target>"
- "use <item>"
- "inventory"

**Social:**
- "talk to <npc>"
- "ask <npc> about <topic>"

---

## File Structure & Data Location

### KB Structure

```
kb/experiences/wylding-woods/
├── world/
│   ├── locations.json          # Waypoints/locations/sublocations + graph
│   └── manifest.json           # Instance registry
│
├── templates/                  # Design-time definitions (markdown)
│   ├── items/
│   │   ├── dream_bottle.md
│   │   └── ...
│   └── npcs/
│       ├── louisa.md
│       └── ...
│
├── instances/                  # Runtime state (JSON)
│   ├── items/
│   │   ├── dream_bottle_1.json
│   │   ├── dream_bottle_2.json
│   │   └── ...
│   └── npcs/
│       └── louisa_1.json
│
└── players/                    # Per-user state
    └── {user_id}/
        ├── progress.json       # Quest state
        └── inventory.json      # Items collected
```

### Key Files

**`world/locations.json`** - Complete world structure:
```json
{
  "waypoint_28a": {
    "waypoint_id": "waypoint_28a",
    "name": "Woander Store Area",
    "locations": {
      "clearing": {
        "location_id": "clearing",
        "name": "Forest Clearing",
        "sublocations": {
          "center": {
            "sublocation_id": "center",
            "name": "Center of Clearing",
            "exits": ["shelf_1", "shelf_2"],      // ← Graph structure
            "cardinal_exits": {                    // ← Optional shortcuts
              "north": "shelf_1"
            }
          }
        }
      }
    }
  }
}
```

**`instances/manifest.json`** - Instance registry:
```json
{
  "instances": [
    {
      "instance_id": 1,
      "template_name": "dream_bottle",
      "semantic_name": "dream_bottle",
      "location": "waypoint_28a/clearing/shelf_1",
      "collected_by": null,
      "_version": 1
    }
  ]
}
```

---

## Common Workflows

### Workflow 1: Test Player Experience

```bash
# 1. Start interactive client
python scripts/gaia_client.py --env local

# 2. Natural language commands
You: look around
You: take the dream bottle
You: go to the fairy door
You: give bottle to fairy door

# Watch for:
# - Narrative quality
# - State changes
# - Quest progress
```

### Workflow 2: Build New Area (Admin)

```bash
# Via CLI
python scripts/gaia_client.py --env local

You: @create waypoint forest_shrine Forest Shrine
You: @create location forest_shrine entrance Shrine Entrance
You: @create sublocation forest_shrine entrance gate Front Gate
You: @create sublocation forest_shrine entrance courtyard Courtyard
You: @connect forest_shrine entrance gate courtyard south
You: @inspect waypoint forest_shrine
```

### Workflow 3: Debug World Structure

```bash
# Quick Python script
python3 << 'EOF'
import requests
import json

def cmd(c):
    r = requests.post("http://localhost:8001/game/command",
        headers={"X-API-Key": "your-key", "Content-Type": "application/json"},
        json={"command": c, "experience": "wylding-woods",
              "user_context": {"role": "admin", "user_id": "debug@test.com"}},
        timeout=30
    )
    print(r.json().get("narrative", r.json()))

cmd("@stats")
cmd("@list waypoints")
cmd("@inspect waypoint waypoint_28a")
cmd("@where louisa")
EOF
```

### Workflow 4: Automated Testing

**File**: `tests/game/test_world_integrity.py`

```python
#!/usr/bin/env python3
"""Test world structure integrity."""
import requests

BASE_URL = "http://localhost:8001"
API_KEY = "test-api-key"

def admin_cmd(command):
    """Execute admin command."""
    response = requests.post(
        f"{BASE_URL}/game/command",
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        json={
            "command": command,
            "experience": "wylding-woods",
            "user_context": {"role": "admin", "user_id": "test@admin.com"}
        },
        timeout=30
    )
    return response.json()

def test_waypoints_exist():
    """Verify all waypoints are defined."""
    result = admin_cmd("@list waypoints")
    assert result["success"]
    assert "waypoint_28a" in result["narrative"]

def test_navigation_graph_valid():
    """Verify sublocation connections are bidirectional."""
    result = admin_cmd("@inspect sublocation waypoint_28a clearing center")
    assert result["success"]
    # Check exits array exists
    assert "exits" in result.get("data", {})

# Run tests
test_waypoints_exist()
test_navigation_graph_valid()
print("✅ All tests passed!")
```

---

## Troubleshooting

### Issue: "Admin commands require admin role"

**Cause**: `role` not set to "admin" in `user_context`

**Fix**:
```python
# ❌ Wrong
"user_context": {"user_id": "test@test.com"}

# ✅ Right
"user_context": {"role": "admin", "user_id": "test@test.com"}
```

### Issue: "@command not recognized"

**Cause**: Missing @ prefix or invalid command

**Fix**: All admin commands must start with `@`:
```bash
# ❌ Wrong
stats

# ✅ Right
@stats
```

### Issue: Player commands not working

**Cause**:
1. Wrong endpoint (should be `/game/command`)
2. Experience not loaded
3. KB files missing

**Fix**:
```bash
# Verify KB loaded
ls kb/experiences/wylding-woods/

# Check world structure
python scripts/gaia_client.py --env local --batch "@stats"

# Test with simple command
python scripts/gaia_client.py --env local --batch "look"
```

### Issue: Slow response times

**Player commands**: 1.5-2s is normal (LLM parsing)
**Admin commands**: <30ms expected

**If slower**:
- Check Docker container health: `docker compose ps`
- Verify KB loaded: `docker logs gaia-kb-service`
- Test direct: `curl http://localhost:8001/health`

---

## Best Practices

### When Testing Games

1. **Start with admin commands** - Verify world structure first
   ```bash
   @stats
   @list waypoints
   @inspect waypoint waypoint_28a
   ```

2. **Then test player commands** - Ensure natural language works
   ```bash
   look around
   take bottle
   go north
   ```

3. **Use logging** - Capture conversations for review
   ```bash
   python scripts/gaia_client.py --env local --log --log-name test-session
   ```

4. **Check state changes** - Verify quest progress, inventory updates
   ```python
   result = game_cmd("take bottle")
   assert "inventory" in result.get("state_changes", {})
   ```

### When Building Worlds

1. **Build top-down** - Waypoint → Location → Sublocation
   ```bash
   @create waypoint test_wp Test Waypoint
   @create location test_wp main Main Area
   @create sublocation test_wp main center Center
   ```

2. **Connect navigation** - Build graph connections
   ```bash
   @connect test_wp main center corner south
   ```

3. **Verify structure** - Inspect after each major change
   ```bash
   @inspect waypoint test_wp
   @list sublocations test_wp main
   ```

4. **Use CONFIRM** - Always required for deletions
   ```bash
   @delete sublocation test_wp main old_spot CONFIRM
   ```

### When Debugging

1. **Check logs first**:
   ```bash
   # KB service logs
   docker logs gaia-kb-service | tail -100

   # Chat service logs
   docker logs gaia-chat-service | tail -100
   ```

2. **Test endpoint directly**:
   ```bash
   curl http://localhost:8001/health | jq
   ```

3. **Use @where to find items**:
   ```bash
   @where louisa
   @where item 5
   ```

4. **Reset for clean testing**:
   ```bash
   @reset player test@test.com CONFIRM
   @reset instance 5 CONFIRM
   ```

---

## Quick Reference Card

**Player Testing:**
```bash
# Interactive
python scripts/gaia_client.py --env local

# Batch
python scripts/gaia_client.py --env local --batch "look around"

# With logging
python scripts/gaia_client.py --env local --log
```

**Admin Commands:**
```bash
@stats                               # Overview
@list waypoints                      # List all
@inspect waypoint waypoint_28a       # Details
@create waypoint new_wp New Waypoint # Build
@edit waypoint new_wp name Updated   # Modify
@delete waypoint new_wp CONFIRM      # Remove (careful!)
```

**Direct API:**
```python
requests.post("http://localhost:8001/game/command",
    headers={"X-API-Key": KEY, "Content-Type": "application/json"},
    json={
        "command": "look around" or "@stats",
        "experience": "wylding-woods",
        "user_context": {"role": "admin"|"player", "user_id": "test@test.com"}
    }
)
```

**Essential Files:**
- `scripts/gaia_client.py` - Interactive CLI
- `kb/experiences/wylding-woods/world/locations.json` - World structure
- `kb/experiences/wylding-woods/instances/manifest.json` - Instance registry
- `test_admin_commands.py` - Example admin tests
- `demo_admin_commands.py` - Visual demo

**Documentation:**
- [Admin Commands Quick Start](docs/features/dynamic-experiences/phase-1-mvp/000-admin-commands-quick-start.md)
- [Complete Admin Command System](docs/features/dynamic-experiences/phase-1-mvp/025-complete-admin-command-system.md)
- [Game Command Developer Guide](docs/features/dynamic-experiences/phase-1-mvp/009-game-command-developer-guide.md)
- [KB Command Processing Spec](docs/features/dynamic-experiences/phase-1-mvp/021-kb-command-processing-spec.md)

---

## Summary

You now know how to:
- ✅ Test gameplay as a player using natural language
- ✅ Build worlds as an admin using @ commands
- ✅ Use the GAIA CLI for interactive testing
- ✅ Write Python scripts for automated testing
- ✅ Navigate the KB file structure
- ✅ Debug game systems and world structure

**Key Insight**: There are two interaction modes - player (LLM-driven, narrative) and admin (instant, structured). Use admin commands for rapid world building, player commands for testing experience.
