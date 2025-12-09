# Instance Management Design

**Status**: Active Design Decision
**Last Updated**: 2025-10-26
**Related**: [Experience Data Models](experience-data-models.md), [Player Progress Storage](player-progress-storage.md)

## Overview

This document defines how MMOIRL game instances are managed, stored, and queried at runtime. It establishes the architectural separation between **templates** (game design, stored in KB) and **instances** (runtime state, stored in PostgreSQL JSONB).

## Core Design Principle

**Templates = What CAN exist (KB files)**
**Instances = What DOES exist (PostgreSQL JSONB)**

```
KB (Git-versioned markdown)           PostgreSQL (Runtime state)
├── templates/npcs/louisa.md    →     instance_id: uuid-1234
├── templates/items/sword.md    →     instance_id: uuid-5678
└── rules/combat-system.md            instance_id: uuid-9abc
```

## Design Decision: Why PostgreSQL JSONB?

### Options Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **KB JSON Files** | Git-versioned, simple | Slow queries (500ms+), no spatial indexing, file locking | ❌ Too slow for runtime |
| **Firebase Firestore** | Real-time sync, flexible | No native geospatial queries, needs Algolia | ❌ Missing core feature |
| **MongoDB** | Flexible schema, good geospatial | Separate infrastructure, not on Supabase | ❌ Unnecessary complexity |
| **PostgreSQL JSONB** | Fast (<100ms), flexible schema, PostGIS, already on Supabase | Requires SQL knowledge | ✅ **Selected** |

### Performance Comparison

```
Query: Find 100-1000 instances within 100m radius

KB Files:           500ms - 2s   (read files, parse JSON, filter in Python)
Firestore:          N/A          (no native geospatial)
MongoDB:            50-200ms     (geospatial index)
PostgreSQL JSONB:   20-100ms     (PostGIS + GIN index)
```

**Winner**: PostgreSQL JSONB with PostGIS for 10-100× performance improvement.

## Schema Design

### Game Instances Table

```sql
CREATE TABLE game_instances (
  instance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experience TEXT NOT NULL,                    -- e.g., "wylding-woods"
  template_id TEXT NOT NULL,                   -- e.g., "npcs/louisa"
  location GEOGRAPHY(POINT),                   -- For PostGIS spatial queries
  data JSONB NOT NULL,                         -- COMPLETELY FLEXIBLE schema
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- GIN index for fast JSONB queries (schema-agnostic, covers ALL fields)
CREATE INDEX idx_instance_data ON game_instances USING GIN (data);

-- Spatial index for "nearby" queries
CREATE INDEX idx_instance_location ON game_instances USING GIST (location);

-- Lookup by template type
CREATE INDEX idx_instance_template ON game_instances (experience, template_id);
```

### Player Progress Table

```sql
CREATE TABLE player_progress (
  user_id TEXT PRIMARY KEY,
  experience TEXT NOT NULL,
  data JSONB NOT NULL,                         -- Flexible player state
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_player_progress_data ON player_progress USING GIN (data);
CREATE INDEX idx_player_experience ON player_progress (experience);
```

## JSONB Flexible Schema Examples

**The `data` JSONB column has NO fixed schema - it evolves with game design:**

```json
// NPC Instance
{
  "semantic_name": "louisa_waypoint28a",
  "dialogue_state": "greeting",
  "trust_level": 0.7,
  "inventory": ["item-uuid-1", "item-uuid-2"],
  "mood": "curious"
}

// Item Instance
{
  "semantic_name": "dream_bottle_bookshelf",
  "collected": false,
  "magic_level": 5,
  "enchantments": ["glowing", "floating"]
}

// Player Progress
{
  "inventory": ["uuid-1", "uuid-2"],
  "current_location": {"waypoint": "waypoint_28a", "lat": 37.905696, "lon": -122.547701},
  "quest_progress": {
    "find_dream_bottle": {"status": "active", "step": 2}
  },
  "npc_relationships": {
    "uuid-louisa": {"trust_level": 0.7, "last_interaction": "2025-10-26T10:30:00Z"}
  }
}
```

**Key Insight**: When game design changes (add `mood` field to NPCs), you just start writing it - no migration needed. GIN index automatically covers new fields.

