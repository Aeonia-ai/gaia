# Phase 2: Codebase Structure Analysis

**Analysis Date:** 2025-11-20

---

## Executive Summary

The GAIA platform consists of **6 microservices** with a total of **164 Python files** across 19 directories. The KB (Knowledge Base) service is the largest and most complex, containing the experience/game system. Significant technical debt exists in the form of legacy files, archive directories, and inconsistent organization.

---

## Service Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         GATEWAY                                  │
│                    (API routing, mTLS)                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┬──────────────────┐
        ▼                 ▼                 ▼                  ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│    AUTH       │ │    CHAT       │ │     KB        │ │    ASSET      │
│  (Supabase)   │ │  (LLM/MCP)    │ │  (Experience) │ │  (Media Gen)  │
└───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘
                          │                 │
                          ▼                 ▼
                  ┌───────────────┐ ┌───────────────┐
                  │    WEB        │ │  LOCATIONS    │
                  │  (FastHTML)   │ │  (AR/GPS)     │
                  └───────────────┘ └───────────────┘
```

---

## Services Inventory

### 1. Gateway Service (`app/services/gateway/`)
**Files:** 2 | **Lines:** ~200
**Purpose:** API routing, mTLS termination, request proxying

| File | Purpose |
|------|---------|
| `routes/locations_endpoints.py` | AR waypoint endpoints (should be in Locations service) |

**Tech Debt:** Location endpoints in gateway instead of dedicated service

### 2. Auth Service (`app/services/auth/`)
**Files:** 1 | **Lines:** ~150
**Purpose:** Authentication via Supabase, API key validation

| File | Purpose |
|------|---------|
| `main.py` | Auth endpoints, JWT validation |

**Status:** Clean, minimal - relies on Supabase

### 3. Chat Service (`app/services/chat/`)
**Files:** 27 + archive | **Lines:** 7,852
**Purpose:** LLM interaction, persona management, MCP orchestration

| File | Lines | Purpose |
|------|-------|---------|
| `unified_chat.py` | 2,118 | Main chat routing, persona system |
| `kb_tools.py` | 900 | KB tool definitions for LLM |
| `chat.py` | 721 | Legacy chat endpoint |
| `chat_stream.py` | 543 | Streaming implementation |
| `persona_service_postgres.py` | 486 | Persona CRUD |
| `multiagent_orchestrator.py` | 463 | Multi-agent coordination |

**Tech Debt:**
- `_archive_2025_01/` contains 26 abandoned files (1,000+ lines each)
- `kb_multiagent_orchestrator.py.disabled` - dead code
- Multiple overlapping chat implementations

### 4. KB Service (`app/services/kb/`)
**Files:** 30 | **Lines:** 20,045
**Purpose:** Knowledge base, experience system, game logic

| File | Lines | Purpose |
|------|-------|---------|
| `kb_agent.py` | 3,932 | Main KB agent (TOO LARGE) |
| `game_commands_legacy_hardcoded.py` | 3,326 | LEGACY - should be deleted |
| `unified_state_manager.py` | 1,702 | World state management |
| `kb_mcp_server.py` | 1,013 | MCP server integration |
| `main.py` | 782 | Service router (46 endpoints!) |
| `kb_semantic_search.py` | 753 | Semantic search |
| `websocket_experience.py` | 551 | WebSocket endpoint |
| `experience_endpoints.py` | 506 | Experience API |

**Command Handlers (14 files):**
| Handler | Type | Purpose |
|---------|------|---------|
| `collect_item.py` | Player | Pick up items |
| `drop_item.py` | Player | Drop items |
| `examine.py` | Player | Inspect objects |
| `go.py` | Player | Move between areas |
| `inventory.py` | Player | View inventory |
| `give_item.py` | Player | Give items to NPCs |
| `use_item.py` | Player | Use items |
| `talk.py` | Player | NPC dialogue |
| `accept_quest.py` | Player | Accept quests |
| `admin_command_router.py` | Admin | Route admin commands |
| `admin_examine.py` | Admin | Inspect world state |
| `admin_where.py` | Admin | Find objects |
| `admin_edit_item.py` | Admin | Modify items |
| `admin_reset_experience.py` | Admin | Reset world state |

**Tech Debt:**
- `game_commands_legacy_hardcoded.py` - 3,326 lines of dead code
- `kb_agent.py` at 3,932 lines - needs decomposition
- 46 endpoints in main.py - too many responsibilities

### 5. Asset Service (`app/services/asset/`)
**Files:** 18 | **Lines:** ~3,000
**Purpose:** Media generation (images, audio, 3D models)

**Status:** Self-contained, well-organized with clear client modules

### 6. Web Service (`app/services/web/`)
**Files:** 16 | **Lines:** ~2,000
**Purpose:** FastHTML web interface

**Status:** Well-organized with components/, routes/, utils/ structure

### 7. Locations Service (`app/services/locations/`)
**Files:** 5 | **Lines:** ~300
**Purpose:** AR waypoint processing, GPS utilities

| File | Purpose |
|------|---------|
| `distance_utils.py` | Haversine distance calculation |
| `location_finder.py` | GPS-based filtering |
| `waypoint_reader.py` | Read waypoints from KB |
| `waypoint_transformer.py` | Transform to Unity format |

**Note:** Endpoints for this service are in Gateway - should be consolidated

---

## Shared Modules (`app/shared/`)

**Files:** 26 | **Lines:** ~2,500

| Module | Purpose | Used By |
|--------|---------|---------|
| `config.py` | Service configuration, env vars | All |
| `database.py` | PostgreSQL connection | Chat, KB, Web |
| `nats_client.py` | NATS messaging | Gateway, KB |
| `redis_client.py` | Redis caching | All |
| `supabase_auth.py` | Supabase integration | Auth, Gateway |
| `jwt_service.py` | JWT creation/validation | Auth, Gateway |
| `security.py` | API key validation | All |
| `rbac.py` / `rbac_simple.py` / `rbac_fixed.py` | RBAC (3 versions!) | KB |
| `models/command_result.py` | Command response model | KB handlers |
| `models/persona.py` | Persona data model | Chat |

**Tech Debt:**
- 3 RBAC implementations (`rbac.py`, `rbac_simple.py`, `rbac_fixed.py`)
- `database_compat.py` - compatibility shim (dead code?)

---

## API Surface Analysis

### Total Endpoints: ~80+

**By Service:**
| Service | Endpoints | Notes |
|---------|-----------|-------|
| KB | 46 | Too many - needs grouping |
| Chat | 12 | Reasonable |
| Gateway | 8 | Includes location endpoints |
| Auth | 5 | Minimal |
| Asset | 15 | Well-organized |
| Web | 10+ | HTML routes |

### KB Service Endpoint Categories (46 total)

```
Agent Endpoints (5)
├── POST /interpret
├── POST /workflow
├── POST /validate
├── GET /status
└── POST /cache/clear

