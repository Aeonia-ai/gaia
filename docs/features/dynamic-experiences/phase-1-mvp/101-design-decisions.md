# Design Decisions Log

**Purpose**: Record key architectural decisions for instance management system
**Format**: ADR (Architecture Decision Records) lite
**Date Started**: 2025-10-26

## DD-001: File-Based Storage for MVP

**Date**: 2025-10-26
**Status**: ✅ Accepted
**Deciders**: User + server-frantz + server-frantz-gemini

### Context
Need to decide between PostgreSQL JSONB vs file-based storage for game instance management MVP.

### Decision
Use JSON files in KB directory structure instead of PostgreSQL for MVP (1-10 concurrent players).

### Rationale
- **Perplexity Research**: File-based storage appropriate for 1-10 player prototype scale
- **Simplicity**: Zero infrastructure overhead, easy to backup/version control with Git
- **Iteration Speed**: Faster development, can inspect/edit files directly
- **Validation**: MMO best practices confirm this approach for prototype scale
- **Migration Path**: Clear upgrade to PostgreSQL at 20-50+ concurrent players

### Consequences
**Positive**:
- Faster MVP delivery (hours vs days)
- Easy debugging (cat manifest.json)
- Git version control for all game state
- No database setup/maintenance

**Negative**:
- Manual queries slower than SQL
- No transactional guarantees (using atomic file ops instead)
- Will need migration at scale

**Mitigation**:
- Use atomic file operations (os.replace) for consistency
- Design file structure to map cleanly to PostgreSQL schema
- Plan migration path in advance

### References
- Perplexity research on MMO data architecture patterns
- [100-instance-management-implementation.md](./100-instance-management-implementation.md)

---

## DD-002: Incremental IDs vs UUIDs for LLM Systems

**Date**: 2025-10-26
**Status**: ✅ Accepted
**Deciders**: User + server-frantz (via Perplexity research)

### Context
Need to decide how to identify game instances in a way that works well with LLM interpretation.

### Decision
Use incremental integer IDs (1, 2, 3, 4...) instead of UUIDs.

**File naming**: `dream_bottle_1.json`, `dream_bottle_2.json`, `louisa_1.json`

### Rationale
**Perplexity Research** confirms:
- UUIDs are "random, hard to resolve" and "easy to hallucinate" for LLMs
- Incremental IDs have "predictable structure" that prevents hallucination
- Procedural generation systems use similar patterns
- Human-readable and debuggable

**LLM Hallucination Example**:
```
UUID: "dream_bottle_a3f2c891-4b2e-4d3a-9c1b-2e8f9a1b3c4d"
LLM might generate: "dream_bottle_a3f2c891-WRONG-4d3a-9c1b-2e8f9a1b3c4d"
```

**Incremental ID**:
```
Actual: "dream_bottle_1", "dream_bottle_2", "dream_bottle_3"
LLM pattern recognition: Simple sequence, low hallucination risk
```

### Consequences
**Positive**:
- LLMs can work with simple numeric patterns reliably
- Human-readable instance files
- Lower storage overhead than UUIDs
- Easier debugging ("instance 2" vs "instance a3f2c891...")

**Negative**:
- IDs must never be reused (track next_id in manifest)
- No distributed ID generation (acceptable for file-based system)

**Mitigation**:
- Central manifest.json tracks `next_id` counter
- Never reuse IDs even after deletion
- Document ID assignment process

### References
- Perplexity: "Incremental IDs vs UUIDs for LLM systems"
- Industry best practices in procedural generation

---

## DD-003: Semantic Names in LLM, IDs in Code

**Date**: 2025-10-26
**Status**: ✅ Accepted
**Deciders**: User + server-frantz + server-frantz-gemini

### Context
How should LLMs reference game instances without hallucinating invalid IDs?

### Decision
**Two-layer naming**:
- **LLM layer**: Works with semantic names only (`"dream_bottle"`, `"louisa"`)
- **Code layer**: Resolves semantic names to instance IDs (`dream_bottle_1.json`)

**Critical Rule**: **NEVER trust LLM to generate or select instance IDs** - always enforce in code.

### Rationale
**Best practice pattern**:
```python
# LLM returns semantic name
llm_response = {"action": "collect_item", "semantic_name": "dream_bottle"}

# Code resolves to actual instance
candidates = [inst for inst in manifest['instances']
              if inst['semantic_name'] == "dream_bottle"
              and inst['location'] == player_location]

instance_id = candidates[0]['id']  # Code selects ID, not LLM
```

**Why this works**:
- LLM operates at human-readable abstraction level
- Code handles technical identifiers
- Prevents LLM from inventing non-existent IDs
- Standard pattern in LLM-driven applications

