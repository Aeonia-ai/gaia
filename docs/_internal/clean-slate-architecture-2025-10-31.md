# Clean Slate Architecture: Dynamic Experiences System

**Date:** 2025-10-31
**Status:** Exploratory Research
**Purpose:** Design a new architecture from first principles for the Dynamic Experiences platform

---

## Document Purpose

This document captures an architectural exploration session where we're designing the Dynamic Experiences system from scratch, without being constrained by current implementation. The goal is to:

1. Question fundamental assumptions
2. Make explicit architectural decisions
3. Design for future scale and flexibility
4. Create a clear requirements specification

**Note:** This is NOT a replacement plan. It's a thought exercise to validate current design or identify improvements.

---

## Project Goal

**Vision:** A platform that lets content creators build interactive, location-based AR experiences (games, adventures, simulations) where:
- Players interact using natural language
- Game logic is defined in content files (markdown), not code
- An LLM interprets player intent and executes game rules
- Experiences can be single-player OR multiplayer
- World state persists and evolves based on player actions

**Primary User:** Content creators driving AI agents via conversational interface to build and test experiences.

---

## Architectural Decisions (Answered)

### 1. Primary Users
**Decision:** All of the above - support multiple user types

**Priority Order:**
1. Content Creators (Non-Technical) - Writers, designers using AI agents
2. Developers/Technical Creators - Engineers extending the system
3. Hybrid Teams - Designers + Developers collaborating
4. AI Agents/LLMs - Automated content generation
5. End Players - People playing the experiences

**Key Insight:** Priority is **creator driving AI agent via conversational interface**.

---

### 2. Command & Interaction Model

**Decision:** Hybrid command system with clear distinction

**Pattern:**
```
@create item magic_sword    ← Creator commands (@ prefix)
pick up the magic sword     ← Player commands (natural language)
talk to wizard              ← Player commands (natural language)
@delete waypoint_5          ← Creator commands (@ prefix)
```

**Rationale:**
- `@` prefix clearly signals "I'm editing, not playing" (proven pattern from MUDs)
- Natural language for players eliminates syntax learning
- On-brand for LLM-powered system
- Creators can seamlessly mix editing and testing

**Inspiration:** MUD wizard commands, Roblox admin commands, Minecraft creative mode

---

### 3. Access Control Model

**Decision:** Permission-based (not mode-switching)

**Implementation:**
```python
if command.startswith('@'):
    if user.role != "creator":
        return "Permission denied"
    execute_admin_command()
else:
    execute_player_command()
```

**Rationale:**
- Simple - no mode state to track
- Creators always have access to @ commands
- No accidental mode switches
- Future enhancement: Add `@test_mode` for experiencing as player without god powers

---

### 4. Command Discovery

**Decision:** Three-layered approach

**Layer 1: Built-in Help (MVP)**
```
@help                  # List all commands
@help create          # Show command details
```

**Layer 2: AI Suggestions (Enhanced)**
```
Creator: "I want to add a sword"
AI: "Try @create item sword or tell me details and I'll do it"
```

**Layer 3: Documentation (Reference)**
- External docs for deep learning
- In-system: `@docs` opens link

**Implementation:** Markdown files with frontmatter (like current system)
```
/admin-logic/
  @create.md    # Contains help + implementation
  @delete.md
```

Help text auto-generated from frontmatter. Fits content-first philosophy.

---

### 5. Storage Architecture

**Decision:** Granular file structure (one entity = one file)

**Structure:** (to be evolved)
```
experiences/wylding-woods/
  config.json
  locations/
    forest_entrance.json
    dark_cave.json
  items/
    magic_sword.json
  npcs/
    wizard.json
  players/
    jason@aeonia.ai.json
  templates/
    items/
    missions/
    npcs/
```

**Rationale:**
- **Future-proof:** Direct 1:1 mapping to database tables later
- **Git-friendly:** Clean diffs, fewer merge conflicts
- **Collaborative:** Multiple creators can work on different entities
- **Migration path:** `for file in */*.json; INSERT INTO ...`