## GIN Index: How It Works

**GIN (Generalized Inverted Index) decomposes JSONB into key-value pairs:**

```
Row 1: {"template": "npcs/louisa", "mood": "happy"}
Row 2: {"template": "items/sword", "damage": 50}

GIN Index Internal Structure:
template=npcs/louisa  → [row 1]
mood=happy           → [row 1]
template=items/sword → [row 2]
damage=50            → [row 2]
```

**When you add a new field** (e.g., `energy_level` to NPCs):
1. Insert/update row with `{"template": "npcs/louisa", "energy_level": 80}`
2. GIN automatically indexes `energy_level=80 → [row 3]`
3. Query `WHERE data->>'energy_level' > '50'` works immediately

**No schema changes, no reindexing, no migrations required.**

## Query Patterns and Performance

### 1. Direct Lookup (Fastest: <1ms)

```python
# Get specific instance by UUID
instance = await db.fetchrow("""
    SELECT instance_id, data, location
    FROM game_instances
    WHERE instance_id = $1
""", instance_uuid)
```

**Use Case**: Examine item in inventory, NPC dialogue continuation

### 2. Template-Based Queries (GIN Index: 5-20ms)

```python
# Find all merchants in experience
merchants = await db.fetch("""
    SELECT instance_id, data, location
    FROM game_instances
    WHERE experience = $1
      AND template_id LIKE 'npcs/merchant%'
""", experience)
```

**Use Case**: Admin tools, spawn management, analytics

### 3. State-Based Queries (GIN Index: 10-50ms)

```python
# Find uncollected quest items
quest_items = await db.fetch("""
    SELECT instance_id, data, location
    FROM game_instances
    WHERE data->>'experience' = $1
      AND data->>'item_type' = 'quest'
      AND data->>'collected' = 'false'
""", experience)
```

**Use Case**: Quest progress, world state queries

### 4. Spatial Queries (PostGIS: 20-100ms)

```python
# Find all instances within 100m of player
nearby = await db.fetch("""
    SELECT instance_id, data, location,
           ST_Distance(location, $2::geography) as distance
    FROM game_instances
    WHERE experience = $1
      AND ST_DWithin(location, $2::geography, 100)
    ORDER BY distance
    LIMIT 50
""", experience, ST_Point(lon, lat))
```

**Use Case**: AR games, "look around" commands, nearby NPC detection

### 5. Player Inventory (Array Lookup: 5-20ms)

```python
# Load player's collected items
inventory_uuids = player_data['inventory']  # From player_progress table
items = await db.fetch("""
    SELECT instance_id, data
    FROM game_instances
    WHERE instance_id = ANY($1)
""", inventory_uuids)
```

**Use Case**: Inventory display, item examination

## Three-Layer Instance Architecture

### Layer 1: World Instances (Shared State)

**Stored in**: `game_instances` table
**Scope**: Shared across all players
**Examples**: NPC spawn locations, world items, quest triggers

```python
# Spawn Louisa at Waypoint 28a (happens once, all players see her)
await db.execute("""
    INSERT INTO game_instances (instance_id, experience, template_id, location, data)
    VALUES ($1, 'wylding-woods', 'npcs/louisa',
            ST_Point(-122.547701, 37.905696)::geography,
            '{"semantic_name": "louisa_waypoint28a", "dialogue_state": "greeting"}'::jsonb)
""", uuid.uuid4())
```

### Layer 2: Player Progress (Per-Player State)

**Stored in**: `player_progress` table
**Scope**: One record per player per experience
**Examples**: Inventory, quest progress, NPC relationships

```python
# Update player's inventory after collecting item
await db.execute("""
    UPDATE player_progress
    SET data = jsonb_set(
        data,
        '{inventory}',
        data->'inventory' || $2::jsonb
    )
    WHERE user_id = $1 AND experience = 'wylding-woods'
""", user_id, json.dumps([collected_item_uuid]))
```

### Layer 3: Player World View (Computed at Runtime)

**Not stored**, computed from Layer 1 + Layer 2
**Purpose**: Filter world instances based on player state

