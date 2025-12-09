# Waypoint to Location-Based Architecture Analysis

**Date:** 2025-11-10
**Branch:** `feature/unified-experience-system`
**Purpose:** Analyze current waypoint implementation and chart evolution path to location-based architecture

---

## Executive Summary

**Current State:** GAIA has a working GPS-based waypoint system serving Unity clients with linear sequences.

**Gap:** System lacks the 4-tier spatial hierarchy (Zone → Location → Area → Point) and AOI (Area of Interest) pattern required for non-linear, location-based gameplay.

**Path Forward:** Evolution, not revolution. Extend existing patterns while maintaining backward compatibility.

---

## 1. Current State Analysis

### 1.1 Data Architecture

#### Three Data Sources (Different Purposes)

| File | Purpose | Managed By | Used By | Status |
|------|---------|------------|---------|--------|
| **world.json** | Runtime game state (mutable) | `UnifiedStateManager` | All player commands, WebSocket, admin commands | ✅ Active, production |
| **Waypoint markdown** | AR waypoint templates (GPS + metadata) | `WaypointReader` | `/api/v0.3/locations/nearby` endpoint | ✅ Active, production |
| **locations.json** | Legacy location templates | Legacy admin CRUD | Admin waypoint commands only | ⚠️ Legacy, mostly obsolete |

**Key Finding:** `world.json` and waypoint markdown are **separate systems** serving **different use cases**:
- Waypoint markdown = AR spatial anchors (GPS coordinates for geofencing)
- world.json = Game state (items, NPCs, quests, player progress)

**Current Mismatch:**
- Waypoint markdown files: 37 waypoints in `wylding-woods` (verified in tests)
- world.json locations: ~3-5 top-level locations with 14+ sublocations per location
- NO direct mapping between waypoint IDs and world.json location IDs

### 1.2 Implementation Components

#### Waypoint System (`/api/v0.3/locations/nearby`)

**Architecture:**
```
Unity Client
    ↓ HTTP GET /api/v0.3/locations/nearby?gps=37.906,-122.547&radius=1000
Gateway (locations_endpoints.py)
    ↓ HTTP GET /waypoints/{experience}
KB Service (waypoints_api.py)
    ↓ File reads from /kb/experiences/{exp}/waypoints/*.md
    └─→ Returns YAML frontmatter as JSON
Gateway
    └─→ Filters by GPS distance (Haversine)
    └─→ Transforms to Unity format
    └─→ Returns sorted by proximity
```

**Key Files:**
- `/Users/jasbahr/Development/Aeonia/server/gaia/app/services/gateway/routes/locations_endpoints.py` (lines 1-148)
  - `get_nearby_locations()` endpoint (line 22)
  - GPS parsing and validation (lines 47-67)
  - Distance filtering with Haversine (lines 73-110)
  - Unity format transformation (lines 118-128)

- `/Users/jasbahr/Development/Aeonia/server/gaia/app/services/locations/waypoint_reader.py` (lines 1-66)
  - HTTP client to KB Service (line 38)
  - Endpoint: `{kb_service_url}/waypoints/{experience}`

- `/Users/jasbahr/Development/Aeonia/server/gaia/app/services/locations/waypoint_transformer.py` (lines 1-52)
  - `transform_to_unity_format()` - Converts KB YAML to Unity JSON
  - Handles GPS-based and pathway waypoints

**Waypoint Data Model (YAML in markdown):**
```yaml
id: waypoint_28a
name: Woander's Dream Bottle Shop
location:
  lat: 37.7749
  lng: -122.4194
waypoint_type: vps  # or "pathway" for non-GPS
media:
  audio: 8-gravity-car-sounds.wav
  visual_fx: spark_jump
  interaction: wheel_rotation
  display_text: "The historic Gravity Car awaits"
```

**Unity JSON Format (output):**
```json
{
  "id": "8_inter_gravity_car",
  "name": "#8 INTER Gravity Car",
  "waypoint_type": "vps",
  "gps": [37.905696, -122.547701],
  "media": {
    "audio": "8-gravity-car-sounds.wav",
    "visual_fx": "spark_jump",
    "interaction": "wheel_rotation",
    "display_text": "The historic Gravity Car awaits"
  },
  "asset_bundle_url": "https://cdn.aeonia.ai/assets/8_inter_gravity_car.unity3d"
}
```