Experience Endpoints (8)
├── POST /experience/interact
├── GET /experience/list
├── GET /experience/info/{id}
├── POST /experience/{id}/quest/state
├── POST /experience/{id}/npc/accept_item
├── POST /experience/{id}/quest/reward
├── GET /experience/{id}/player/inventory
└── WebSocket /ws/experience

Game Commands (3)
├── POST /game/command
├── POST /game/test/simple-command
└── GET /game/experiences

KB Storage/RBAC (5)
├── GET /search
├── GET /document/{path}
├── POST /share
├── POST /workspace
└── POST /team

Core KB (10+)
├── POST /trigger-clone
├── POST /search
├── POST /context
├── POST /multitask
├── POST /navigate
├── POST /synthesize
├── POST /threads
├── POST /read
├── POST /list
└── POST /search/semantic

Semantic Search (4)
├── POST /semantic/index
├── GET /semantic/stats
├── POST /semantic/search
└── DELETE /semantic/clear
```

---

## Experience/KB Content Structure

```
experiences/
├── wylding-woods/          # Primary demo experience
│   ├── config.json         # Experience configuration
│   ├── +game.md           # Experience metadata
│   ├── world.json         # Current world state (runtime)
│   ├── template.json      # World template (for resets)
│   ├── players/           # Player state files
│   ├── characters/        # NPC definitions
│   │   └── louisa.md
│   ├── game-logic/        # Command implementations
│   │   ├── actions/
│   │   ├── admin-logic/
│   │   └── prompts/
│   ├── items/             # Item templates
│   ├── narrative/         # Story content
│   └── waypoints/         # AR waypoint definitions
│
├── west-of-house/         # Text adventure
├── rock-paper-scissors/   # Simple game
├── mission-unpossible/    # AR mission
└── sanctuary/             # Future experience
```

---

## Key Architectural Patterns

### 1. Command Pattern (Experience System)
```python
# Handler interface
async def handle_command(user_id, experience_id, command_data, connection_id) -> CommandResult

# Registration in command_processor.py
handlers = {
    "collect": handle_collect_item,
    "drop": handle_drop_item,
    # ...
}
```

### 2. State Management (World State)
```python
# unified_state_manager.py
class UnifiedStateManager:
    async def get_world_state(experience) -> dict
    async def update_world_state(experience, updates, user_id, connection_id) -> dict
    async def build_aoi(experience, user_id, zone) -> dict  # Area of Interest
```

### 3. Real-Time Updates (NATS)
```python
# World update flow
update_world_state() → _publish_world_update() → NATS → WebSocket → Unity
```

### 4. Persona-Based Tool Filtering (Chat)
```python
# unified_chat.py
def _get_kb_tools_for_persona(persona_name):
    if persona_name == "louisa":
        return NPC_TOOLS  # Game tools only
    elif persona_name == "game master":
        return EXPERIENCE_TOOLS + KB_SEARCH_TOOLS
    else:
        return GENERAL_KB_TOOLS
```

---

## Complexity Hotspots

| File | Lines | Issues |
|------|-------|--------|
| `kb_agent.py` | 3,932 | Too large, needs decomposition |
| `game_commands_legacy_hardcoded.py` | 3,326 | Dead code, should delete |
| `unified_chat.py` | 2,118 | Many responsibilities |
| `unified_state_manager.py` | 1,702 | Complex but necessary |
| `kb/main.py` | 782 | 46 endpoints, needs grouping |

---

## Recommendations

### High Priority
1. **Delete `game_commands_legacy_hardcoded.py`** - 3,326 lines of dead code
2. **Decompose `kb_agent.py`** - Extract agent types into separate files
3. **Group KB endpoints** - Create sub-routers by domain

### Medium Priority
4. **Consolidate RBAC** - Pick one implementation, delete others
5. **Move location endpoints** - From gateway to locations service
6. **Archive chat experiments** - Move `_archive_2025_01/` out of codebase

### Low Priority
7. **Standardize handler patterns** - Create base class for handlers
8. **Document API surface** - OpenAPI spec generation
9. **Create service boundary diagram** - For onboarding

---

## Next: Phase 3 - Technical Debt Audit

Will search for:
- TODO/FIXME/KLUDGE markers
- Hardcoded values
- Duplicated logic
- Commented code blocks