```python
async def get_player_world_view(user_id: str, experience: str, location: Dict):
    # Load nearby world instances
    world_instances = await db.fetch("""
        SELECT * FROM game_instances
        WHERE experience = $1
          AND ST_DWithin(location, $2::geography, 100)
    """, experience, location)

    # Load player progress
    player_data = await db.fetchrow("""
        SELECT data FROM player_progress
        WHERE user_id = $1 AND experience = $2
    """, user_id, experience)

    # Filter: Remove collected items from world view
    collected = set(player_data['data'].get('inventory', []))
    visible_instances = [
        inst for inst in world_instances
        if inst['instance_id'] not in collected
    ]

    # Augment: Apply NPC relationships
    for inst in visible_instances:
        if inst['template_id'].startswith('npcs/'):
            npc_id = str(inst['instance_id'])
            relationship = player_data['data'].get('npc_relationships', {}).get(npc_id, {})
            inst['data']['player_relationship'] = relationship

    return visible_instances
```

## UUID Management and LLM Integration

### Problem: LLMs Can't Be Trusted with UUIDs

**Anti-Pattern**: LLM generates or references UUIDs directly
```json
// ❌ WRONG: LLM hallucinates UUIDs
{"action": "collect", "instance_id": "550e8400-e29b-41d4-a716-446655440000"}
```

**Solution**: LLM uses semantic names, server resolves to UUIDs

### ID Management Strategy

**1. World Instances: Designer-Generated UUIDs**

Designers create instances with static UUIDs in migration scripts:

```sql
-- migrations/002_spawn_wylding_woods_npcs.sql
INSERT INTO game_instances (instance_id, experience, template_id, location, data) VALUES
  ('550e8400-e29b-41d4-a716-446655440000', 'wylding-woods', 'npcs/louisa',
   ST_Point(-122.547701, 37.905696)::geography,
   '{"semantic_name": "louisa_waypoint28a"}'::jsonb),
  ('7c9e6679-7425-40de-944b-e07fc1f90ae7', 'wylding-woods', 'items/dream-bottle',
   ST_Point(-122.548856, 37.906523)::geography,
   '{"semantic_name": "dream_bottle_bookshelf"}'::jsonb);
```

**2. LLM Returns Semantic Actions**

```python
# LLM prompt includes semantic names
prompt = f"""
Nearby instances:
- louisa (NPC, merchant)
- dream_bottle (item, quest objective)

Player command: "collect the dream bottle"
"""

# LLM returns semantic action (no UUIDs!)
llm_response = {
  "success": true,
  "narrative": "You carefully pick up the glowing dream bottle...",
  "actions": [
    {"action": "collect", "target": "dream_bottle"},  # Semantic name
    {"action": "play_sound", "sound": "item_collect.mp3"}
  ]
}
```

**3. Server Resolves Semantic Names to UUIDs**

```python
async def resolve_action_targets(actions, nearby_instances, player_state):
    """Convert LLM's semantic names to instance UUIDs"""
    for action in actions:
        if action.get("target"):
            # Find instance matching semantic name
            instance = next(
                (inst for inst in nearby_instances
                 if inst['data'].get('semantic_name') == action['target']
                 or inst['template_id'].endswith(action['target'])),
                None
            )
            if instance:
                action['instance_id'] = str(instance['instance_id'])
            else:
                action['error'] = f"Target '{action['target']}' not found nearby"
    return actions
```

**4. Server Generates UUIDs for New Instances**

```python
# When spawning new instances at runtime
import uuid

new_instance_id = str(uuid.uuid4())
await db.execute("""
    INSERT INTO game_instances (instance_id, experience, template_id, location, data)
    VALUES ($1, $2, $3, $4, $5)
""", new_instance_id, experience, template_id, location, data)
```

### UUID Best Practices

✅ **DO**:
- Use `uuid.uuid4()` for server-generated IDs
- Store UUIDs as `UUID` type in PostgreSQL (not `TEXT`)
- Include `semantic_name` in JSONB for debugging
- Let LLM work with template names and semantic names
- Server resolves semantic → UUID before executing actions