**Database Migration:**
```
Directory → Table/Collection
Filename → Primary Key
File content → Row/Document
```

---

### 6. Concurrency Control

**Decision:** File locking now, DB transactions later

**Current (Files):**
```python
from filelock import FileLock

with FileLock("locations/castle.json.lock"):
    data = read_json("locations/castle.json")
    data["items"].append("sword")
    write_json("locations/castle.json", data)
```

**Future (Database):**
```python
async with db.transaction():
    data = await db.get(id)
    data = modify(data)
    await db.update(id, data)
```

**Rationale:**
- File locking: Simple, safe for MVP, single-server
- Pattern maps cleanly to DB transactions
- Database handles concurrency when scaling
- Limitation: Only works on same machine (fine for MVP)

---

### 7. Spatial Hierarchy

**Decision:** 4-level flexible hierarchy with optional levels

**Hierarchy:**
```
Zone (optional: city, neighborhood, region)
  └── Venue (required: specific location - store, waypoint, landmark)
      └── Area (optional: room, section, zone within venue)
          └── Point (required: interactive spot - GPS coord OR VPS transform)
```

**Level Definitions:**
- **Zone** = Geographic region (city, neighborhood, park) - GPS boundary
- **Venue** = Specific location (store, waypoint, landmark) - GPS OR VPS scan
- **Area** = Subdivision within venue (room, section, grove) - Optional detail
- **Point** = Interactive spot (GPS coordinate OR VPS transform anchor)

**Real-World Examples:**

**Woander Store (Dense Indoor VPS):**
```
Venue: "Woander Store"
  └── Point: "fairy-door-main" (VPS transform)
  └── Point: "spawn_zone_1" (VPS transform)
  └── Point: "shelf_1" (VPS transform)
```
Skips Zone (indoor only) and Area (single space)

**Mission Unpossible (Urban Mobile GPS):**
```
Zone: "Oakland Downtown"
  └── Venue: "Main Street Bus Stop"
      └── Point: "red_door_543" (GPS: 37.8957, -122.5232)
```
Skips Area (outdoor locations)

**Wylding Woods (Outdoor Trail Hybrid):**
```
Zone: "Mill Valley Parks"
  └── Venue: "Waypoint 28a" (GPS + VPS)
      └── Area: "Fairy Grove" (VPS sub-region)
          └── Point: "ancient_oak" (VPS transform)
```
Uses all four levels

**Positioning Types:**
- **GPS** - Outdoor, meter-level precision, lat/long coordinates
- **VPS** - Indoor, centimeter-level precision, transform anchors in scanned mesh
- **HYBRID** - Both GPS waypoint + VPS detail when at location

**File Structure (Current):**
```
experiences/wylding-woods/
  zones/
    mill-valley-parks.json
  venues/
    waypoint-28a.json
    woander-store.json
  areas/
    fairy-grove.json
  points/
    ancient-oak.json
    fairy-door-main.json
    red-door-543.json
```

**Database Migration (Future):**
```sql
CREATE TABLE locations (
  id UUID PRIMARY KEY,
  parent_id UUID REFERENCES locations(id),  -- Nullable for skipped levels

  -- Hierarchy
  type ENUM('zone', 'venue', 'area', 'point') NOT NULL,
  name TEXT NOT NULL,

  -- Positioning (polymorphic)
  position_type ENUM('gps', 'vps', 'hybrid') NOT NULL,

  -- GPS data (nullable if VPS only)
  latitude FLOAT,
  longitude FLOAT,

  -- VPS data (nullable if GPS only)
  vps_scan_id TEXT,
  transform_anchor TEXT,

  -- Spatial indexing
  h3_index TEXT,  -- For efficient geographic queries

  -- Metadata
  metadata JSONB
);

CREATE INDEX idx_parent ON locations(parent_id);
CREATE INDEX idx_type ON locations(type);
CREATE INDEX idx_h3 ON locations(h3_index);
```