### Consequences
**Positive**:
- LLM prompt complexity reduced (works with simple names)
- Zero risk of LLM hallucinating invalid IDs
- Code has full control over instance selection
- Easy to add disambiguation logic

**Negative**:
- Need mapping layer between semantic names and IDs
- Ambiguity when multiple instances share semantic name

**Mitigation**:
- Use location-based filtering (drastically reduces ambiguity)
- Implement clarification prompts for remaining ambiguities
- Store descriptions for human-friendly disambiguation

### References
- Perplexity research on LLM-friendly naming patterns
- server-frantz-gemini validation

---

## DD-004: GPS → Waypoint → Instances Resolution

**Date**: 2025-10-26
**Status**: ✅ Accepted
**Deciders**: User + server-frantz

### Context
How to determine which game instances are available to the player in an AR location-based game?

### Decision
Three-step resolution:
1. **Unity sends GPS** coordinates to server
2. **Server calculates** closest waypoint via Haversine distance (50m radius)
3. **Server filters instances** by waypoint ID

**Instances reference waypoint IDs, not raw GPS coordinates.**

### Rationale
**Existing proof of concept**: `/api/v0.3/locations/nearby` endpoint already implements GPS-to-waypoint matching with Haversine distance.

**Why this works**:
- **Physical location** drastically reduces instance ambiguity
- Most commands have exactly **1 valid instance** at player's GPS location
- Waypoints are the "location grid" - discrete zones instead of continuous coordinates
- 37 existing waypoints provide proven infrastructure

**Example**:
```
Player GPS: (37.9061, -122.5450)
    ↓ Haversine distance calculation
Closest waypoint: "waypoint_28a" (Mill Valley Library) - 15m away
    ↓ Filter instances by location
Available: [louisa_1, dream_bottle_1]  # Both at waypoint_28a
```

### Consequences
**Positive**:
- Massive reduction in semantic ambiguity
- Reuses existing GPS infrastructure
- Waypoints provide natural game boundaries
- Server-side location authority (no client cheating)

**Negative**:
- Player must be within 50m of waypoint to interact
- Haversine calculation on every command (acceptable - fast)

**Mitigation**:
- 50m radius balances accuracy vs usability
- Cache waypoint data in memory (static, loads once)
- Clear error messages when player not at waypoint

### References
- Existing `/api/v0.3/locations/nearby` implementation
- 37 waypoint markdown files in KB

---

## DD-005: Dictionary-Based Implementation (Not Classes)

**Date**: 2025-10-26
**Status**: ✅ Accepted
**Deciders**: User + server-frantz

### Context
Should we implement Gaia.Simulation class hierarchy (proposed by server-frantz-gemini) now or later?

### Decision
**MVP**: Use Python dictionaries and JSON file operations
**Future**: Refactor to classes when migrating to PostgreSQL

**Current approach**:
```python
# Load as dictionary
instance = json.load(open('dream_bottle_1.json'))
instance['state']['collected_by'] = user_id

# Write with atomic operation
temp = f"{file}.tmp"
with open(temp, 'w') as f:
    json.dump(instance, f)
os.replace(temp, file)
```

**Future refactoring** (when scaling):
```python
# Class-based approach
class ItemInstance(ObjectInstance):
    def collect(self, user_id):
        self.state['collected_by'] = user_id
        self.save()
```

### Rationale
**User directive**: "let's use dictionaries"

**Benefits**:
- **Faster MVP delivery**: No class hierarchy design needed
- **Simpler code**: Fewer abstractions to debug
- **Validate architecture first**: Ensure file structure works before adding class layer
- **Easier refactoring**: Dictionary→Class migration is straightforward

**Classic pattern**: "Make it work, make it right, make it fast"
1. **Make it work** (dictionaries) ← MVP
2. **Make it right** (classes) ← Refactoring phase
3. **Make it fast** (PostgreSQL) ← Scale phase

### Consequences
**Positive**:
- 6-9 hour implementation timeline (vs 2-3 days with classes)
- Direct JSON manipulation (no ORM complexity)
- Easy to inspect state files
- Flexibility to change structure quickly

**Negative**:
- No type checking (dict keys are strings)
- No method encapsulation (e.g., `instance.collect()`)
- Manual validation of required fields

**Mitigation**:
- Document expected dictionary structure clearly
- Use helper functions for common operations
- Plan class hierarchy design in parallel (ready when needed)

**Future Migration Path**:
- Keep Gaia.Simulation namespace design from server-frantz-gemini
- Implement when moving to PostgreSQL (natural refactoring point)
- Dictionaries will map cleanly to class attributes