#### Game State System (world.json)

**Architecture:**
```
Unity Client (WebSocket or HTTP)
    ↓ Command: collect, move, talk, look
Gateway → KB Service
    ↓ ExperienceCommandProcessor.process_command()
    ↓ Fast Path (Python) OR Flexible Path (LLM + markdown)
UnifiedStateManager
    ↓ get_world_state(experience, user_id)
    ↓ update_world_state(experience, updates, user_id)
File: /kb/experiences/{exp}/state/world.json
```

**Key Files:**
- `/Users/jasbahr/Development/Aeonia/server/gaia/app/services/kb/unified_state_manager.py` (lines 1-100+)
  - `get_world_state()` - Loads world.json
  - `update_world_state()` - Modifies world.json
  - File locking for shared state model (fcntl)
  - NATS event publishing after state changes

- `/Users/jasbahr/Development/Aeonia/server/gaia/app/services/kb/command_processor.py`
  - Routes commands to Python handlers or LLM
  - Returns `CommandResult` contract

**world.json Structure:**
```json
{
  "locations": {
    "woander_store": {
      "name": "Woander's Dream Bottle Shop",
      "description": "...",
      "sublocations": {
        "entrance": {...},
        "spawn_zone_1": {"items": [...]},
        "spawn_zone_2": {"items": [...]},
        "fairy_house_spiral": {...}
        // 14+ sublocations total
      }
    }
  },
  "npcs": {
    "woander": {...},
    "louisa": {...}
  },
  "quests": {...},
  "metadata": {
    "_version": 6,
    "last_modified": "2025-11-05T19:42:13Z"
  }
}
```

### 1.3 Current Unity Client Behavior

**Linear Waypoint Sequence:**
```
WaypointManager:
  waypoints = [w1, w2, w3, w4]  // Array order = sequence
  currentIndex = 0

OnGPSUpdate():
  if distance(playerGPS, waypoints[currentIndex].gps) < activationRadius:
    OnWaypointEntered(waypoints[currentIndex])
    LoadInteractionPrefab()

OnInteractionComplete():
  currentIndex++
  MoveToNext()
```

