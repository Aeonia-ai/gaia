# Instance Management Implementation - Validated Design

**Status**: Ready for Implementation
**Version**: 1.0
**Date**: 2025-10-26
**Validation**: Two Claude agents + Perplexity research

## Executive Summary

File-based instance management system for MMOIRL AR game MVP (1-10 concurrent players). Validated against MMO best practices with proven patterns for template/instance separation, semantic name resolution, and location-based filtering.

## Validation Sources

1. **Perplexity Research**: Incremental IDs superior to UUIDs for LLM systems
2. **Perplexity Research**: File-based storage appropriate for 1-10 player scale
3. **server-frantz**: Complete design with GPS-to-waypoint resolution
4. **server-frantz-gemini**: MMO best practices and class hierarchy validation

## Three-Layer Architecture

```
Layer 1: World Instances (Shared State)
   ↓ JSON files in instances/ directory
Layer 2: Player Progress (Per-User State)
   ↓ JSON files in players/{user_id}/
Layer 3: Player World View (Runtime Computed)
   ↓ Merge of layers 1+2 at command execution
```

## Directory Structure

```
kb/
├── experiences/
│   └── wylding-woods/
│       ├── instances/                    # Layer 1: World state
│       │   ├── manifest.json            # Central instance registry
│       │   ├── npcs/
│       │   │   └── louisa_1.json        # NPC instance
│       │   ├── items/
│       │   │   └── dream_bottle_1.json  # Item instance
│       │   └── quests/
│       │       └── find_bottle_1.json   # Quest instance
│       │
│       ├── templates/                    # Design-time definitions
│       │   ├── npcs/
│       │   │   └── louisa.md
│       │   ├── items/
│       │   │   └── dream_bottle.md
│       │   └── quests/
│       │       └── find_the_bottle.md
│       │
│       └── waypoints/                    # Existing 37 AR locations
│           ├── waypoint-001-mill-valley-library.md
│           └── ... (36 more)
│
└── players/                              # Layer 2: Per-user state
    └── {user_id}/                        # e.g., auth0|12345
        └── wylding-woods/
            └── progress.json
```

## Key Design Decisions

### DD-001: Incremental IDs > UUIDs

**Decision**: Use incremental integer IDs (1, 2, 3...) instead of UUIDs
**Rationale**: Perplexity research confirms predictable structure prevents LLM hallucination
**Format**: `dream_bottle_1.json`, `dream_bottle_2.json`

**Why UUIDs Fail with LLMs**:
- LLMs hallucinate invalid UUIDs: `a3f2c891-WRONG-4d3a-9c1b-2e8f9a1b3c4d`
- Hard to debug and read
- Higher storage overhead

**Why Incremental IDs Work**:
- Predictable: 1, 2, 3, 4...
- Human-readable
- Low hallucination risk
- Validated by procedural generation best practices

### DD-002: Semantic Names in LLM, IDs in Code

**Decision**: LLM works with semantic names, code resolves to instance IDs
**Pattern**:
```python
# LLM sees
"dream_bottle"

# Code resolves to
instance_id = 2
file = "items/dream_bottle_1.json"
```

**Implementation**:
```python
# LLM returns semantic name
llm_response = {"action": "collect_item", "semantic_name": "dream_bottle"}

# Code resolves using manifest
candidates = [inst for inst in manifest['instances']
              if inst['semantic_name'] == "dream_bottle"
              and inst['location'] == player_location]

instance = candidates[0]  # Take first match at player's location
```

**Critical Rule**: **NEVER trust LLM to generate/select IDs** - always enforce in code

### DD-003: GPS → Waypoint → Instances Resolution

**Decision**: Server calculates waypoint from GPS, instances reference waypoint IDs
**Flow**:
```
Unity GPS (37.9061, -122.5450)
    ↓ Haversine distance calculation
Server: Closest waypoint = "waypoint_28a" (within 50m radius)
    ↓ Filter by location
Instances at waypoint_28a: [louisa_1, dream_bottle_1]
```