**Migration Path:**
```
Directory structure → Table rows
zones/mill-valley-parks.json → INSERT (type='zone', parent_id=NULL)
venues/waypoint-28a.json → INSERT (type='venue', parent_id=zone_id)
points/ancient-oak.json → INSERT (type='point', parent_id=venue_id)
```

**Rationale:**
- Proven pattern (Google Maps, Foursquare, AR games all use similar)
- Flexible - skip levels when not needed
- Handles mixed positioning (GPS, VPS, hybrid) via type attribute
- Clean migration - file path maps directly to table rows
- Efficient queries via H3 spatial index
- Single polymorphic table simpler than separate tables per level

**Inspiration:** Google Maps (Country→City→POI), Pokemon GO (S2 cells→POI), Foursquare (City→Venue)

---

### 8. Data Model & Database Choice

**Decision:** Document-oriented database (MongoDB) with flexible schemas

**Rationale:**

**AI Content Flexibility**
- AI agents generate varied content structures that evolve over time
- Templates may have different fields (NPCs have dialogue trees, items have mechanics)
- Rigid schemas require constant migrations as content types expand
- Document databases embrace schema diversity while maintaining queryability

**Template-Instance Pattern**
- Templates = Markdown + parsed structure (like OOP classes)
- Instances = Runtime state + template reference (like OOP objects)
- Documents naturally support embedding template data OR referencing by ID
- Rich narrative content (markdown) coexists with structured game state

**Spatial Queries**
- Native geospatial indexing (2dsphere) for GPS-based queries
- Efficient "find nearby venues" without complex spatial libraries
- H3 hexagonal indexing for large-scale geographic partitioning
- Polymorphic position types (GPS/VPS/hybrid) in same collection

**Collections (Conceptual):**

1. **Experiences** - Game configuration and metadata
   - Experience ID, name, description
   - State model (shared vs isolated)
   - Multiplayer settings, creator info

2. **Locations** - Spatial hierarchy (Zone→Venue→Area→Point)
   - Parent reference (self-referential hierarchy)
   - Type (zone/venue/area/point)
   - Position type (GPS/VPS/hybrid) determines available fields
   - Geospatial indexes for proximity queries

3. **Templates** - Content blueprints (items, NPCs, missions)
   - Raw markdown source (human-editable)
   - Parsed structure (machine-readable)
   - AI generation metadata (who created, when, how)
   - Type-specific fields (flexible schema per type)

4. **Instances** - Runtime entity state
   - Template reference (which blueprint)
   - Current state (collected, damaged, active)
   - Location (where in spatial hierarchy)
   - Player associations (who owns/interacts)

5. **Players** - Per-player progression and inventory
   - Experience-specific state (isolated mode)
   - Shared state references (shared mode)
   - Quest progress, relationships, history

**Key Patterns:**

**Materialized Path for Hierarchy**
- Store full ancestry path in each location
- Fast "find all descendants" queries
- Example: `path: "mill-valley-parks/waypoint-28a/fairy-grove"`

**Polymorphic Documents**
- `position_type` field determines which position fields exist
- GPS locations have `latitude`/`longitude`
- VPS locations have `vps_scan_id`/`transform_anchor`
- Hybrid has both

**Embedded vs Referenced**
- Frequently accessed together → Embed (template data in instance)
- Large or shared across many → Reference (location hierarchy)
- AI content is embedded to reduce query round-trips

**Manifest Replacement**
- Current: Central `manifest.json` duplicates data, can desync
- Future: Dynamic views via database queries
- Always current, no synchronization maintenance

**Migration Strategy (Files → Database):**

1. **Directory → Collection**
   - `experiences/wylding-woods/` → `experiences` collection
   - `venues/*.json` → `locations` collection (type=venue)

2. **Content Preservation**
   - Markdown files → `raw` field (human-editable)
   - Parse markdown → `parsed` field (machine-readable)
   - Keep both for flexibility

3. **Relationship Mapping**
   - File references → Document references (ObjectId)
   - Directory hierarchy → Parent-child relationships
   - Symbolic links → Array of references

4. **Metadata Transfer**
   - Git timestamps → `created_at`/`last_modified`
   - File permissions → RBAC roles
   - Commit history → Change log collection