### References
- User decision: "let's use dictionaries"
- server-frantz-gemini class hierarchy (deferred, not rejected)

---

## DD-006: Atomic File Operations (No Complex Locking)

**Date**: 2025-10-26
**Status**: ✅ Accepted
**Deciders**: server-frantz (via Perplexity research)

### Context
How to handle concurrent writes to instance files without complex distributed locking?

### Decision
Use `os.replace()` for atomic file writes. No additional locking mechanisms for MVP.

**Pattern**:
```python
# Atomic write
temp_file = f"{instance_file}.tmp"
with open(temp_file, 'w') as f:
    json.dump(data, f, indent=2)
os.replace(temp_file, instance_file)  # Atomic on POSIX
```

### Rationale
**Perplexity Research**:
- `os.replace()` is atomic on POSIX systems (macOS, Linux)
- "Last write wins" acceptable at 1-10 player scale
- File-based locking appropriate for prototype

**Why this works at MVP scale**:
- Low concurrency (1-10 players)
- Collision probability very low
- OS-level atomic operation prevents corruption
- No distributed system complexity

### Consequences
**Positive**:
- Simple implementation (no lock files, no semaphores)
- OS guarantees atomicity (no partial writes)
- Acceptable for prototype scale

**Negative**:
- "Last write wins" - concurrent updates may overwrite each other
- No conflict detection
- Won't scale to 50+ concurrent players

**Mitigation**:
- Add `_version` field to instance files (for future optimistic locking)
- Monitor for concurrent modification issues in testing
- Plan migration to proper locking when scaling:
  - **PostgreSQL**: Row-level locks + transactions
  - **Redis**: Distributed locks (SETNX pattern)
  - **Optimistic locking**: Version-based conflict detection

**Future Migration**:
```python
# Optimistic locking (future)
UPDATE game_instances
SET state = $1, _version = _version + 1
WHERE id = $2 AND _version = $3;

if cursor.rowcount == 0:
    raise ConcurrentModificationError()
```

### References
- Perplexity research on file-based locking patterns
- `_version` field included in instance JSON schema

---

## DD-007: Location-Based Disambiguation

**Date**: 2025-10-26
**Status**: ✅ Accepted
**Deciders**: server-frantz + server-frantz-gemini

### Context
How to handle multiple instances with the same semantic name (e.g., two "sword" items)?

### Decision
**Primary disambiguation**: Player's GPS location (waypoint filtering)
**Secondary disambiguation**: Prompt user for clarification with descriptions

**Pattern**:
```python
candidates = [inst for inst in manifest['instances']
              if inst['semantic_name'] == "dream_bottle"
              and inst['location'] == player_waypoint]

if len(candidates) == 1:
    return candidates[0]  # Unambiguous
elif len(candidates) > 1:
    return {"needs_clarification": True,
            "options": [c['description'] for c in candidates]}
```

### Rationale
**AR game advantage**: Physical location provides natural disambiguation

Most commands are **unambiguous**:
- Player at waypoint_28a wants "dream_bottle"
- Only 1 dream_bottle at waypoint_28a
- Result: Instant resolution

**Rare ambiguity** (multiple instances at same location):
- Two swords at same waypoint: "rusty sword" vs "shining sword"
- Prompt: "Which sword? (rusty sword / shining sword)"

### Consequences
**Positive**:
- 90%+ of commands resolve without clarification
- Location filter drastically reduces search space
- Natural UX (player interacts with what they see)

**Negative**:
- Edge case: Multiple identical items at same location
- Requires description field in manifest

**Mitigation**:
- Encourage unique descriptions per location during content design
- Fall back to clarification prompts when needed
- Track disambiguation requests to improve content design

### References
- server-frantz GPS resolution design
- MMO best practices for spatial queries

---

## DD-008: Sublocation Field - Server Semantic Labels, Unity Spatial Mapping

**Date**: 2025-10-26
**Status**: ✅ Accepted
**Deciders**: User + server-frantz + Perplexity research

### Context
Wylding Woods experience operates within a single GPS waypoint (Woander Store) but has multiple points of interest inside (fairy houses, shelves, magic mirror). How should the server track sub-waypoint locations without knowing 3D coordinates?

### Decision
**Two-layer location system**:
- **Waypoint**: GPS-based location (e.g., "waypoint_28a")
- **Sublocation**: Semantic label for indoor positioning (e.g., "fairy_door_1", "magic_mirror", "shelf_3")

**Server stores semantic labels, Unity maps to 3D transforms.**

**Instance Schema with Sublocation**:
```json
{
  "id": 1,
  "semantic_name": "louisa",
  "location": "waypoint_28a",
  "sublocation": "fairy_door_1",
  "instance_file": "npcs/louisa_1.json"
}
```