**Why This Works**:
- Physical location drastically reduces ambiguity
- Most commands have exactly 1 valid instance at player's GPS location
- Proven pattern from existing `/api/v0.3/locations/nearby` endpoint

### DD-004: Dictionary-Based Implementation

**Decision**: Use Python dictionaries and JSON, not classes (for MVP)
**Rationale**: Faster path to working demo, validate architecture first

**Current Approach**:
```python
# Load as dictionary
instance = json.load(open('dream_bottle_1.json'))
instance['state']['collected_by'] = user_id
```

**Future Refactoring** (when scaling):
```python
# Refactor to classes
class ItemInstance(ObjectInstance):
    def collect(self, user_id):
        self.state['collected_by'] = user_id
```

**Migration Path**: Implement `Gaia.Simulation` namespace with class hierarchy when moving to PostgreSQL

### DD-005: Atomic File Operations

**Decision**: Use `os.replace()` for atomic writes, no complex locking needed
**Pattern**:
```python
# Atomic write
temp_file = f"{instance_file}.tmp"
with open(temp_file, 'w') as f:
    json.dump(data, f, indent=2)
os.replace(temp_file, instance_file)  # Atomic on POSIX
```

**Why This Works at 1-10 Player Scale**:
- `os.replace()` is atomic on POSIX systems
- "Last write wins" acceptable with low concurrency
- No complex distributed locking needed
- Validated by Perplexity as appropriate for prototype scale

**Future**: Add optimistic locking with `_version` field when scaling to 20-50+ players

### DD-006: Template File Format

**Decision**: Templates follow structured Markdown with blockquote metadata, matching west-of-house pattern
**Reference**: Existing pattern in `/kb/experiences/west-of-house/world/items/lamp.md`

**Format Structure**:
```markdown
# [Entity Name]

> **[Entity Type] ID**: [id]
> **Type**: [category]
> **[Additional Metadata]**: [value]

## Description
[Rich text description for LLM and humans]

## [Type-Specific Sections]
[Behavior, states, dialogue, mechanics, etc.]

## Unity Configuration
- Prefab: [prefab_name]
- [Other Unity-specific settings]
```

**Why This Format**:
- Human-readable markdown body
- Structured metadata in blockquotes (easy to parse)
- Consistent with existing KB content patterns
- LLM can extract both structured and narrative information
- Git-friendly (text-based, diffable)

---

#### NPC Template Example

**File**: `kb/experiences/wylding-woods/templates/npcs/louisa.md`

```markdown
# Louisa

> **NPC ID**: louisa
> **Type**: fairy
> **Role**: quest_giver
> **Size**: 6 inches tall

## Description
A small fairy with blue-lavender wings, about 6 inches tall. Her gossamer dress shimmers with iridescent threads that catch the light as she moves. She has an earnest, helpful demeanor and speaks with gentle, encouraging tones.

## Personality
- Warm and welcoming to visitors
- Deeply cares about the dreams of the forest
- Patient teacher of magical traditions
- Worries about the fading magic in the woods

## Dialogue Topics
### The Dream Bottles
"Long ago, dreams from the forest were captured in these bottles. They hold fragments of wonder, imagination, and possibility. Without them, the magic fades."

### The Fairy Houses
"Each house bears a symbol: spiral for creativity, star for hope, moon for dreams, sun for joy. Return the matching bottle to restore each house's power."

### How to Help
"Find the dream bottles scattered around Woander Store. When you find one, examine its symbol, then return it to the fairy house bearing the same mark."

## Behaviors
- **On First Meeting**: Introduces herself, explains the quest
- **During Quest**: Provides hints if player seems stuck
- **On Quest Complete**: Celebrates with player, thanks them warmly

## Unity Configuration
- Prefab: `Louisa.prefab`
- Animation Controller: `FairyIdle`
- Voice Lines: `/Audio/Louisa/`
- Interaction Range: 2.0 meters
```

---

#### Item Template Example

**File**: `kb/experiences/wylding-woods/templates/items/dream_bottle.md`