❌ **DON'T**:
- Let LLM generate or reference UUIDs directly
- Use semantic names as primary keys
- Rely on LLM to maintain UUID consistency
- Pass raw UUIDs to LLM prompts (use semantic names instead)

## Template Loading and Caching

### Template Loading Architecture

```python
class KBIntelligentAgent:
    def __init__(self):
        self.template_cache: Dict[str, Dict] = {}  # In-memory cache

    async def execute_game_command(self, command, experience, user_context, session_state):
        # 1. Load templates from KB (cached)
        templates = await self._load_templates_cached(experience)

        # 2. Load instances from PostgreSQL
        nearby_instances = await self._load_nearby_instances(experience, location)
        player_state = await self._load_player_state(user_context['user_id'], experience)

        # 3. Build LLM prompt with both
        prompt = self._build_game_command_prompt(
            command=command,
            templates=templates,      # Markdown from KB
            instances=nearby_instances,  # JSONB from PostgreSQL
            player_state=player_state
        )

        # 4. LLM interprets using semantic names
        llm_response = await self.llm_service.chat_completion(...)

        # 5. Server resolves semantic names → UUIDs
        actions = await resolve_action_targets(llm_response['actions'], nearby_instances, player_state)

        # 6. Update game state in PostgreSQL
        await self._update_game_state(actions, user_context['user_id'])

        return llm_response

    async def _load_templates_cached(self, experience: str) -> Dict[str, str]:
        """Load KB templates with in-memory caching"""
        cache_key = f"templates:{experience}"

        # Check cache (5-minute TTL)
        if cache_key in self.template_cache:
            cache_age = time.time() - self.template_cache[cache_key]["timestamp"]
            if cache_age < 300:
                return self.template_cache[cache_key]["data"]

        # Cache miss: Load from KB
        templates = await self._load_context(f"/experiences/{experience}")

        # Cache includes all markdown files with resolved links
        self.template_cache[cache_key] = {
            "data": templates,  # Dict[file_path, markdown_content]
            "timestamp": time.time()
        }

        return templates
```

### Why Cache Templates, Not Instances?

**Templates (KB Files)**:
- ✅ Infrequent changes (weekly releases, not per-command)
- ✅ Same for all players (shared context)
- ✅ Can be loaded once and reused
- ✅ Markdown structure needs to be preserved (links, formatting)

