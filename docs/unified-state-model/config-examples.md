# Experience Config Examples

**Version:** 1.0.0
**Last Updated:** 2025-10-27

This document provides complete, production-ready config examples for different experience types, along with migration guidance from the current structure.

## Table of Contents

1. [Shared Multiplayer: Wylding Woods](#shared-multiplayer-wylding-woods)
2. [Isolated Single-Player: West of House](#isolated-single-player-west-of-house)
3. [Simple Mini-Game: Rock Paper Scissors](#simple-mini-game-rock-paper-scissors)
4. [Migration Guide](#migration-guide)
5. [Decision Matrix](#decision-matrix)

---

## Shared Multiplayer: Wylding Woods

### Use Case
AR fairy tale adventure where multiple players explore real-world locations simultaneously. Players interact with shared NPCs and items - if one player takes a dream bottle, other players see it's gone.

### config.json

```json
{
  "id": "wylding-woods",
  "name": "The Wylding Woods",
  "version": "1.0.0",
  "description": "AR fairy tale adventure with shared world state and GPS-based waypoints",

  "state": {
    "model": "shared",
    "coordination": {
      "locking_enabled": true,
      "lock_timeout_ms": 5000,
      "optimistic_versioning": true
    },
    "persistence": {
      "auto_save": true,
      "save_interval_s": 30,
      "backup_enabled": false
    }
  },

  "multiplayer": {
    "enabled": true,
    "max_concurrent_players": null,
    "player_visibility": "location",
    "shared_entities": true,
    "entity_ownership": "first_interaction"
  },

  "bootstrap": {
    "player_starting_location": null,
    "player_starting_inventory": [],
    "initialize_world_on_first_player": false,
    "copy_template_for_isolated": false,
    "world_template_path": "state/world.json"
  },

  "content": {
    "templates_path": "templates/",
    "state_path": "state/",
    "game_logic_path": "game-logic/",
    "markdown_enabled": true,
    "hierarchical_loading": true
  },

  "capabilities": {
    "gps_based": true,
    "ar_enabled": true,
    "voice_enabled": false,
    "inventory_system": true,
    "quest_system": true,
    "combat_system": false
  }
}
```

### Directory Structure

```
/experiences/wylding-woods/
├── config.json                    # ← New unified config
├── state/
│   └── world.json                 # ← Unified world state (all entities)
├── templates/
│   ├── npcs/
│   │   └── louisa.md             # Entity blueprints
│   └── items/
│       └── dream_bottle.md
├── game-logic/
│   ├── look.md                    # Markdown command handlers
│   ├── talk.md
│   └── collect.md
└── waypoints/
    ├── waypoint_28a.md            # GPS waypoint definitions
    └── ...
```

### state/world.json Structure

```json
{
  "version": 1,
  "last_modified": "2025-10-27T18:00:00Z",

  "entities": {
    "louisa_1": {
      "template": "louisa",
      "type": "npc",
      "location": "waypoint_28a",
      "sublocation": "fairy_door_1",
      "state": {
        "emotional_state": "anxious",
        "bottles_returned": 2,
        "quest_given": true,
        "conversation_topics": ["missing_dreams", "dream_bottles", "gratitude"]
      }
    },
    "dream_bottle_1": {
      "template": "dream_bottle",
      "type": "item",
      "location": "waypoint_28a",
      "sublocation": "shelf_1",
      "state": {
        "collected": true,
        "collected_by": "jason@aeonia.ai",
        "collected_at": "2025-10-27T17:31:11Z"
      }
    },
    "dream_bottle_2": {
      "template": "dream_bottle",
      "type": "item",
      "location": "waypoint_28a",
      "sublocation": "shelf_2",
      "state": {
        "collected": false
      }
    }
  },

  "world_flags": {
    "quest_phase": "collection",
    "total_bottles": 4,
    "bottles_collected": 2
  },

  "locations": {
    "waypoint_28a": {
      "active_players": ["jason@aeonia.ai", "alice@example.com"],
      "last_activity": "2025-10-27T18:00:00Z",
      "discovered_by": ["jason@aeonia.ai", "alice@example.com", "bob@example.com"]
    }
  }
}
```

### Player View Structure

```json
// /players/jason@aeonia.ai/wylding-woods/view.json
{
  "player": {
    "current_location": "waypoint_28a",
    "current_sublocation": "fairy_door_1",
    "inventory": ["dream_bottle_1", "dream_bottle_3"],
    "stats": {}
  },

  "progress": {
    "visited_locations": ["waypoint_28a", "waypoint_15b"],
    "discovered_sublocations": ["fairy_door_1", "shelf_1", "shelf_2"],
    "quest_states": {
      "return_bottles": {
        "status": "active",
        "player_bottles_returned": 2,
        "started_at": "2025-10-27T17:00:00Z"
      }
    },
    "achievements": ["first_bottle_found", "met_louisa"],
    "observations": {
      "louisa_emotional_state": "She seemed grateful when I returned the bottles"
    }
  },

  "session": {
    "started_at": "2025-10-27T17:00:00Z",
    "last_active": "2025-10-27T18:00:00Z",
    "turns_taken": 23
  },

  "metadata": {
    "_version": 5
  }
}
```

### Migration Steps

**Current structure:**
```
/experiences/wylding-woods/
├── instances/
│   ├── manifest.json
│   ├── npcs/louisa_1.json
│   └── items/dream_bottle_1.json
└── templates/...

/players/jason@aeonia.ai/wylding-woods/
└── progress.json
```

**Migration:**

1. **Create config.json** (as shown above)

2. **Merge instances into state/world.json:**
   ```bash
   # Run migration script
   python scripts/migrate_wylding_woods_state.py
   ```

   This script:
   - Reads `instances/manifest.json`
   - Loads all instance files from `instances/npcs/` and `instances/items/`
   - Merges into single `state/world.json` with unified schema
   - Preserves all state data (bottles_returned, emotional_state, etc.)

3. **Convert progress.json to view.json:**
   ```bash
   # For each player
   python scripts/migrate_player_progress.py jason@aeonia.ai wylding-woods
   ```

   This script:
   - Reads `/players/{user}/wylding-woods/progress.json`
   - Expands to full view.json schema
   - Adds session tracking, metadata
   - Maintains backward compatibility (inventory, quest_progress)

4. **Verify migration:**
   ```bash
   python scripts/validate_experience_config.py wylding-woods
   ```

---

## Isolated Single-Player: West of House

### Use Case
Classic text adventure where each player has their own independent world. No multiplayer interaction - each player's actions only affect their own game state.

### config.json

```json
{
  "id": "west-of-house",
  "name": "West of House",
  "version": "1.0.0",
  "description": "Classic text adventure in the style of Zork",

  "state": {
    "model": "isolated",
    "coordination": {
      "locking_enabled": false,
      "optimistic_versioning": false
    },
    "persistence": {
      "auto_save": true,
      "save_interval_s": 10,
      "backup_enabled": false
    }
  },

  "multiplayer": {
    "enabled": false,
    "shared_entities": false
  },

  "bootstrap": {
    "player_starting_location": "west_of_house",
    "player_starting_inventory": [],
    "initialize_world_on_first_player": false,
    "copy_template_for_isolated": true,
    "world_template_path": "state/world.json"
  },

  "content": {
    "templates_path": "templates/",
    "state_path": "state/",
    "game_logic_path": "game-logic/",
    "markdown_enabled": true,
    "hierarchical_loading": true
  },

  "capabilities": {
    "gps_based": false,
    "ar_enabled": false,
    "voice_enabled": false,
    "inventory_system": true,
    "quest_system": false,
    "combat_system": true
  }
}
```

### Directory Structure

```
/experiences/west-of-house/
├── config.json                    # ← New unified config
├── state/
│   └── world.json                 # ← Template (copied per player)
├── templates/
│   ├── rooms/
│   │   └── west_of_house.md
│   └── items/
│       └── mailbox.md
└── game-logic/
    ├── look.md
    ├── take.md
    └── open.md
```

### state/world.json (Template)

```json
{
  "session": {
    "id": null,
    "started_at": null,
    "turns_taken": 0,
    "score": 0,
    "rank": "Beginner"
  },

  "player": {
    "current_room": "west_of_house",
    "inventory": [],
    "inventory_capacity": 7,
    "health": 100,
    "alive": true
  },

  "world_state": {
    "mailbox_opened": false,
    "mailbox_contents": ["leaflet"],
    "lamp_lit": false,
    "trap_door_open": false,
    "house_entered": false,
    "window_discovered": false,
    "grue_timer": 0,
    "matches_remaining": 5
  },

  "room_states": {
    "west_of_house": {
      "visited": true,
      "items": ["mailbox"],
      "description_shown": false
    },
    "north_of_house": {
      "visited": false,
      "items": [],
      "description_shown": false
    },
    "forest": {
      "visited": false,
      "items": ["lamp"],
      "description_shown": false
    },
    "cellar": {
      "visited": false,
      "items": ["sword"],
      "description_shown": false,
      "is_dark": true
    }
  },

  "discovered_locations": ["west_of_house"],

  "achievements": {
    "first_item_taken": false,
    "mailbox_opened": false,
    "lamp_found": false,
    "lamp_lit": false,
    "house_entered": false,
    "sword_taken": false,
    "survived_darkness": false
  },

  "command_history": []
}
```

### Player View Structure (After Copy)

```json
// /players/jason@aeonia.ai/west-of-house/view.json
// This is a COPY of world.json, player can modify freely
{
  "session": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "started_at": "2025-10-27T18:00:00Z",
    "turns_taken": 15,
    "score": 25,
    "rank": "Amateur Adventurer"
  },

  "player": {
    "current_room": "forest",
    "inventory": ["leaflet", "lamp"],
    "inventory_capacity": 7,
    "health": 100,
    "alive": true
  },

  "world_state": {
    "mailbox_opened": true,
    "mailbox_contents": [],
    "lamp_lit": false,
    "trap_door_open": false,
    "house_entered": false,
    "window_discovered": false,
    "grue_timer": 0,
    "matches_remaining": 5
  },

  "room_states": {
    "west_of_house": {
      "visited": true,
      "items": [],  // mailbox opened, contents taken
      "description_shown": true
    },
    "forest": {
      "visited": true,
      "items": [],  // lamp taken
      "description_shown": true
    },
    ...
  },

  "discovered_locations": ["west_of_house", "north_of_house", "forest"],

  "achievements": {
    "first_item_taken": true,
    "mailbox_opened": true,
    "lamp_found": true,
    "lamp_lit": false,
    "house_entered": false,
    "sword_taken": false,
    "survived_darkness": false
  },

  "command_history": [
    {"turn": 1, "command": "look", "timestamp": "2025-10-27T18:00:00Z"},
    {"turn": 2, "command": "open mailbox", "timestamp": "2025-10-27T18:00:15Z"},
    ...
  ],

  "metadata": {
    "_version": 15,
    "_copied_from_template": "2025-10-27T18:00:00Z"
  }
}
```

### Migration Steps

**Current structure:**
```
/experiences/west-of-house/
└── state/
    └── session-template.json
```

**Migration:**

1. **Create config.json** (as shown above)

2. **Rename session-template.json:**
   ```bash
   mv state/session-template.json state/world.json
   ```

3. **No player migration needed** - each player starts fresh with copy

4. **Verify:**
   ```bash
   python scripts/validate_experience_config.py west-of-house
   ```

---

## Simple Mini-Game: Rock Paper Scissors

### Use Case
Quick mini-game with minimal state, isolated per player, no multiplayer.

### config.json

```json
{
  "id": "rock-paper-scissors",
  "name": "Rock Paper Scissors",
  "version": "1.0.0",
  "description": "Classic hand game against AI opponent",

  "state": {
    "model": "isolated",
    "coordination": {
      "locking_enabled": false
    },
    "persistence": {
      "auto_save": true,
      "save_interval_s": 60
    }
  },

  "multiplayer": {
    "enabled": false
  },

  "bootstrap": {
    "player_starting_location": "game_arena",
    "copy_template_for_isolated": true,
    "world_template_path": "state/world.json"
  },

  "content": {
    "state_path": "state/",
    "game_logic_path": "game-logic/",
    "markdown_enabled": true,
    "hierarchical_loading": false
  },

  "capabilities": {
    "gps_based": false,
    "ar_enabled": false,
    "voice_enabled": false,
    "inventory_system": false,
    "quest_system": false,
    "combat_system": false
  }
}
```

### state/world.json (Minimal Template)

```json
{
  "game_state": {
    "rounds_played": 0,
    "rounds_won": 0,
    "rounds_lost": 0,
    "rounds_tied": 0,
    "current_streak": 0,
    "best_streak": 0
  },

  "session": {
    "started_at": null,
    "last_played": null
  },

  "history": []
}
```

### Migration Steps

**Current structure:**
```
/experiences/rock-paper-scissors/
└── state/
    └── session-template.json
```

**Migration:**

1. Create config.json
2. Rename session-template.json to world.json
3. Verify config

---

## Migration Guide

### Step-by-Step Migration Process

#### Phase 1: Create Configs (No Breaking Changes)

```bash
# For each experience
cd /experiences/{experience-id}

# 1. Create config.json based on experience type
cp /docs/unified-state-model/config-templates/{type}.json config.json

# 2. Customize config values
vim config.json

# 3. Validate config
python /scripts/validate_experience_config.py {experience-id}
```

#### Phase 2: Migrate State Files (Data Migration)

**For Shared Model (Wylding Woods):**

```bash
# Run automated migration script
python scripts/migrate_experience_state.py wylding-woods \
  --merge-instances \
  --keep-backup

# This creates:
# - state/world.json (merged from instances/)
# - state/backups/instances-backup-{timestamp}.tar.gz
# - Keeps original instances/ directory until verified
```

**For Isolated Model (West of House, Rock Paper Scissors):**

```bash
# Simple rename
cd /experiences/west-of-house/state
mv session-template.json world.json

# Validate
python scripts/validate_experience_config.py west-of-house
```

#### Phase 3: Migrate Player Data

```bash
# For shared model experiences only
python scripts/migrate_player_views.py wylding-woods \
  --all-players \
  --keep-backup

# This converts progress.json → view.json for all players
```

#### Phase 4: Update Code References

```bash
# Update KB service to use UnifiedStateManager
# Update game command endpoints to read config
# Update bootstrap logic to use config-driven approach
```

#### Phase 5: Verify Migration

```bash
# Run integration tests
pytest tests/integration/unified_state_model/ -v

# Verify each experience
for exp in wylding-woods west-of-house rock-paper-scissors; do
  python scripts/test_experience.py $exp --full-test
done
```

#### Phase 6: Cleanup Old Files

```bash
# Once verified working, remove old structure
cd /experiences/wylding-woods
rm -rf instances/  # Merged into state/world.json

# Player progress.json files are kept for backward compat
# (UnifiedStateManager can read both formats)
```

---

## Decision Matrix

Use this table to determine the right config settings for your experience:

| Question | Answer → Config Setting |
|----------|------------------------|
| **Do players interact with same world?** | Yes → `state.model: "shared"` <br> No → `state.model: "isolated"` |
| **Can players see each other?** | Yes → `multiplayer.enabled: true` <br> No → `multiplayer.enabled: false` |
| **If multiplayer, where are players visible?** | Everywhere → `player_visibility: "global"` <br> Same location only → `player_visibility: "location"` <br> Never → `player_visibility: "none"` |
| **Do players affect each other's world?** | Yes → `shared_entities: true` <br> No → `shared_entities: false` |
| **How should items be owned?** | First to grab → `entity_ownership: "first_interaction"` <br> Permanent claim → `entity_ownership: "permanent"` <br> Temporary → `entity_ownership: "temporary"` |
| **Where do players start?** | Fixed location → `player_starting_location: "waypoint_id"` <br> Let them choose → `player_starting_location: null` |
| **Do players need GPS?** | Yes → `capabilities.gps_based: true` |
| **Do players need AR camera?** | Yes → `capabilities.ar_enabled: true` |
| **Does experience have inventory?** | Yes → `capabilities.inventory_system: true` |
| **Does experience have quests?** | Yes → `capabilities.quest_system: true` |
| **Does experience have combat?** | Yes → `capabilities.combat_system: true` |

### Common Patterns

#### Pattern 1: Multiplayer AR Adventure
```json
{
  "state": {"model": "shared"},
  "multiplayer": {
    "enabled": true,
    "player_visibility": "location",
    "shared_entities": true
  },
  "capabilities": {
    "gps_based": true,
    "ar_enabled": true
  }
}
```
**Examples:** Wylding Woods, Pokémon GO-style games

#### Pattern 2: Solo Text Adventure
```json
{
  "state": {"model": "isolated"},
  "multiplayer": {"enabled": false},
  "capabilities": {
    "gps_based": false,
    "ar_enabled": false
  }
}
```
**Examples:** West of House, Zork-style games

#### Pattern 3: Casual Mini-Game
```json
{
  "state": {"model": "isolated"},
  "multiplayer": {"enabled": false},
  "capabilities": {
    "inventory_system": false,
    "quest_system": false
  }
}
```
**Examples:** Rock Paper Scissors, quick games

#### Pattern 4: Shared Puzzle World
```json
{
  "state": {"model": "shared"},
  "multiplayer": {
    "enabled": true,
    "player_visibility": "global",
    "shared_entities": true
  },
  "capabilities": {
    "inventory_system": true,
    "quest_system": true
  }
}
```
**Examples:** Escape room-style experiences, collaborative puzzles

---

## Testing Your Config

### Validation Checklist

- [ ] Config validates against JSON schema
- [ ] Required fields present (`id`, `name`, `version`, `state.model`)
- [ ] All paths exist and are accessible
- [ ] If `state.model == "shared"`, locking is enabled
- [ ] If `multiplayer.enabled == true`, coordination configured
- [ ] Bootstrap settings consistent with state model
- [ ] Capabilities match actual experience features

### Test Commands

```bash
# Validate config syntax and schema
python scripts/validate_experience_config.py {experience-id}

# Test bootstrap process
python scripts/test_experience_bootstrap.py {experience-id} test-user@example.com

# Test state operations
python scripts/test_experience_state.py {experience-id} \
  --test-read \
  --test-write \
  --test-concurrent

# Full integration test
python scripts/test_experience.py {experience-id} --full-test
```

### Common Validation Errors

**Error:** `state.model "shared" requires locking_enabled: true`
```json
// Fix: Enable locking for shared model
"state": {
  "model": "shared",
  "coordination": {
    "locking_enabled": true  // ← Add this
  }
}
```

**Error:** `Path not found: templates/`
```bash
# Fix: Create missing directories
mkdir -p templates/npcs templates/items
```

**Error:** `multiplayer.enabled but state.model is "isolated"`
```json
// Warning (not error): Consider if this is intentional
// Multiplayer chat but isolated world states
```

---

## Next Steps

1. Choose config template for your experience type
2. Customize config values
3. Validate config
4. Migrate state files (if needed)
5. Test bootstrap process
6. Deploy and monitor

For questions or issues, see:
- [Config Schema Reference](experience-config-schema.md)
- [Unified State Model Overview](unified-state-model-overview.md)
- [Migration Troubleshooting](migration-troubleshooting.md)