```markdown
# Dream Bottle

> **Item ID**: dream_bottle
> **Type**: collectible
> **Category**: quest_item
> **Rarity**: magical

## Description
A small glass bottle that glows with an inner light. Swirling mist dances inside, containing fragments of captured dreams. Each bottle bears a unique symbol etched into the glass—spiral, star, moon, or sun—corresponding to one of the fairy houses in the store.

The bottle feels warm to the touch and hums with a faint, pleasant vibration. The mist inside shifts colors based on which symbol it bears.

## Symbol Variants
- **Spiral** (turquoise glow): Represents creativity and imagination
- **Star** (golden glow): Represents hope and wishes
- **Moon** (silver glow): Represents dreams and night magic
- **Sun** (amber glow): Represents joy and energy

## Properties
- **Visual**: Translucent glass, ethereal glow, swirling particle effects
- **Size**: Small enough to hold in one hand (approximately 4 inches tall)
- **Weight**: Nearly weightless, as if filled with air
- **Collectible**: Yes, one-time pickup per instance
- **Quest Item**: Must be returned to matching fairy house

## Behaviors
### On Pickup
"You carefully lift the dream bottle. The mist inside swirls excitedly, as if recognizing your touch."

### On Examine
"The bottle bears a [SYMBOL] symbol. The mist inside glows with a [COLOR] light."

### On Successful Return
"The bottle dissolves into streams of light that flow into the fairy house. You hear distant, joyful music as the house glows brighter."

### On Wrong House Return (Validation Failure)
"The bottle's symbol doesn't match this house. Perhaps there's another house nearby with the matching symbol?"

## Unity Configuration
- Prefab: `DreamBottle.prefab`
- Material: `DreamBottleMaterial` (with 4 symbol variants)
- Particle System: `DreamMistParticles`
- Pickup Sound: `bottle_pickup.wav`
- Success Sound: `bottle_return_success.wav`
- Spawn Scale: 0.15 (Unity units)
```

---

**Template Usage Pattern**:
```python
# LLM reads template for rich context
template_content = await kb.read_file(
    f"experiences/wylding-woods/templates/{entity_type}/{template_name}.md"
)

# Instance references template
instance = {
    "id": 1,
    "template": "dream_bottle",  # Points to dream_bottle.md
    "symbol": "spiral",  # Instance-specific variant
    "location": "waypoint_28a"
}
```

**Benefits**:
1. **Content Updates**: Change template once, all instances reflect the new description
2. **LLM Context**: Rich narrative content for generating responses
3. **Unity Integration**: Clear prefab and configuration references
4. **Human Readable**: Game designers can edit without technical knowledge
5. **Version Control**: Text-based format works with Git

## File Formats

### 1. manifest.json (Central Instance Registry)

**Purpose**: Track all live instances with incremental IDs
**Location**: `kb/experiences/{experience}/instances/manifest.json`

```json
{
  "experience": "wylding-woods",
  "next_id": 3,
  "instances": [
    {
      "id": 1,
      "template": "louisa",
      "semantic_name": "louisa",
      "instance_file": "npcs/louisa_1.json",
      "location": "waypoint_28a",
      "sublocation": "fairy_door_1",
      "description": "A kind librarian who knows Mill Valley's secrets",
      "created_at": "2025-10-26T10:00:00Z"
    },
    {
      "id": 2,
      "template": "dream_bottle",
      "semantic_name": "dream_bottle",
      "instance_file": "items/dream_bottle_1.json",
      "location": "waypoint_28a",
      "sublocation": "shelf_3",
      "description": "A glowing bottle filled with swirling magical energy",
      "created_at": "2025-10-26T10:00:00Z"
    }
  ]
}
```

**Key Fields**:
- `id`: Incremental integer (never reuse)
- `semantic_name`: What LLM sees ("dream_bottle")
- `location`: Waypoint ID where instance exists
- `sublocation`: Optional semantic label for indoor positioning (Unity maps to GameObject transform)
- `description`: Human-readable descriptor (for disambiguation)

### 2. Instance File (items/dream_bottle_1.json)