**Limitations:**
- ❌ Linear only (can't skip waypoints or do non-linear exploration)
- ❌ No server-authoritative state (client decides when waypoint is "complete")
- ❌ No geofence enter/exit events tracked server-side
- ❌ No mission-based objective ordering
- ❌ Items/NPCs gated by mission progress (not always visible)

---

## 2. New Architecture Requirements

### 2.1 Spatial Hierarchy (4 Tiers)

```
Zone (Level 0)
  └─ Location (Level 2) ← GPS + geofence boundary
       └─ Area (Level 3)
            └─ Point (Level 4)
```

**Examples:**
```
Zone: "Mill Valley"
  Location: "Woander's Store" (GPS: 37.7749, -122.4194, radius: 50m)
    Area: "Main Floor"
      Point: "Display Shelf A"
      Point: "Display Shelf B"
    Area: "Back Room"
      Point: "Magic Mirror"
  Location: "Dream Weaver's Clearing" (GPS: 37.905696, -122.547701, radius: 30m)
    Area: "Fairy Grove"
      Point: "Louisa's Mushroom"
```

**Key Properties:**
- **Level 2 (Location)** = Has GPS coordinates + geofence radius
- **Level 3 (Area)** = Subregion within a location (no GPS, relative positioning)
- **Level 4 (Point)** = Interaction point (item spawn, NPC position)

### 2.2 AOI (Area of Interest) Pattern

**On Geofence Entry:**
```
Player enters "Woander's Store" geofence
  ↓
Server sends full location tree:
  └─ All Areas in this Location
  └─ All Points in each Area
  └─ All Items at each Point (visible, regardless of mission state)
  └─ All NPCs in this Location
  ↓
Unity spawns dynamic objects from server data
```

**Mission Progress Tracking (Server-Side):**
```
Mission: "Collect 3 Dream Bottles"
  Objectives:
    1. Collect bottle_of_joy (at Woander's Store)
    2. Collect bottle_of_courage (at Dream Weaver's Clearing)
    3. Talk to Louisa (at Dream Weaver's Clearing)
```

**Key Differences from Current:**
- ✅ Items always visible (not gated by mission state)
- ✅ Mission tracks objectives across multiple locations
- ✅ Player can visit locations in any order
- ✅ Server tracks geofence enter/exit events

### 2.3 WebSocket State Synchronization

**Current Gap (from CURRENT-STATUS-2025-11-09.md):**
```
✅ WebSocket connection successful
✅ Authentication working
✅ Ping/pong health checks passing
✅ Action protocol working (collect_bottle)
❌ Server doesn't tell client WHERE bottles are located
❌ Client cannot spawn any game objects
```

**Proposed (from websocket-world-state-sync-proposal.md):**
```json
{
  "type": "connected",
  "player": {
    "current_location": "woander_store",
    "inventory": []
  },
  "area_of_interest": {
    "location_id": "woander_store",
    "sublocations": {
      "spawn_zone_1": {
        "items": [{"id": "bottle_1", "type": "dream_bottle", ...}]
      }
    },
    "npcs": {"woander": {...}}
  }
}
```

**On Location Change:**
```json
{
  "type": "location_entered",
  "location_id": "dream_weaver_clearing",
  "area_of_interest": {
    // Full tree for new location
  }
}
```

---

## 3. Gap Analysis

### 3.1 Missing: Location Hierarchy Data Model

**Current:**
- Waypoints have `id`, `name`, `gps`, `media` (flat structure)
- world.json has `locations` → `sublocations` (2 levels only)
- No explicit hierarchy levels (Zone, Location, Area, Point)

**Needed:**
```python
# Domain models (app/domain/entities/)
@dataclass
class Location:
    id: str
    name: str
    level: int  # 2 for Location
    gps: Optional[GPSCoordinate]
    geofence_radius_meters: int
    parent_zone_id: Optional[str]
    areas: List['Area']

@dataclass
class Area:
    id: str
    name: str
    level: int  # 3 for Area
    parent_location_id: str
    points: List['Point']

@dataclass
class Point:
    id: str
    name: str
    level: int  # 4 for Point
    parent_area_id: str
    items: List[str]  # Item IDs
    npcs: List[str]   # NPC IDs
```

**Files to Create:**
- `/Users/jasbahr/Development/Aeonia/server/gaia/app/domain/entities/location.py`
- `/Users/jasbahr/Development/Aeonia/server/gaia/app/domain/entities/area.py`
- `/Users/jasbahr/Development/Aeonia/server/gaia/app/domain/entities/point.py`

### 3.2 Missing: Geofence Enter/Exit Tracking

**Current:**
- `/api/v0.3/locations/nearby` returns waypoints within radius (one-time query)
- No event tracking for geofence entry/exit
- Client decides when to trigger interactions

**Needed:**
```python
# app/services/kb/location_tracker.py
class LocationTracker:
    def handle_gps_update(self, user_id: str, gps: GPSCoordinate):
        """Track geofence transitions and emit events."""
        current_location = self._get_current_location(user_id)
        nearby_locations = self._find_nearby_locations(gps, radius=50)

        for loc in nearby_locations:
            if loc.id != current_location:
                # Emit NATS event: location.entered
                await self._on_location_entered(user_id, loc)

        if current_location and current_location not in nearby_locations:
            # Emit NATS event: location.exited
            await self._on_location_exited(user_id, current_location)
```

**NATS Events:**
```python
# app/shared/events.py
@dataclass
class LocationEnteredEvent:
    user_id: str
    location_id: str
    timestamp: datetime
    gps: GPSCoordinate

@dataclass
class LocationExitedEvent:
    user_id: str
    location_id: str
    timestamp: datetime
```

**WebSocket Endpoint:**
```python
# New endpoint: POST /api/v0.3/locations/gps-update
@router.post("/gps-update")
async def handle_gps_update(
    gps: GPSCoordinate,
    user_id: str = Depends(get_current_user)
):
    """Handle client GPS updates and trigger geofence events."""
    tracker = LocationTracker()
    events = await tracker.handle_gps_update(user_id, gps)
    return {"events": events}
```

### 3.3 Missing: AOI (Area of Interest) State Delivery

**Current:**
- world.json contains ALL locations for entire experience
- No filtering by player's current location
- WebSocket welcome message has no world state (from CURRENT-STATUS-2025-11-09.md)

**Needed:**
```python
# app/services/kb/aoi_manager.py
class AOIManager:
    def get_area_of_interest(
        self,
        experience: str,
        user_id: str,
        location_id: str
    ) -> Dict[str, Any]:
        """Get full location tree for current AOI."""
        world_state = await self.state_manager.get_world_state(experience, user_id)

        # Filter to ONLY current location
        location = world_state["locations"].get(location_id)

        # Get NPCs at this location
        npcs = {
            npc_id: npc_data
            for npc_id, npc_data in world_state["npcs"].items()
            if npc_data.get("location", "").startswith(location_id)
        }

        return {
            "location_id": location_id,
            "location": location,
            "npcs": npcs,
            "timestamp": datetime.utcnow().isoformat()
        }
```

**Integration Point:**
- `/Users/jasbahr/Development/Aeonia/server/gaia/app/services/kb/websocket_experience.py` (line 97)
  - Enhance welcome message with AOI
- `/Users/jasbahr/Development/Aeonia/server/gaia/app/services/kb/experience_connection_manager.py`
  - Track player's current location per WebSocket connection

### 3.4 Missing: Mission-Based Objective System

**Current:**
- world.json has `quests: {...}` (simple state tracking)
- No concept of objectives across multiple locations
- No server-authoritative objective completion

**Needed:**
```python
# app/domain/entities/mission.py
@dataclass
class Mission:
    id: str
    name: str
    objectives: List['Objective']
    required_objectives: int  # e.g., 3 out of 5

@dataclass
class Objective:
    id: str
    type: str  # "collect", "talk", "visit"
    target_id: str  # Item ID, NPC ID, or Location ID
    target_location_id: str  # Where this objective can be completed
    completed: bool
    order: Optional[int]  # None = can be completed in any order

# app/services/kb/mission_tracker.py
class MissionTracker:
    def check_objective_completion(
        self,
        user_id: str,
        mission_id: str,
        action: str,
        target_id: str
    ) -> ObjectiveResult:
        """Check if action completes an objective."""
        mission = self._get_mission(mission_id)

        for obj in mission.objectives:
            if obj.type == action and obj.target_id == target_id and not obj.completed:
                obj.completed = True
                await self._emit_objective_completed_event(user_id, obj)

                if self._is_mission_complete(mission):
                    await self._emit_mission_completed_event(user_id, mission)
```

### 3.5 Missing: Location → Waypoint Mapping

**Current:**
- Waypoint IDs: `8_inter_gravity_car`, `1_inter_woander_storefront`
- world.json location IDs: `woander_store`, `dream_weaver_clearing`
- NO explicit mapping between them

**Needed:**
```yaml
# waypoint-28a.md
id: waypoint_28a
name: Woander's Dream Bottle Shop
location:
  lat: 37.7749
  lng: -122.4194
waypoint_type: vps
# NEW: Link to world.json location
game_location_id: woander_store  # Maps to world.json locations.woander_store
```

**OR: Enhanced world.json structure:**
```json
{
  "locations": {
    "woander_store": {
      "name": "Woander's Dream Bottle Shop",
      "gps": {
        "lat": 37.7749,
        "lng": -122.4194,
        "geofence_radius_meters": 50
      },
      "waypoint_id": "waypoint_28a",  // Link to waypoint markdown
      "sublocations": {...}
    }
  }
}
```

---

## 4. Recommended Evolution Path

### 4.1 Phase 1: Foundation (1-2 weeks)

**Goal:** Add spatial hierarchy without breaking existing systems

**Tasks:**

1. **Define Domain Models** (2-3 days)
   - Create `app/domain/entities/location.py`
   - Create `app/domain/entities/area.py`
   - Create `app/domain/entities/point.py`
   - Add `gps` and `geofence_radius_meters` fields to Location

2. **Enhance world.json Schema** (1 day)
   ```json
   {
     "locations": {
       "woander_store": {
         "level": 2,  // NEW: Explicit level
         "gps": {"lat": 37.7749, "lng": -122.4194},  // NEW: GPS in world.json
         "geofence_radius_meters": 50,  // NEW: Geofence
         "waypoint_id": "waypoint_28a",  // NEW: Link to waypoint
         "sublocations": {
           "entrance": {
             "level": 3,  // NEW: Area level
             "points": {
               "shelf_a": {"level": 4, "items": [...]}  // NEW: Point level
             }
           }
         }
       }
     }
   }
   ```

3. **Backward Compatibility** (1 day)
   - Existing `/api/v0.3/locations/nearby` unchanged
   - UnifiedStateManager still reads/writes world.json
   - Waypoint markdown files unchanged
   - Add migration script to backfill new fields

**Deliverables:**
- Domain models defined
- world.json schema extended (backward compatible)
- Migration script for existing data

### 4.2 Phase 2: AOI State Delivery (1 week)

**Goal:** WebSocket clients receive location trees on connection

**Tasks:**

1. **Create AOIManager** (2 days)
   - File: `app/services/kb/aoi_manager.py`
   - Method: `get_area_of_interest(experience, user_id, location_id)`
   - Returns filtered world state for one location only

2. **Enhance WebSocket Welcome** (1 day)
   - File: `app/services/kb/websocket_experience.py` (line 97)
   - Add `area_of_interest` to welcome message
   - Include player's current location and inventory

3. **Add Location Change Events** (2 days)
   - NATS event: `LocationEnteredEvent`
   - WebSocket message: `{"type": "location_entered", "area_of_interest": {...}}`
   - Trigger: Player moves to new location (via GPS update or explicit `move` command)

4. **Testing** (1 day)
   - Unity client receives bottle locations on connection
   - Can spawn bottles dynamically
   - Location change events trigger new AOI delivery

**Deliverables:**
- AOIManager implemented
- WebSocket sends AOI on connection
- Location change events working

### 4.3 Phase 3: Geofence Tracking (1 week)

**Goal:** Server tracks geofence enter/exit events

**Tasks:**

1. **Create LocationTracker** (2 days)
   - File: `app/services/kb/location_tracker.py`
   - Method: `handle_gps_update(user_id, gps)`
   - Emit NATS events for enter/exit

2. **Add GPS Update Endpoint** (1 day)
   - Endpoint: `POST /api/v0.3/locations/gps-update`
   - Body: `{"gps": {"lat": 37.7749, "lng": -122.4194}}`
   - Returns: `{"events": ["entered:woander_store"], "area_of_interest": {...}}`

3. **WebSocket Integration** (1 day)
   - Client sends GPS updates via WebSocket
   - Server responds with location events + AOI

4. **State Persistence** (1 day)
   - Track player's `current_location` in player view
   - Update on geofence enter/exit

**Deliverables:**
- LocationTracker implemented
- GPS update endpoint working
- Server-authoritative location tracking

### 4.4 Phase 4: Mission System (2 weeks)

**Goal:** Non-linear missions with objectives across locations

**Tasks:**

1. **Define Mission Domain Models** (2 days)
   - File: `app/domain/entities/mission.py`
   - Models: `Mission`, `Objective`, `ObjectiveType`

2. **Create MissionTracker** (3 days)
   - File: `app/services/kb/mission_tracker.py`
   - Methods:
     - `get_active_missions(user_id)`
     - `check_objective_completion(user_id, action, target_id)`
     - `get_mission_progress(user_id, mission_id)`

3. **Integrate with Commands** (2 days)
   - `collect` command triggers objective check
   - `talk` command triggers objective check
   - `visit` command (new) for location-based objectives

4. **WebSocket Updates** (2 days)
   - NATS event: `ObjectiveCompletedEvent`
   - NATS event: `MissionCompletedEvent`
   - WebSocket forwards to client

5. **Testing** (1 day)
   - Multi-location mission completion
   - Non-linear objective order
   - Mission progress persistence

**Deliverables:**
- Mission system implemented
- Objectives track across locations
- Client receives mission progress updates

---

## 5. Backward Compatibility Strategy

### 5.1 Unity Client Migration

**Phase 1-2:** Dual mode support
- Old clients: Still use `/api/v0.3/locations/nearby` (unchanged)
- New clients: Use WebSocket AOI delivery
- Server supports both patterns

**Phase 3:** Deprecation
- Announce `/api/v0.3/locations/nearby` deprecation
- Provide migration guide for Unity client update
- 6-month deprecation window

**Phase 4:** Removal
- Remove legacy endpoint
- All clients use WebSocket AOI pattern

### 5.2 Data Migration

**world.json:**
```bash
# Migration script (one-time)
python scripts/migrate_world_json_to_hierarchy.py \
  --experience wylding-woods \
  --dry-run

# Output:
# - Adds "level" field to each location/sublocation
# - Backfills "gps" from waypoint markdown (if available)
# - Adds "geofence_radius_meters" (default: 50)
# - Preserves existing structure
```

**Waypoint markdown:**
- No changes required (backward compatible)
- Optional: Add `game_location_id` field for explicit mapping

---

## 6. Key Files Summary

### Existing Files (to modify)

| File | Lines | Purpose | Changes Needed |
|------|-------|---------|----------------|
| `app/services/gateway/routes/locations_endpoints.py` | 22-147 | `/api/v0.3/locations/nearby` endpoint | Add deprecation warning, optional migration to new format |
| `app/services/kb/websocket_experience.py` | 97-105 | WebSocket welcome message | Add AOI delivery |
| `app/services/kb/unified_state_manager.py` | 1-100+ | world.json state management | Support new hierarchy fields |
| `app/services/locations/waypoint_transformer.py` | 7-52 | YAML → Unity JSON | Add hierarchy fields to output |

### New Files (to create)

| File | Purpose |
|------|---------|
| `app/domain/entities/location.py` | Location domain model (Level 2) |
| `app/domain/entities/area.py` | Area domain model (Level 3) |
| `app/domain/entities/point.py` | Point domain model (Level 4) |
| `app/domain/entities/mission.py` | Mission and Objective models |
| `app/services/kb/aoi_manager.py` | Area of Interest state filtering |
| `app/services/kb/location_tracker.py` | Geofence enter/exit tracking |
| `app/services/kb/mission_tracker.py` | Mission progress tracking |
| `app/services/gateway/routes/location_tracking_endpoints.py` | GPS update endpoint |
| `scripts/migrate_world_json_to_hierarchy.py` | Data migration script |

---

## 7. Testing Strategy

### Unit Tests
```python
# tests/unit/domain/test_location_hierarchy.py
def test_location_has_gps_and_geofence():
    loc = Location(
        id="woander_store",
        gps=GPSCoordinate(37.7749, -122.4194),
        geofence_radius_meters=50
    )
    assert loc.is_within_geofence(GPSCoordinate(37.7750, -122.4195))

# tests/unit/services/test_aoi_manager.py
async def test_aoi_filters_to_current_location_only():
    aoi = await aoi_manager.get_area_of_interest(
        experience="wylding-woods",
        user_id="test-user",
        location_id="woander_store"
    )
    assert "woander_store" in aoi["location"]
    assert "dream_weaver_clearing" not in aoi
```

### Integration Tests
```python
# tests/integration/locations/test_geofence_tracking.py
async def test_gps_update_triggers_location_entered_event():
    response = await client.post(
        "/api/v0.3/locations/gps-update",
        json={"gps": {"lat": 37.7749, "lng": -122.4194}}
    )
    assert response.json()["events"] == ["entered:woander_store"]

# tests/integration/websocket/test_aoi_delivery.py
async def test_websocket_welcome_includes_aoi():
    async with websocket_client("/ws/experience") as ws:
        welcome = await ws.receive_json()
        assert "area_of_interest" in welcome
        assert welcome["area_of_interest"]["location_id"] == "woander_store"
```

### E2E Tests
```python
# tests/e2e/test_location_based_gameplay.py
async def test_player_enters_location_receives_items():
    # Player connects
    async with websocket_client("/ws/experience") as ws:
        welcome = await ws.receive_json()
        assert len(welcome["area_of_interest"]["items"]) > 0

    # Player moves to new location
    await ws.send_json({"command": "move", "target": "dream_weaver_clearing"})
    event = await ws.receive_json()
    assert event["type"] == "location_entered"
    assert len(event["area_of_interest"]["items"]) > 0
```

---

## 8. Risk Assessment

### High Risk
- **Breaking Unity Client:** Changing waypoint format breaks existing deployments
  - **Mitigation:** Dual mode support (Phases 1-2), gradual migration

### Medium Risk
- **Performance:** Sending full location tree on every geofence entry
  - **Mitigation:** AOI filtering (send ONLY current location), caching, compression

### Low Risk
- **Data Migration:** world.json backfilling fails
  - **Mitigation:** Dry-run mode, validation script, rollback plan

---

## 9. Success Criteria

**Phase 1 Complete:**
- ✅ Domain models defined and unit tested
- ✅ world.json schema extended with backward compatibility
- ✅ Data migration script validated on wylding-woods

**Phase 2 Complete:**
- ✅ Unity client receives bottle locations on WebSocket connection
- ✅ Client can spawn objects dynamically from server data
- ✅ AOI updates on location change

**Phase 3 Complete:**
- ✅ Server tracks player location via GPS updates
- ✅ Geofence enter/exit events emitted to client
- ✅ Player's current_location persisted in player view

**Phase 4 Complete:**
- ✅ Missions define objectives across multiple locations
- ✅ Player can complete objectives in any order
- ✅ Mission progress synced to client via WebSocket

---

## 10. Next Steps (Immediate Actions)

1. **Review this analysis** with architecture team
2. **Prioritize phases** based on Unity client roadmap
3. **Create Phase 1 implementation plan** with task breakdown
4. **Design world.json schema extension** with backward compatibility
5. **Prototype AOI delivery** in development branch

**Estimated Timeline:**
- Phase 1: 1-2 weeks
- Phase 2: 1 week
- Phase 3: 1 week
- Phase 4: 2 weeks
- **Total: 5-6 weeks** for complete location-based architecture

**Dependencies:**
- Unity client team alignment on AOI message format
- Decision on data migration strategy (in-place vs copy)
- NATS infrastructure for geofence events (already exists)

---

## Appendix: Architecture Patterns Applied

**Clean Architecture:**
- Domain entities (`Location`, `Area`, `Point`) in `app/domain/entities/`
- Use cases (`AOIManager`, `LocationTracker`, `MissionTracker`) in `app/services/kb/`
- Infrastructure (`UnifiedStateManager`, `WaypointReader`) decoupled via interfaces

**Hexagonal Architecture (Ports & Adapters):**
- **Port:** `ILocationRepository` (abstract)
- **Adapter:** `WorldJsonLocationRepository` (concrete, reads world.json)
- **Adapter:** `WaypointMarkdownRepository` (concrete, reads waypoint markdown)

**Domain-Driven Design:**
- **Bounded Contexts:** Waypoints (AR spatial) vs Locations (game state)
- **Aggregates:** Location (aggregate root) contains Areas and Points
- **Repositories:** `LocationRepository` for persistence
- **Domain Events:** `LocationEnteredEvent`, `ObjectiveCompletedEvent`

**AOI (Area of Interest) Pattern:**
- Progressive loading (industry standard: Pokémon GO, Minecraft)
- Server-authoritative state delivery
- Delta updates for state changes (already implemented via NATS)

---

**Document Status:** ✅ Complete - Ready for Architecture Review
**Author:** Claude Code (System Architecture Designer)
**Date:** 2025-11-10
