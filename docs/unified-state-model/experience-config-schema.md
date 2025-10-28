# Experience Config Schema

**Version:** 1.0.0
**Last Updated:** 2025-10-27

## Overview

Every experience in the GAIA Knowledge Base must have a `config.json` file at `/experiences/{experience-id}/config.json`. This configuration defines how the experience manages state, handles multiplayer interactions, and bootstraps new players.

## Core Philosophy: Players as Views

The unified state model treats **world state as the source of truth** and **players as views into that world**. The config file determines whether the world state is:

- **Shared** (multiplayer): One world file, all players interact with same entities
- **Isolated** (single-player): Each player gets their own copy of the world

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "name", "version", "state"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z0-9-]+$",
      "description": "Unique experience identifier (kebab-case)"
    },
    "name": {
      "type": "string",
      "description": "Human-readable experience name"
    },
    "version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$",
      "description": "Semantic version (major.minor.patch)"
    },
    "description": {
      "type": "string",
      "description": "Brief description of the experience"
    },
    "state": {
      "type": "object",
      "required": ["model"],
      "properties": {
        "model": {
          "type": "string",
          "enum": ["shared", "isolated"],
          "description": "State model: shared (multiplayer) or isolated (single-player)"
        },
        "coordination": {
          "type": "object",
          "properties": {
            "locking_enabled": {
              "type": "boolean",
              "default": true,
              "description": "Enable file locking for concurrent writes (required for shared model)"
            },
            "lock_timeout_ms": {
              "type": "integer",
              "default": 5000,
              "description": "Maximum time to wait for lock acquisition"
            },
            "optimistic_versioning": {
              "type": "boolean",
              "default": true,
              "description": "Use version numbers to detect concurrent modifications"
            }
          }
        },
        "persistence": {
          "type": "object",
          "properties": {
            "auto_save": {
              "type": "boolean",
              "default": true,
              "description": "Automatically save state after changes"
            },
            "save_interval_s": {
              "type": "integer",
              "default": 30,
              "description": "Interval between auto-saves (if enabled)"
            },
            "backup_enabled": {
              "type": "boolean",
              "default": false,
              "description": "Create timestamped backups of state files"
            }
          }
        }
      }
    },
    "multiplayer": {
      "type": "object",
      "properties": {
        "enabled": {
          "type": "boolean",
          "default": false,
          "description": "Whether multiple players can interact simultaneously"
        },
        "max_concurrent_players": {
          "type": ["integer", "null"],
          "default": null,
          "description": "Maximum concurrent players (null = unlimited)"
        },
        "player_visibility": {
          "type": "string",
          "enum": ["global", "location", "none"],
          "default": "location",
          "description": "How players see other players (global = everywhere, location = same location only, none = invisible)"
        },
        "shared_entities": {
          "type": "boolean",
          "default": true,
          "description": "Whether entities (NPCs, items) are shared across players"
        },
        "entity_ownership": {
          "type": "string",
          "enum": ["first_interaction", "permanent", "temporary"],
          "default": "first_interaction",
          "description": "How entity ownership is determined"
        }
      }
    },
    "bootstrap": {
      "type": "object",
      "properties": {
        "player_starting_location": {
          "type": ["string", "null"],
          "default": null,
          "description": "Default starting location (null = ask player)"
        },
        "player_starting_inventory": {
          "type": "array",
          "items": {"type": "string"},
          "default": [],
          "description": "Entity IDs to place in player's starting inventory"
        },
        "initialize_world_on_first_player": {
          "type": "boolean",
          "default": false,
          "description": "Create world.json when first player joins (vs requiring pre-existing file)"
        },
        "copy_template_for_isolated": {
          "type": "boolean",
          "default": true,
          "description": "Copy world template to player's view for isolated model"
        },
        "world_template_path": {
          "type": "string",
          "default": "state/world.json",
          "description": "Path to world state template relative to experience root"
        }
      }
    },
    "content": {
      "type": "object",
      "properties": {
        "templates_path": {
          "type": "string",
          "default": "templates/",
          "description": "Path to entity templates directory"
        },
        "state_path": {
          "type": "string",
          "default": "state/",
          "description": "Path to state files directory"
        },
        "game_logic_path": {
          "type": "string",
          "default": "game-logic/",
          "description": "Path to markdown game logic files"
        },
        "markdown_enabled": {
          "type": "boolean",
          "default": true,
          "description": "Enable markdown-driven game logic"
        },
        "hierarchical_loading": {
          "type": "boolean",
          "default": true,
          "description": "Load content hierarchically (like /agent/interpret)"
        }
      }
    },
    "capabilities": {
      "type": "object",
      "description": "Feature flags for experience capabilities",
      "properties": {
        "gps_based": {
          "type": "boolean",
          "default": false,
          "description": "Requires GPS location data"
        },
        "ar_enabled": {
          "type": "boolean",
          "default": false,
          "description": "Supports AR rendering"
        },
        "voice_enabled": {
          "type": "boolean",
          "default": false,
          "description": "Supports voice commands"
        },
        "inventory_system": {
          "type": "boolean",
          "default": true,
          "description": "Has player inventory system"
        },
        "quest_system": {
          "type": "boolean",
          "default": false,
          "description": "Has quest/mission system"
        },
        "combat_system": {
          "type": "boolean",
          "default": false,
          "description": "Has combat mechanics"
        }
      }
    }
  }
}
```

## Field Descriptions

### Core Fields

#### `id` (required)
- **Type:** string
- **Pattern:** `^[a-z0-9-]+$` (lowercase, numbers, hyphens only)
- **Description:** Unique identifier for this experience. Must match the directory name in `/experiences/{id}/`.
- **Examples:** `"wylding-woods"`, `"west-of-house"`, `"rock-paper-scissors"`

#### `name` (required)
- **Type:** string
- **Description:** Human-readable display name for the experience
- **Examples:** `"The Wylding Woods"`, `"West of House"`, `"Rock Paper Scissors"`

#### `version` (required)
- **Type:** string
- **Pattern:** Semantic versioning `major.minor.patch`
- **Description:** Version number for tracking experience updates
- **Examples:** `"1.0.0"`, `"2.1.3"`

#### `description` (optional)
- **Type:** string
- **Description:** Brief description shown to players when selecting experience
- **Example:** `"AR fairy tale adventure in real-world locations"`

### State Configuration (`state`)

#### `state.model` (required)
- **Type:** enum `["shared", "isolated"]`
- **Description:** Determines how world state is managed
  - **`shared`**: One world.json file, all players interact with same world state (multiplayer)
  - **`isolated`**: Each player gets their own copy of world.json (single-player)
- **When to use shared:** Multiplayer games where players affect each other's world
- **When to use isolated:** Single-player adventures where each player has independent reality

#### `state.coordination.locking_enabled`
- **Type:** boolean
- **Default:** `true`
- **Description:** Enable file locking to prevent concurrent write conflicts
- **Required for:** `state.model: "shared"`
- **Can disable for:** `state.model: "isolated"` (no concurrent access to same file)

#### `state.coordination.lock_timeout_ms`
- **Type:** integer
- **Default:** `5000` (5 seconds)
- **Description:** Maximum milliseconds to wait when acquiring file lock
- **Use cases:**
  - Lower values (1000-2000ms): Fast-paced games, fail fast on conflicts
  - Higher values (5000-10000ms): Complex operations, more tolerance for waiting

#### `state.coordination.optimistic_versioning`
- **Type:** boolean
- **Default:** `true`
- **Description:** Use version numbers in state files to detect concurrent modifications
- **How it works:**
  1. Read world state with version=5
  2. Make changes locally
  3. Write with version=6 only if current version still 5
  4. If current version > 5, conflict detected → retry or merge

#### `state.persistence.auto_save`
- **Type:** boolean
- **Default:** `true`
- **Description:** Automatically persist state changes to disk
- **If false:** Must call save() explicitly (useful for transactional operations)

#### `state.persistence.save_interval_s`
- **Type:** integer
- **Default:** `30` seconds
- **Description:** Minimum interval between automatic saves
- **Purpose:** Rate limit disk writes for high-frequency updates

#### `state.persistence.backup_enabled`
- **Type:** boolean
- **Default:** `false`
- **Description:** Create timestamped backup copies before overwriting state files
- **Backup location:** `state/backups/{timestamp}-world.json`
- **Use case:** Critical experiences where state corruption would be catastrophic

### Multiplayer Configuration (`multiplayer`)

#### `multiplayer.enabled`
- **Type:** boolean
- **Default:** `false`
- **Description:** Whether multiple players can interact simultaneously
- **Note:** Can be `true` even with `state.model: "isolated"` (shared chat, isolated worlds)

#### `multiplayer.max_concurrent_players`
- **Type:** integer or null
- **Default:** `null` (unlimited)
- **Description:** Maximum number of players allowed in experience at once
- **Use cases:**
  - `null`: Open world, no limit
  - `1`: Single-player only
  - `2-10`: Small group experiences
  - `100+`: Massive multiplayer

#### `multiplayer.player_visibility`
- **Type:** enum `["global", "location", "none"]`
- **Default:** `"location"`
- **Description:** How players see other players
  - **`global`**: Players see all other players everywhere (lobby-style)
  - **`location`**: Players only see others in same waypoint/room (proximity-based)
  - **`none`**: Players are invisible to each other (independent instances)

#### `multiplayer.shared_entities`
- **Type:** boolean
- **Default:** `true`
- **Description:** Whether entities (NPCs, items) are shared across players
- **Examples:**
  - `true`: If player A takes dream bottle, player B can't take it
  - `false`: Each player sees their own instances of entities

#### `multiplayer.entity_ownership`
- **Type:** enum `["first_interaction", "permanent", "temporary"]`
- **Default:** `"first_interaction"`
- **Description:** How entity ownership is determined
  - **`first_interaction`**: First player to interact "owns" entity for that session
  - **`permanent`**: Entity ownership persists across sessions
  - **`temporary`**: Entity ownership expires after N minutes of inactivity

### Bootstrap Configuration (`bootstrap`)

#### `bootstrap.player_starting_location`
- **Type:** string or null
- **Default:** `null`
- **Description:** Default location for new players
  - **`null`**: Ask player to choose starting location
  - **`"waypoint_id"`**: Always start at specified location
- **Examples:** `null`, `"waypoint_28a"`, `"west_of_house"`

#### `bootstrap.player_starting_inventory`
- **Type:** array of strings
- **Default:** `[]`
- **Description:** Entity IDs to place in player's inventory at start
- **Example:** `["compass_1", "map_1"]` (player starts with compass and map)

#### `bootstrap.initialize_world_on_first_player`
- **Type:** boolean
- **Default:** `false`
- **Description:** Auto-create world.json when first player joins
- **Use cases:**
  - `false`: world.json must be pre-created by experience designer
  - `true`: System creates world.json from templates on demand

#### `bootstrap.copy_template_for_isolated`
- **Type:** boolean
- **Default:** `true`
- **Description:** For `state.model: "isolated"`, copy world template to player's view
- **If false:** Create minimal player view, reference shared world template (hybrid approach)

#### `bootstrap.world_template_path`
- **Type:** string
- **Default:** `"state/world.json"`
- **Description:** Path to world state template file relative to experience root
- **Used by:** Isolated model (copies this file), shared model (validates existence)

### Content Configuration (`content`)

#### `content.templates_path`
- **Type:** string
- **Default:** `"templates/"`
- **Description:** Directory containing entity templates (npcs/, items/, etc.)

#### `content.state_path`
- **Type:** string
- **Default:** `"state/"`
- **Description:** Directory containing state files (world.json, etc.)

#### `content.game_logic_path`
- **Type:** string
- **Default:** `"game-logic/"`
- **Description:** Directory containing markdown files with game command logic

#### `content.markdown_enabled`
- **Type:** boolean
- **Default:** `true`
- **Description:** Enable markdown-driven game logic (vs hardcoded Python)

#### `content.hierarchical_loading`
- **Type:** boolean
- **Default:** `true`
- **Description:** Load content hierarchically like `/agent/interpret` endpoint
- **How it works:** Search parent directories for context markdown files

### Capabilities (`capabilities`)

Feature flags indicating what the experience supports. Used by clients to enable/disable UI features.

#### `capabilities.gps_based`
- **Type:** boolean
- **Default:** `false`
- **Description:** Experience requires GPS location data
- **Examples:** Wylding Woods (true), West of House (false)

#### `capabilities.ar_enabled`
- **Type:** boolean
- **Default:** `false`
- **Description:** Experience supports AR rendering
- **Client behavior:** Show AR camera view if true

#### `capabilities.voice_enabled`
- **Type:** boolean
- **Default:** `false`
- **Description:** Experience accepts voice commands
- **Client behavior:** Show microphone button if true

#### `capabilities.inventory_system`
- **Type:** boolean
- **Default:** `true`
- **Description:** Experience has player inventory system
- **Client behavior:** Show inventory UI if true

#### `capabilities.quest_system`
- **Type:** boolean
- **Default:** `false`
- **Description:** Experience has quests/missions system
- **Client behavior:** Show quest log UI if true

#### `capabilities.combat_system`
- **Type:** boolean
- **Default:** `false`
- **Description:** Experience has combat mechanics
- **Client behavior:** Show health bar, combat UI if true

## Validation Rules

The system must validate config files on experience load:

### Required Field Validation
- `id`, `name`, `version`, `state.model` must be present
- `id` must match directory name
- `version` must be valid semver

### Consistency Validation
- If `state.model == "shared"` and `multiplayer.enabled == true`:
  - `state.coordination.locking_enabled` must be `true`
- If `state.model == "isolated"`:
  - `multiplayer.shared_entities` should be `false` (warning, not error)
- If `bootstrap.copy_template_for_isolated == true`:
  - File at `bootstrap.world_template_path` must exist

### Path Validation
- All path fields (`content.templates_path`, etc.) must:
  - Be relative paths (no leading `/`)
  - Point to directories that exist
  - Not contain `..` (no parent directory traversal)

### Performance Validation
- If `state.persistence.save_interval_s < 5`:
  - Warning: High-frequency saves may impact performance
- If `state.coordination.lock_timeout_ms > 30000`:
  - Warning: Long timeout may cause poor UX

## Example: Validation Error Messages

```
ERROR: Invalid config for experience 'wylding-woods'
- Missing required field: state.model
- Invalid version format: "1.0" (must be "major.minor.patch")
- Path not found: templates/ (specified in content.templates_path)

WARNING: Potential issues with experience 'wylding-woods'
- state.model is "shared" but multiplayer.enabled is false (unusual configuration)
- save_interval_s is 2 seconds (may impact performance)
```

## Config Loading Process

1. **Read config.json** from `/experiences/{experience-id}/config.json`
2. **Parse JSON** and validate syntax
3. **Apply defaults** for optional fields
4. **Validate schema** against JSON schema definition
5. **Run consistency checks** (cross-field validation)
6. **Verify paths** exist and are accessible
7. **Cache config** in memory with experience metadata
8. **Log warnings** for potential issues (don't fail)

## Related Documentation

- [Config Examples](config-examples.md) - Complete examples for different experience types
- [Unified State Model Overview](unified-state-model-overview.md) - Architecture overview
- [Migration Guide](migration-guide.md) - Converting existing experiences to unified model