**Purpose**: Mutable runtime state for specific instance
**Location**: `kb/experiences/{experience}/instances/items/dream_bottle_1.json`

```json
{
  "id": 2,
  "template": "dream_bottle",
  "semantic_name": "dream_bottle",
  "location": "waypoint_28a",
  "sublocation": "shelf_3",
  "state": {
    "collected_by": null,
    "glowing": true,
    "quest_item": true,
    "spawn_time": "2025-10-26T10:00:00Z"
  },
  "_version": 1
}
```

**State Management**:
- `state`: Flexible dictionary for runtime properties
- `_version`: Incrementing counter for optimistic locking (future)
- `collected_by`: null = available, user_id = collected
- `sublocation`: Semantic label for Unity transform mapping (optional)

### 3. Player Progress (players/{user_id}/wylding-woods/progress.json)

**Purpose**: Per-player game state
**Location**: `kb/players/{user_id}/{experience}/progress.json`

```json
{
  "user_id": "auth0|12345",
  "experience": "wylding-woods",
  "current_location": "waypoint_28a",
  "inventory": [2],
  "quest_progress": {
    "find_the_bottle": {
      "status": "completed",
      "started_at": "2025-10-26T10:00:00Z",
      "completed_at": "2025-10-26T10:30:00Z"
    }
  },
  "npc_relationships": {
    "louisa_1": {
      "trust_level": 0.7,
      "dialogue_state": "quest_offered",
      "last_interaction": "2025-10-26T10:25:00Z"
    }
  },
  "visited_waypoints": ["waypoint_28a", "waypoint_15c"],
  "stats": {
    "total_items_collected": 1,
    "quests_completed": 1,
    "playtime_minutes": 45
  },
  "created_at": "2025-10-26T09:00:00Z",
  "updated_at": "2025-10-26T10:35:00Z"
}
```

## In-Memory Caching Strategy

**Goal**: Eliminate file I/O overhead for manifest queries (500x performance improvement)

### Why Cache the Manifest?

**Without caching**:
```python
# Every command reads from disk (5ms latency)
def get_instances_at_waypoint(waypoint: str):
    with open('instances/manifest.json', 'r') as f:
        manifest = json.load(f)  # File I/O on every request
    return [i for i in manifest['instances'] if i['location'] == waypoint]
```

**With caching**:
```python
# Load once at startup, query from RAM (0.01ms latency)
class KBAgent:
    def __init__(self):
        self.manifest_cache = self._load_manifest()  # Load once
        self.manifest_lock = asyncio.Lock()  # Thread-safe writes

    async def get_instances_at_waypoint(self, waypoint: str):
        # Query from RAM - no file I/O
        return [
            i for i in self.manifest_cache['instances']
            if i['location'] == waypoint
        ]
```

**Performance Comparison**:
- Disk read: ~5ms per query
- RAM read: ~0.01ms per query
- **500x faster**

### Write-Through Caching Pattern

When state changes, update both cache AND disk atomically:

```python
class KBAgent:
    def __init__(self, kb_path: str):
        self.kb_path = kb_path
        self.manifest_cache = None
        self.manifest_lock = asyncio.Lock()
        self._load_manifest_into_cache()

    def _load_manifest_into_cache(self):
        """Load manifest once at startup"""
        manifest_path = f"{self.kb_path}/instances/manifest.json"
        with open(manifest_path, 'r') as f:
            self.manifest_cache = json.load(f)
        print(f"Loaded {len(self.manifest_cache['instances'])} instances into cache")

    async def _save_manifest_atomic(self, manifest_data: dict):
        """
        Write-through: Update cache and disk atomically
        Uses os.replace() for atomic file writes (POSIX)
        """
        manifest_path = f"{self.kb_path}/instances/manifest.json"
        temp_path = f"{manifest_path}.tmp"

        # Write to temp file
        with open(temp_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)

        # Atomic replace (no partial writes)
        os.replace(temp_path, manifest_path)

        # Update cache after successful disk write
        self.manifest_cache = manifest_data

    async def collect_item(self, instance_id: int, user_id: str):
        """
        Example: Collecting item with write-through caching
        """
        async with self.manifest_lock:
            # Find instance in cache
            instance_entry = next(
                (i for i in self.manifest_cache['instances'] if i['id'] == instance_id),
                None
            )

            if not instance_entry:
                return {"error": f"Instance {instance_id} not found"}

            # Remove from manifest (item collected)
            self.manifest_cache['instances'].remove(instance_entry)

            # Write through to disk (atomic)
            await self._save_manifest_atomic(self.manifest_cache)

            return {"success": True, "instance_id": instance_id}
```