**Benefits:**

- **AI-Friendly:** Agents generate flexible structures without schema migrations
- **Performance:** Embedded data reduces joins, geospatial indexes speed location queries
- **Developer Experience:** Markdown coexists with structured data, familiar query language
- **Scalability:** Sharding by experience or geographic region when needed
- **Future-Proof:** Add new entity types without altering existing collections

**Inspiration:** Firestore (flexible schemas), MongoDB Atlas (geospatial), Notion (content + structure)

---

## Open Questions (Unanswered)

### Data Model
- [ ] What's the complete entity schema?
- [ ] What fields are required vs optional?
- [ ] How do entities reference each other?
- [ ] What's the relationship model? (foreign keys, embedded, references)

**Next Step:** Review examples to define schema.

---

### LLM Integration
- [ ] How does LLM interpret player commands?
- [ ] What context is sent to LLM?
- [ ] How is LLM response parsed and executed?
- [ ] How do we handle LLM hallucinations/errors?
- [ ] Streaming vs batch responses?

---

### State Models (Shared vs Isolated)
- [ ] How does state model work with spatial hierarchy?
- [ ] Where is player state stored in file structure?
- [ ] How is template instantiation handled for isolated experiences?
- [ ] What triggers state copying in isolated mode?
- [ ] How do locations relate to state (shared world vs isolated instances)?

**Current Understanding:**
- **Shared:** Single world, multiple player views
- **Isolated:** Each player gets copy of template

**Questions:**
- Are locations shared across all players or per-player in isolated mode?
- Does spatial hierarchy live in experience root or per-player?

---

### API Design
- [ ] What endpoints does this service expose?
- [ ] Request/response format?
- [ ] Synchronous vs streaming?
- [ ] Versioning strategy?

---

### Content Creation Workflow
- [ ] How does creator test changes?
- [ ] Hot reload or restart required?
- [ ] Sandbox/preview mode?
- [ ] Rollback mechanisms?
- [ ] Version control integration?

---

### Performance & Scale
- [ ] Response time targets?
- [ ] Concurrent user limits?
- [ ] Caching strategy?
- [ ] When to move from files to database?

---

### AI Agent Capabilities
- [ ] What can AI agent generate automatically?
- [ ] What requires human approval?
- [ ] How are AI-generated entities tracked?
- [ ] Quality control mechanisms?

---

## Design Principles

1. **Content-First:** Game logic in content files, not code
2. **Permission Over Mode:** Role-based access, not session modes
3. **Future-Proof Storage:** File structure mirrors database schema
4. **Seamless Mixing:** Creators can edit and test without context switching
5. **LLM as Interpreter:** Natural language commands for players
6. **Explicit Admin Actions:** @ prefix for creator operations

---

## Next Steps

1. **Define Data Model** - Review examples and create complete entity schemas
2. **Design LLM Integration** - How commands are interpreted and executed
3. **Detail State Models** - How shared/isolated works with granular files
4. **Specify API** - Service interface and contracts

---

## Research Notes

### Influences from Other Games

**MUDs (Multi-User Dungeons):**
- `@` prefix for wizard/admin commands
- Permission-based, not mode-based
- Seamless mixing of admin and play

**Minecraft:**
- `/` prefix for commands
- Creative mode for building while playing
- Permission levels (op vs player)

**Roblox:**
- `:` prefix for admin commands
- Rank-based permission system
- Chat-based command interface

**Key Takeaway:** `@` prefix for admin commands is a proven pattern with 30+ years of history in text-based virtual worlds.

---

## Status

**Last Updated:** 2025-10-31
**Current Phase:** Architectural Foundation Complete
**Next Action:** LLM Integration Design, State Model Details, API Specification

**Decisions Made:** 8/8 core architectural decisions
1. ✅ Primary Users
2. ✅ Command & Interaction Model
3. ✅ Access Control
4. ✅ Command Discovery
5. ✅ Storage Architecture
6. ✅ Concurrency Control
7. ✅ Spatial Hierarchy
8. ✅ Data Model & Database Choice