**Division of Responsibility**:

| Task | Server | Unity Client |
|------|--------|--------------|
| **Location naming** | ✅ Defines "fairy_door_1" | ✅ Creates GameObject with matching name |
| **3D positioning** | ❌ Never knows x,y,z coordinates | ✅ Transform has position/rotation |
| **Spatial logic** | ❌ No indoor mapping | ✅ AR Foundation handles placement |
| **Instance filtering** | ✅ Returns instances at sublocation | ✅ Renders objects at transforms |

### Rationale

**User directive**: "we can have semanticly meaningful location references in the waypoint, like 'fairy_door_1', 'magic_mirror', etc, which Unity can map to similarly named transforms"

**Critical principle**: "unity never places anything in the server" - server never knows 3D coordinates

**Perplexity Research on AR Game Spatial Patterns**:
- Industry standard: Server tracks waypoints/zones, client handles indoor positioning
- Pokémon GO / Niantic pattern: Server has location IDs, client does AR placement
- AR Foundation best practice: Use semantic anchors and named transforms
- Indoor positioning: Client-side via plane detection, raycasting, NavMesh

**Why this works**:
- **Server-client decoupling**: Server doesn't need to know 3D spatial logic
- **Designer-friendly**: Place named GameObjects in Unity editor visually
- **Flexible**: Change 3D positions without touching server data
- **Scalable**: Adding new sublocations doesn't require server schema changes

### Consequences

**Positive**:
- Clean separation of concerns (location IDs vs 3D space)
- Unity designers can iterate on spatial layout independently
- Server queries remain simple: filter by waypoint + sublocation
- AR placement logic stays in Unity (AR Foundation expertise)

**Negative**:
- Semantic names must match between server JSON and Unity GameObjects
- Naming convention required (document in Unity client guide)
- Typos in names cause placement failures

**Mitigation**:
- Document naming convention: lowercase_with_underscores
- Unity validation script to check for missing transforms
- Server returns clear error if sublocation not found
- Add sublocation to server response for Unity verification

### Implementation

**Server Response Includes Sublocation**:
```json
{
  "success": true,
  "actions": [{
    "type": "collect_item",
    "instance_id": 2,
    "semantic_name": "dream_bottle",
    "sublocation": "shelf_3"
  }]
}
```

**Unity Mapping**:
```csharp
string sublocation = response.actions[0].sublocation;

if (!string.IsNullOrEmpty(sublocation)) {
    Transform spawnPoint = GameObject.Find(sublocation);
    if (spawnPoint != null) {
        PlayCollectionAnimation(spawnPoint.position);
    } else {
        Debug.LogWarning($"Sublocation '{sublocation}' not found in scene");
    }
}
```

### References
- Perplexity: AR game spatial hierarchy patterns
- User quote: "I will migrate to having bounding-volumes or transforms acting as in-waypoint spawn points, object placement points, or movement targets eventually. Not for this demo due on Tuesday tho"
- Industry pattern: Pokémon GO uses S2 cells (geographic IDs) + client-side AR placement

---

## Summary Table

| Decision | Status | Impact | Migration Plan |
|----------|--------|--------|----------------|
| **DD-001: File-Based Storage** | ✅ Accepted | High | PostgreSQL at 20-50+ players |
| **DD-002: Incremental IDs** | ✅ Accepted | High | Keep pattern, add UUID option for distributed systems |
| **DD-003: Semantic Names** | ✅ Accepted | Critical | Keep pattern (works at all scales) |
| **DD-004: GPS Resolution** | ✅ Accepted | High | Add spatial indexing (PostGIS) when scaling |
| **DD-005: Dictionary-Based** | ✅ Accepted | Medium | Refactor to classes with PostgreSQL migration |
| **DD-006: Atomic File Ops** | ✅ Accepted | Medium | Add optimistic locking when scaling |
| **DD-007: Location-Based Disambiguation** | ✅ Accepted | High | Keep pattern, add spatial indexes |
| **DD-008: Sublocation Field** | ✅ Accepted | High | Keep pattern, add spatial queries when scaling |

---

## Future Decisions to Track

- **DD-009**: Class hierarchy implementation (Gaia.Simulation namespace)
- **DD-010**: PostgreSQL schema design (when migrating)
- **DD-010**: Redis caching strategy (session state, waypoint mappings)
- **DD-011**: Optimistic locking implementation (_version field usage)
- **DD-012**: Multi-user collaboration (shared vs personal instances)

---

**Last Updated**: 2025-10-26
**Next Review**: After MVP implementation complete