### Concurrency Safety

**Problem**: What if 2 players collect the same item simultaneously?

**Solution**: `asyncio.Lock` prevents concurrent manifest writes

```python
async def collect_item(self, instance_id: int, user_id: str):
    async with self.manifest_lock:  # Only one writer at a time
        # Check if item still available
        instance = self._find_instance(instance_id)
        if not instance:
            return {"error": "Item already collected"}

        # Update manifest
        self.manifest_cache['instances'].remove(instance)
        await self._save_manifest_atomic(self.manifest_cache)
```

**Why this works at 1-10 player scale**:
- Low collision probability
- asyncio.Lock prevents race conditions
- os.replace() guarantees atomic writes
- "Last write wins" acceptable for prototype

**Future scaling** (20-50+ players):
- Add optimistic locking with `_version` field
- Migrate to PostgreSQL with row-level locks
- Add Redis for distributed locking

### What NOT to Cache

**Manifest**: ✅ Cache (small, read-heavy, shared by all players)
**Player Progress**: ❌ Don't cache for MVP (load on-demand, per-user unique)

**Player progress caching** (future optimization):
```python
# Only if needed - add LRU cache for active players
from functools import lru_cache

@lru_cache(maxsize=100)  # Cache last 100 active players
def get_player_state(user_id: str):
    player_file = f"{self.kb_path}/players/{user_id}/wylding-woods/progress.json"
    with open(player_file, 'r') as f:
        return json.load(f)
```

### Cache Invalidation

**Manifest cache never invalidates** - it's the single source of truth updated via write-through

**If external process modifies files** (e.g., admin tool):
```python
def reload_manifest(self):
    """Reload manifest from disk (for admin operations)"""
    self._load_manifest_into_cache()
    print("Manifest reloaded from disk")
```

### Performance Impact

**Before caching**:
- Query instances at waypoint: 5ms (disk read)
- 10 concurrent requests: 50ms total
- Bottleneck: File I/O

**After caching**:
- Query instances at waypoint: 0.01ms (RAM lookup)
- 10 concurrent requests: 0.1ms total
- **500x faster queries**

**Cost**: ~10KB RAM for manifest (negligible)

## Complete Flow: "Collect Dream Bottle" Command

### Step 1: Unity → Server Request

```json
POST /kb/game/execute_command
{
  "command": "collect the dream bottle",
  "experience": "wylding-woods",
  "user_id": "auth0|12345",
  "gps": "37.9061,-122.5450"
}
```

### Step 2: Server Determines Current Waypoint

```python
async def execute_game_command(
    command: str,
    user_id: str,
    experience: str,
    gps: str
):
    # Parse GPS coordinates
    lat, lng = parse_gps(gps)  # 37.9061, -122.5450

    # Load waypoints from KB markdown files
    waypoints = await self._load_waypoints(experience)

    # Find closest waypoint using Haversine distance
    current_waypoint = find_closest_waypoint(
        lat, lng, waypoints,
        max_radius=50  # 50 meter activation radius
    )

    if not current_waypoint:
        return {
            "error": "You're not at a waypoint. Move closer to a location.",
            "nearest_waypoint_distance": get_nearest_distance(lat, lng, waypoints)
        }

    # current_waypoint = {
    #   "id": "waypoint_28a",
    #   "name": "Mill Valley Library",
    #   "gps": [37.9061, -122.5450]
    # }
```

### Step 3: Load Instances at Waypoint