**Instances (PostgreSQL)**:
- ❌ Change every command (player actions, state updates)
- ❌ Player-specific view (filtered by inventory, relationships)
- ❌ Need fresh data for each query (can't cache)
- ❌ Already fast (<100ms with indexes)

**Cache Strategy**:
- **Templates**: 5-minute in-memory cache (simple Dict)
- **Instances**: No caching, direct PostgreSQL queries (already fast)
- **Player State**: Could cache for 30s, but likely not worth complexity

## Integration with Game Command Execution

### Complete Flow

```python
# 1. Player sends command
POST /kb/game_commands
{
  "command": "collect the dream bottle",
  "experience": "wylding-woods",
  "session_state": {
    "location": {"lat": 37.906523, "lon": -122.548856}
  }
}

# 2. KB Agent loads templates (cached) + instances (PostgreSQL)
templates = await load_templates_cached("wylding-woods")
# Returns: Dict of all NPC/item templates from KB markdown

nearby_instances = await db.fetch("""
    SELECT instance_id, template_id, data, location
    FROM game_instances
    WHERE experience = 'wylding-woods'
      AND ST_DWithin(location, ST_Point(-122.548856, 37.906523)::geography, 100)
""")
# Returns: [
#   {instance_id: uuid-1, template_id: "npcs/louisa", data: {...}},
#   {instance_id: uuid-2, template_id: "items/dream-bottle", data: {...}}
# ]

player_state = await db.fetchrow("""
    SELECT data FROM player_progress
    WHERE user_id = 'user123' AND experience = 'wylding-woods'
""")
# Returns: {inventory: [], quest_progress: {...}}

# 3. LLM interprets with semantic names
llm_response = {
  "success": true,
  "narrative": "You pick up the glowing dream bottle...",
  "actions": [
    {"action": "collect", "target": "dream_bottle"},
    {"action": "play_sound", "sound": "collect.mp3"}
  ],
  "state_changes": {
    "inventory": ["dream_bottle"]
  }
}

# 4. Server resolves semantic → UUID
actions = [
  {"action": "collect", "target": "dream_bottle", "instance_id": "uuid-2"},
  {"action": "play_sound", "sound": "collect.mp3"}
]

# 5. Update player state in PostgreSQL
await db.execute("""
    UPDATE player_progress
    SET data = jsonb_set(data, '{inventory}', data->'inventory' || $2::jsonb)
    WHERE user_id = $1 AND experience = 'wylding-woods'
""", user_id, json.dumps(["uuid-2"]))

# 6. Mark item as collected in world state
await db.execute("""
    UPDATE game_instances
    SET data = jsonb_set(data, '{collected}', 'true'::jsonb)
    WHERE instance_id = $1
""", "uuid-2")
```

## Migration Path

### Phase 1: Simple Instance Management (Current)

- ✅ Create `game_instances` and `player_progress` tables
- ✅ Manual instance creation via SQL migrations
- ✅ LLM uses semantic names, server resolves to UUIDs
- ✅ In-memory template caching

### Phase 2: Admin Tools (Future)

- Add `/admin/spawn` endpoint for designers to create instances via API
- Web UI for instance management
- Visual map of spawned instances

### Phase 3: Dynamic Spawning (Future)

- LLM can request new instance spawns (e.g., combat drops loot)
- Server validates and creates instances with generated UUIDs
- Event system for instance lifecycle (spawn, despawn, respawn)

### Phase 4: Multi-Experience Scaling (Future)

- Partition `game_instances` table by experience
- Optimize queries with partial indexes
- Consider read replicas for high-traffic experiences

## Performance Monitoring

### Key Metrics to Track

```python
# Add timing instrumentation
import time

async def execute_game_command(...):
    start = time.time()

    t1 = time.time()
    templates = await load_templates_cached(experience)
    template_load_ms = (time.time() - t1) * 1000

    t2 = time.time()
    instances = await load_nearby_instances(...)
    instance_query_ms = (time.time() - t2) * 1000

    t3 = time.time()
    llm_response = await llm_service.chat_completion(...)
    llm_ms = (time.time() - t3) * 1000

    t4 = time.time()
    await update_game_state(...)
    state_update_ms = (time.time() - t4) * 1000

    total_ms = (time.time() - start) * 1000

    logger.info(f"Command execution breakdown: "
                f"template={template_load_ms:.0f}ms, "
                f"instances={instance_query_ms:.0f}ms, "
                f"llm={llm_ms:.0f}ms, "
                f"update={state_update_ms:.0f}ms, "
                f"total={total_ms:.0f}ms")
```

**Target Performance**:
- Template load (cached): <10ms
- Instance query: <50ms
- LLM inference: 500-2000ms (dominant factor)
- State update: <20ms
- **Total: <2.5s** (dominated by LLM, not data access)

### Query Optimization

```sql
-- Check if indexes are being used
EXPLAIN ANALYZE
SELECT * FROM game_instances
WHERE experience = 'wylding-woods'
  AND ST_DWithin(location, ST_Point(-122.547701, 37.905696)::geography, 100);

-- Should show:
-- Index Scan using idx_instance_location on game_instances
-- (NOT Seq Scan - that means index isn't being used)
```

## Conclusion

**This design achieves**:
- ✅ **Flexible schema**: JSONB adapts to game design changes without migrations
- ✅ **Fast queries**: <100ms for spatial/state lookups (10-100× faster than files)
- ✅ **Reliable IDs**: Server-managed UUIDs, LLM uses semantic names
- ✅ **Separation of concerns**: KB = templates (design), PostgreSQL = instances (runtime)
- ✅ **Simple caching**: In-memory template cache, no Redis complexity
- ✅ **Already on Supabase**: No new infrastructure needed

**Next Steps**:
1. Create `game_instances` and `player_progress` tables
2. Write initial instance spawn migration for Wylding Woods
3. Update `kb_agent.execute_game_command()` to load instances from PostgreSQL
4. Test with commands from `/tmp/test_*.json`
5. Monitor performance and optimize as needed