```python
    # Load central manifest
    manifest_path = f"{self.kb_path}/experiences/{experience}/instances/manifest.json"
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    # Filter instances by location (only at player's waypoint)
    instances_here = [
        inst for inst in manifest['instances']
        if inst['location'] == current_waypoint['id']
        and not self._is_collected(inst)  # Exclude already collected items
    ]

    # instances_here = [
    #   {"id": 1, "semantic_name": "louisa", ...},
    #   {"id": 2, "semantic_name": "dream_bottle", ...}
    # ]
```

### Step 4: Load Player State

```python
    # Load player progress file
    player_file = f"{self.kb_path}/players/{user_id}/{experience}/progress.json"

    if os.path.exists(player_file):
        with open(player_file, 'r') as f:
            player_state = json.load(f)
    else:
        # Create default player state
        player_state = {
            "user_id": user_id,
            "experience": experience,
            "current_location": current_waypoint['id'],
            "inventory": [],
            "quest_progress": {},
            "npc_relationships": {},
            "visited_waypoints": [current_waypoint['id']],
            "created_at": datetime.now().isoformat()
        }
```

### Step 5: LLM Interprets Command (Semantic Names Only)

```python
    # Build LLM context with semantic names
    llm_context = f"""
You are parsing a game command for an AR location-based game.

Player location: {current_waypoint['name']} ({current_waypoint['id']})

Available objects at this location:
{json.dumps([{
    "name": inst['semantic_name'],
    "description": inst['description']
} for inst in instances_here], indent=2)}

Player inventory (instance IDs): {player_state['inventory']}

Player command: "{command}"

Parse the command and return the action as JSON.
Format: {{"action": "collect_item", "semantic_name": "dream_bottle"}}

Only use semantic names from the available objects list above.
"""

    # LLM interprets (works with semantic names, NOT IDs)
    llm_response = await self.llm.chat([
        {"role": "system", "content": "You are a game command parser. Return only valid JSON."},
        {"role": "user", "content": llm_context}
    ])

    # Parse LLM response
    action = json.loads(llm_response['content'])
    # action = {"action": "collect_item", "semantic_name": "dream_bottle"}
```

### Step 6: Code Resolves Semantic Name → Instance ID

```python
    # Resolve semantic name to actual instance (CODE enforces, never trust LLM)
    semantic_name = action['semantic_name']

    candidates = [
        inst for inst in instances_here
        if inst['semantic_name'] == semantic_name
    ]

    if len(candidates) == 0:
        return {
            "error": f"There's no {semantic_name} here",
            "available": [inst['semantic_name'] for inst in instances_here]
        }

    elif len(candidates) == 1:
        # Unambiguous! Only one dream_bottle at this waypoint
        instance = candidates[0]  # id: 2

    else:
        # Multiple matches - ask for clarification
        return {
            "narrative": f"Which {semantic_name}?",
            "options": [
                {
                    "id": c['id'],
                    "description": c['description']
                } for c in candidates
            ],
            "needs_clarification": True
        }
```

### Step 7: Execute Action with Atomic File Operations

```python
    # Execute collection with atomic writes
    result = await self._collect_item(
        user_id=user_id,
        experience=experience,
        instance_id=instance['id'],
        current_waypoint=current_waypoint['id']
    )
```

**Atomic Collection Implementation**:

```python
async def _collect_item(
    self,
    user_id: str,
    experience: str,
    instance_id: int,
    current_waypoint: str
):
    """
    Collect an item with atomic file operations.
    No complex locking needed at 1-10 player scale.
    """
    # 1. Load instance file
    manifest = self._load_manifest(experience)
    instance_entry = next(
        (inst for inst in manifest['instances'] if inst['id'] == instance_id),
        None
    )

    if not instance_entry:
        return {"error": f"Instance {instance_id} not found"}

    instance_file = f"{self.kb_path}/experiences/{experience}/instances/{instance_entry['instance_file']}"

    with open(instance_file, 'r') as f:
        instance = json.load(f)

    # 2. Validate not already collected
    if instance.get('state', {}).get('collected_by'):
        return {
            "error": "Item already collected",
            "collected_by": instance['state']['collected_by']
        }

    # 3. Update instance (mark as collected) - ATOMIC WRITE
    instance['state']['collected_by'] = user_id
    instance['state']['collected_at'] = datetime.now().isoformat()
    instance['_version'] = instance.get('_version', 0) + 1

    # Atomic write pattern
    temp_file = f"{instance_file}.tmp"
    with open(temp_file, 'w') as f:
        json.dump(instance, f, indent=2)
    os.replace(temp_file, instance_file)  # Atomic OS operation

    # 4. Update player inventory - ATOMIC WRITE
    player_file = f"{self.kb_path}/players/{user_id}/{experience}/progress.json"

    with open(player_file, 'r') as f:
        player = json.load(f)

    player['inventory'].append(instance_id)
    player['current_location'] = current_waypoint
    player['updated_at'] = datetime.now().isoformat()

    # Atomic write pattern
    temp_file = f"{player_file}.tmp"
    with open(temp_file, 'w') as f:
        json.dump(player, f, indent=2)
    os.replace(temp_file, player_file)  # Atomic OS operation

    return {
        "success": True,
        "instance_id": instance_id,
        "narrative_context": instance_entry['description']
    }
```

### Step 8: LLM Generates Narrative

```python
    # Generate narrative based on actual result
    narrative_prompt = f"""
Generate a short, atmospheric narrative (2-3 sentences) for this event:

Player successfully collected: {instance['description']}
Location: {current_waypoint['name']}
Experience: {experience}

Create vivid, immersive text that makes the player feel present in the moment.
"""

    narrative_response = await self.llm.chat([
        {"role": "system", "content": "You are a narrative generator for an AR game."},
        {"role": "user", "content": narrative_prompt}
    ])

    narrative = narrative_response['content']
    # Example output:
    # "You pick up the glowing dream bottle from the library desk.
    #  Its ethereal light pulses gently in your hands, filling you
    #  with a sense of wonder and possibility..."
```

### Step 9: Return Response to Unity

```python
    return {
        "success": True,
        "narrative": narrative,
        "current_waypoint": current_waypoint['id'],
        "current_waypoint_name": current_waypoint['name'],
        "actions": [
            {
                "type": "collect_item",
                "instance_id": instance['id'],
                "semantic_name": semantic_name,
                "description": instance['description'],
                "sublocation": instance.get('sublocation')  # Unity uses for placement
            }
        ],
        "state_changes": {
            "inventory_added": [instance['id']],
            "instances_updated": [instance['id']],
            "location_confirmed": current_waypoint['id']
        },
        "player_state": {
            "inventory": player_state['inventory'],  # Updated list
            "current_location": current_waypoint['id'],
            "quest_progress": player_state['quest_progress']
        }
    }
```

**Unity Response Handling**:
```csharp
// Unity receives structured response
var response = JsonUtility.FromJson<GameCommandResponse>(jsonString);

if (response.success) {
    // Update UI with narrative
    narrativeText.text = response.narrative;

    // Update player inventory
    foreach (var itemId in response.state_changes.inventory_added) {
        playerInventory.Add(itemId);
    }

    // Trigger AR effects at correct sublocation
    if (response.actions[0].type == "collect_item") {
        var action = response.actions[0];

        // Use sublocation if provided to position AR effect
        if (!string.IsNullOrEmpty(action.sublocation)) {
            Transform spawnPoint = GameObject.Find(action.sublocation);
            if (spawnPoint != null) {
                PlayCollectionAnimation(spawnPoint.position);
            } else {
                Debug.LogWarning($"Sublocation '{action.sublocation}' not found");
                PlayCollectionAnimation(action.instance_id);  // Fallback
            }
        } else {
            PlayCollectionAnimation(action.instance_id);
        }
    }
}
```

## Implementation Checklist

### Phase 1: File Structure (30 minutes)
- [ ] Create `instances/` directory structure
- [ ] Create `instances/manifest.json` with initial instances
- [ ] Create `instances/npcs/louisa_1.json`
- [ ] Create `instances/items/dream_bottle_1.json`
- [ ] Create `players/` directory structure
- [ ] Create example `players/test-user/wylding-woods/progress.json`

### Phase 2: KB Agent Methods (2-3 hours)
- [ ] Implement `_load_manifest()` in kb_agent.py
- [ ] Implement `_load_player_state()` in kb_agent.py
- [ ] Implement `_create_default_player_state()` in kb_agent.py
- [ ] Implement `_collect_item()` with atomic operations
- [ ] Implement `_resolve_semantic_name()` for disambiguation
- [ ] Implement `find_closest_waypoint()` with Haversine distance

### Phase 3: Game Command Endpoint (2-3 hours)
- [ ] Update `execute_game_command()` to accept GPS parameter
- [ ] Add GPS-to-waypoint resolution
- [ ] Add instance loading at waypoint
- [ ] Add LLM semantic name interpretation
- [ ] Add code-enforced ID resolution
- [ ] Add narrative generation

### Phase 4: Testing (1-2 hours)
- [ ] Test "collect dream bottle" at correct location (waypoint_28a)
- [ ] Test "collect dream bottle" at wrong location (should fail)
- [ ] Test collecting already-collected item (should fail)
- [ ] Test ambiguous semantic name (multiple instances)
- [ ] Test player state persistence across commands
- [ ] Test atomic file operations under concurrent requests

### Phase 5: Documentation (30 minutes)
- [ ] Add code comments with design rationale
- [ ] Create example request/response in API docs
- [ ] Document error cases and edge cases

**Total Estimated Time**: 6-9 hours for complete implementation

## Migration Path (Future Scale)

### At 20-50+ Concurrent Players

**Move to PostgreSQL JSONB**:
```sql
CREATE TABLE game_instances (
    id SERIAL PRIMARY KEY,
    experience TEXT NOT NULL,
    template TEXT NOT NULL,
    semantic_name TEXT NOT NULL,
    location TEXT NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_instances_location ON game_instances(location);
CREATE INDEX idx_instances_semantic ON game_instances(semantic_name);
CREATE INDEX idx_instances_state ON game_instances USING GIN(state);
```

**Add Redis Caching**:
```python
# Cache player state for active sessions
redis.set(f"player:{user_id}:state", json.dumps(player_state), ex=3600)

# Cache waypoint-to-instances mapping
redis.set(f"waypoint:{waypoint_id}:instances", json.dumps(instances), ex=300)
```

**Implement Optimistic Locking**:
```python
# Version-based conflict resolution
UPDATE game_instances
SET state = $1, _version = _version + 1
WHERE id = $2 AND _version = $3;

if cursor.rowcount == 0:
    raise ConcurrentModificationError("Instance was modified by another request")
```

**Keep Same Patterns**:
- Semantic name resolution (still LLM-safe)
- GPS-to-waypoint resolution (proven pattern)
- Template/instance separation (industry standard)
- Location-based filtering (scales well with indexes)

## Validation Summary

✅ **Design Validated By**:
- **Perplexity**: Incremental IDs superior for LLMs, file-based appropriate for 1-10 players
- **server-frantz**: Complete implementation flow with GPS resolution
- **server-frantz-gemini**: MMO best practices, template/instance separation pattern
- **Existing System**: `/api/v0.3/locations/nearby` proves GPS-to-waypoint feasibility

✅ **Best Practices Confirmed**:
- Template/instance separation (Prototype pattern, ECS architecture)
- Semantic name resolution (reduces LLM hallucination)
- Location-based filtering (proven in procedural generation)
- Atomic file operations (appropriate for prototype scale)

✅ **Implementation Ready**:
- All file formats defined
- Complete flow documented (9 steps)
- Helper methods specified
- Error handling planned
- Migration path clear

---

**Status**: Design complete and validated. Ready for implementation.
**Next Step**: Create file structure and implement methods in kb_agent.py
**Timeline**: 6-9 hours to working "collect dream bottle" demo
