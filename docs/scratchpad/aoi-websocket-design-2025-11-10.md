# Area of Interest (AOI) WebSocket Design

**Date**: 2025-11-10
**Status**: Phase 1 MVP - Implemented and Tested
**Implementation**: `/app/services/kb/unified_state_manager.py` (build_aoi at line 1226)
**Context**: Location-based world state delivery for Unity AR client

---

## Problem Statement

Unity AR client connects via WebSocket but receives no world state data. Players cannot see items (bottles) to collect because the server doesn't send location contents on connection.

**Current Gap** (from `CURRENT-STATUS-2025-11-09.md`):
- ✅ WebSocket connection works
- ✅ Command processing works
- ❌ Welcome message sends only connection metadata
- ❌ No world state discovery on connect
- ❌ Unity can't spawn bottles

**Goal**: Implement Area of Interest (AOI) pattern where server sends relevant world state when client connects or moves to new locations.

---

## Architecture Research

### Industry Best Practices

**Question**: How do location-based AR games deliver world state?

**Research** (Pokémon GO, Niantic, MMOs, Minecraft, Roblox):

1. **Connection Handshake is Separate from World State**
   - Connection acknowledgment comes first (auth, session info)
   - World state sent in separate follow-up messages
   - Never combine connection + full state in single message

2. **Progressive Loading Over Single Payload**
   - Send immediate vicinity first (area of interest)
   - Stream additional data as needed
   - Avoids overwhelming mobile devices/networks
   - Faster perceived load times

3. **Tick-Based Synchronization for Updates**
   - Initial snapshot has version number
   - Delta updates reference base version
   - Prevents missed/out-of-order updates
   - Client buffers early deltas, requests resync if needed

4. **Area-Primary Data Structure**
   - Areas contain their items/NPCs (not items pointing to areas)
   - Matches Unity scene graph model
   - Better for "show me everything here" queries
   - Optional back-references for "where is this item" queries

5. **Empty Response for No Location Match**
   - Don't return error messages
   - Show empty/sparse map
   - Optional contextual message ("No locations nearby")
   - Maintains app reliability perception

**Sources**: Perplexity research, game architecture patterns

---

## Entity Model & Data Architecture

### Target Entity Model

From `mmoirl-actual/system/data/20-entity-relationship-model.md`:

**Spatial Hierarchy** (following MMO/game engine conventions):
1. **Geography** - GPS anchor with optional region metadata (e.g., "Mill Valley Parks Waypoint 28A", region: "san_francisco_bay_area")
2. **Zone** - Experience-specific themed location at a Geography (e.g., "Woander's Magical Shop" in Wylding Woods)
3. **Area** - Functional subdivisions within Zone (e.g., "counter", "display_shelf")
4. **Spot** - Precise interactable points (e.g., "counter.register")

**Entity Types**:
1. **Template** - Content blueprints (NPC definitions, item types)
2. **Instance** - Runtime entities spawned from templates
3. **Relationship** - Player-specific state with entities

**Note**: Queries use GPS distance (haversine), not hierarchical traversal. Region is metadata for UI filtering/optimization.

### Current vs. Target

**Current** (`world.json`):
- Monolithic file with everything mixed
- Items/NPCs embedded in locations
- No Template/Instance separation
- No Geography/Zone distinction

**Target** (granular entity model):
- Separate files per entity
- Geography shared across experiences
- Zones reference Geography
- Instances reference Templates
- Clear migration path to database

### Adapter Pattern Strategy

**Decision**: Use **Option C (Adapter Pattern)**

Instead of refactoring world.json immediately, create abstraction layer:

```python
# Domain interfaces (what AOI needs)
class IWorldState(ABC):
    async def get_zone(zone_id, experience_id) -> Zone
    async def get_instances_at_zone(...) -> List[Instance]
    async def get_player_state(...) -> PlayerState

# Implementation
class UnifiedStateManager(IWorldState):
    # Existing methods + new interface adapters
    # Reads world.json behind the scenes
```

**Benefits**:
- Unblocks demo immediately
- No breaking changes to world.json
- Later: swap implementation for database
- Clean separation of concerns

---

## WebSocket Message Flow Design

### Complete Flow

```
Client                          Server
  |                               |
  |------ WebSocket Connect ----->|
  |       ?token=JWT              |
  |       &experience=ww          |
  |                               |
  |<----- {"type": "connected"} --|
  |       {                       |
  |         "connection_id": "...",
  |         "user_id": "...",     |
  |         "experience": "ww",   |
  |         "timestamp": 123456   |
  |       }                       |
  |                               |
  |-- {"type": "update_location"}->|
  |    {                          |
  |      "lat": 37.906,           | → Query nearby geographies
  |      "lng": -122.544           | → Find zone for experience
  |    }                          | → Load instances
  |                               | → Merge template data
  |                               |
  |<-- {"type": "area_of_interest"}|
  |    {                          |
  |      "snapshot_version": 12345,
  |      "zone": {...},          |
  |      "areas": {...},          |
  |      "items": [...],          |
  |      "npcs": [...],           |
  |      "player": {...}          |
  |    }                          |
  |                               |
  |-- (player moves) ------------>|
  |                               |
  |-- {"type": "update_location"}->|
  |    {"lat": 37.908, ...}       | → Check geofence
  |                               | → Load new zone if changed
  |                               |
  |<-- {"type": "area_entered"} --|
  |    {                          |
  |      "zone_id": "waypoint_28a",
  |      "snapshot_version": 12350,
  |      "area_of_interest": {...}|
  |    }                          |
  |                               |
  |-- {"type": "action", ...} --->|
  |                               |
  |<-- {"type": "action_response"}|
  |                               |
  |<-- {"type": "world_update"} --|
  |    {                          |
  |      "version": 12351,        |
  |      "base_version": 12350,   |
  |      "changes": {...}         |
  |    }                          |
```

### Message Type Decisions

**Why separate `update_location` from `connected`?**
- Client needs GPS permission first
- GPS accuracy takes time to stabilize
- Follows industry separation of concerns
- Allows client control over when to request state

**Why version tracking on AOI?**
- Synchronizes with delta updates
- Client can buffer out-of-order updates
- Enables resync if updates missed
- Industry standard (tick-based sync)

---

## Area of Interest Payload Structure

### Complete AOI Schema

```json
{
  "type": "area_of_interest",
  "timestamp": 1730678400000,
  "snapshot_version": 12345,

  "zone": {
    "id": "woander_store",
    "name": "Woander's Magical Shop",
    "description": "The entrance to Woander's mystical shop...",
    "gps": {
      "lat": 37.906512,
      "lng": -122.544217
    }
  },

  # NOTE: Phase 1 MVP structure shown above
  # Phase 2 will add: geography_id, geofence_radius_m in gps object

  "areas": {
    "spawn_zone_1": {
      "id": "spawn_zone_1",
      "name": "Display Shelf Area",
      "description": "A shelf displaying various magical curiosities...",
      "items": [
        {
          "instance_id": "dream_bottle_1",
          "template_id": "dream_bottle",
          "type": "dream_bottle",
          "semantic_name": "peaceful dream bottle",
          "description": "A bottle glowing with soft azure light...",
          "collectible": true,
          "visible": true,
          "state": {
            "glowing": true,
            "dream_type": "peaceful",
            "symbol": "spiral"
          }
        }
      ],
      "npcs": []
    },
    "counter": {
      "id": "counter",
      "name": "Shop Counter",
      "description": "The main counter where Woander conducts business...",
      "items": [],
      "npcs": [
        {
          "instance_id": "woander_1",
          "template_id": "woander",
          "name": "Woander",
          "type": "shopkeeper_fairy",
          "description": "A cheerful blue elf shopkeeper...",
          "state": {
            "greeting_given": false,
            "shop_open": true
          }
        }
      ]
    }
  },

  "player": {
    "current_location": "woander_store",
    "current_area": null,
    "inventory": []
  }
}
```

### Key Design Decisions

**Area-contains-items structure** (not item-has-area):
- **Why**: Industry standard (Unity scene graphs, spatial partitioning)
- **Benefits**:
  - Natural grouping for rendering
  - Efficient "show me everything here" queries
  - Matches progressive loading pattern
  - Better for client-side culling
- **Source**: Game engine research (Unity Transform hierarchy, spatial queries)

**Template + Instance merge**:
- Items have both `template_id` (blueprint) and `instance_id` (runtime)
- AOI denormalizes template properties into instance for client convenience
- Client doesn't need separate template lookup
- Server maintains separation internally

**Snapshot versioning**:
- Enables tick-based synchronization
- Client can validate delta updates apply to correct base
- Critical for preventing desync in multiplayer

### Phase 1 vs Phase 2 Features

**Phase 1 (MVP - Current Implementation)**:
- Basic zone structure: `id`, `name`, `description`, `gps` (lat/lng only)
- Areas with `id`, `name`, `description` only
- Items with instance/template data and state
- NPCs with instance/template data and state
- Player state: `current_location`, `current_area`, `inventory`
- Timestamp-based snapshot versioning

**Phase 2 (Planned Enhancements)**:
- Zone: Add `geography_id`, `geofence_radius_m` in gps object
- Areas: Add `location`, `accessible_from`, `ambient` properties
- Zone: Add `environment` properties
- Monotonic counter versioning
- Enhanced GPS validation and geofencing

---

## Implementation Architecture

### Domain Layer - Interfaces

```python
# app/domain/interfaces/world_state.py
from abc import ABC, abstractmethod
from typing import Optional, List

class IWorldState(ABC):
    """Interface for world state queries (used by AOI use case)."""

    @abstractmethod
    async def get_zone_by_geography(
        self,
        geo_id: str,
        experience_id: str
    ) -> Optional[Zone]:
        """
        Get zone (themed location) for geography in experience.

        Geography = GPS anchor (may have region metadata)
        Zone = Experience-specific theming at that Geography
        """
        pass

    @abstractmethod
    async def get_instances_at_zone(
        self,
        zone_id: str,
        experience_id: str
    ) -> List[Instance]:
        """Get all item/NPC instances in a zone (includes all areas)."""
        pass

    @abstractmethod
    async def get_template(
        self,
        template_id: str,
        experience_id: str
    ) -> Optional[Template]:
        """Get template definition."""
        pass

    @abstractmethod
    async def get_player_state(
        self,
        user_id: str,
        experience_id: str
    ) -> PlayerState:
        """Get player's current state."""
        pass

    @abstractmethod
    async def get_nearby_geographies(
        self,
        lat: float,
        lng: float,
        radius_m: int
    ) -> List[Geography]:
        """Find geographies near GPS coordinates."""
        pass
```

### Use Case Layer

```python
# app/use_cases/get_area_of_interest.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class GetAOIRequest:
    user_id: str
    experience_id: str
    lat: float
    lng: float

@dataclass
class GetAOIResponse:
    aoi: Optional[dict]
    snapshot_version: int
    success: bool
    error: Optional[str] = None

class GetAreaOfInterestUseCase:
    """
    Use Case: Get Area of Interest for player location.

    Orchestrates fetching zone, instances, templates, and player state
    to build complete AOI payload for client.
    """

    def __init__(self, world_state: IWorldState):
        self.world_state = world_state

    async def execute(self, request: GetAOIRequest) -> GetAOIResponse:
        # 1. Find nearby geographies
        geographies = await self.world_state.get_nearby_geographies(
            request.lat,
            request.lng,
            radius_m=100
        )

        if not geographies:
            # Industry pattern: empty response, not error
            return GetAOIResponse(
                aoi=None,
                snapshot_version=self._get_current_version(),
                success=True
            )

        # 2. Get zone for first geography
        # TODO: Handle multiple geographies (disambiguation)
        geo = geographies[0]
        zone = await self.world_state.get_zone_by_geography(
            geo.id,
            request.experience_id
        )

        if not zone:
            return GetAOIResponse(
                aoi=None,
                snapshot_version=self._get_current_version(),
                success=True
            )

        # 3. Get instances at zone
        instances = await self.world_state.get_instances_at_zone(
            zone.id,
            request.experience_id
        )

        # 4. Get templates and merge with instances
        template_ids = list(set(i.template_id for i in instances))
        templates = {}
        for tid in template_ids:
            t = await self.world_state.get_template(tid, request.experience_id)
            if t:
                templates[tid] = t

        # 5. Get player state
        player = await self.world_state.get_player_state(
            request.user_id,
            request.experience_id
        )

        # 6. Build AOI payload
        aoi = self._build_aoi(zone, instances, templates, player)

        return GetAOIResponse(
            aoi=aoi,
            snapshot_version=self._get_current_version(),
            success=True
        )

    def _build_aoi(self, zone, instances, templates, player):
        """
        Assemble AOI with area-contains-items structure.
        Merge template properties into instance data.
        """
        # Group instances by area
        areas = {}
        for area_id, area_meta in zone.areas.items():
            areas[area_id] = {
                "id": area_id,
                "name": area_meta["name"],
                "description": area_meta["description"],
                "items": [],
                "npcs": []
            }

        # Add instances to areas
        for instance in instances:
            area_id = instance.area_id
            if area_id not in areas:
                continue  # Skip orphaned instances

            # Merge template + instance
            template = templates.get(instance.template_id)
            if not template:
                continue  # Skip if template missing

            merged = {
                "instance_id": instance.id,
                "template_id": instance.template_id,
                **template.properties,  # Denormalize template data
                "state": instance.state  # Instance-specific state
            }

            if template.type == "item":
                areas[area_id]["items"].append(merged)
            elif template.type == "npc":
                areas[area_id]["npcs"].append(merged)

        return {
            "zone": {
                "id": zone.id,
                "name": zone.name,
                "description": zone.description,
                "gps": zone.gps  # Phase 1: {lat, lng} only, no geofence_radius_m
                # Phase 2 will add: geography_id field
            },
            "areas": areas,
            "player": {
                "current_location": player.current_location,
                "current_area": player.current_area,
                "inventory": player.inventory
            }
        }

    def _get_current_version(self) -> int:
        """
        Get current snapshot version for synchronization.

        TODO: Implement proper versioning strategy:
        - Monotonic counter per experience
        - Timestamp-based (milliseconds)
        - Or use existing NATS sequence numbers
        """
        import time
        return int(time.time() * 1000)
```

### Adapter Layer

```python
# app/services/kb/unified_state_manager.py (extended)

class UnifiedStateManager(IWorldState):
    """
    Existing state manager extended with IWorldState interface.

    Reads world.json and presents it as granular entities.
    No breaking changes to existing code.
    """

    # ... existing methods ...

    async def get_zone_by_geography(
        self,
        geo_id: str,
        experience_id: str
    ) -> Optional[Zone]:
        """
        Adapter: Extract zone from world.json location.

        In current model: geo_id == location_id
        Future: separate geography → zone mapping
        """
        world = await self._load_world_state(experience_id)
        location = world.get("locations", {}).get(geo_id)

        if not location:
            return None

        return Zone(
            id=location["id"],
            name=location["name"],
            description=location["description"],
            geography_id=geo_id,
            areas=self._extract_area_metadata(location)
        )

    async def get_instances_at_zone(
        self,
        zone_id: str,
        experience_id: str
    ) -> List[Instance]:
        """
        Adapter: Extract instances from world.json location.

        Items and NPCs in sublocations become Instance entities.
        """
        world = await self._load_world_state(experience_id)
        location = world.get("locations", {}).get(zone_id)

        if not location:
            return []

        instances = []

        # Extract items from all areas
        for area_id, area in location.get("sublocations", {}).items():
            for item in area.get("items", []):
                instances.append(Instance(
                    id=item["id"],  # instance_id
                    template_id=item["id"],  # same in current model
                    area_id=area_id,
                    state=item.get("state", {})
                ))

            # Extract NPC if present
            npc_id = area.get("npc")
            if npc_id:
                npc = world.get("npcs", {}).get(npc_id)
                if npc:
                    instances.append(Instance(
                        id=f"{npc_id}_1",  # synthetic instance_id
                        template_id=npc_id,
                        area_id=area_id,
                        state=npc.get("state", {})
                    ))

        return instances

    async def get_template(
        self,
        template_id: str,
        experience_id: str
    ) -> Optional[Template]:
        """
        Adapter: Extract template from inline item/NPC data.

        In world.json, items are inline. Extract shared properties
        as "template" definition.
        """
        world = await self._load_world_state(experience_id)

        # Search locations for item
        for location in world.get("locations", {}).values():
            for area in location.get("sublocations", {}).values():
                for item in area.get("items", []):
                    if item.get("id") == template_id:
                        return Template(
                            id=item["id"],
                            type="item",
                            properties={
                                "type": item.get("type"),
                                "semantic_name": item.get("semantic_name"),
                                "description": item.get("description"),
                                "collectible": item.get("collectible", False),
                                "visible": item.get("visible", True)
                            }
                        )

        # Check NPCs
        npc = world.get("npcs", {}).get(template_id)
        if npc:
            return Template(
                id=npc["id"],
                type="npc",
                properties={
                    "name": npc.get("name"),
                    "type": npc.get("type"),
                    "description": npc.get("description"),
                    "dialogue": npc.get("dialogue", {})
                }
            )

        return None

    async def get_nearby_geographies(
        self,
        lat: float,
        lng: float,
        radius_m: int
    ) -> List[Geography]:
        """
        Find geographies near GPS coordinates.

        TODO: Implement actual GPS distance calculation
        Current: Returns all locations (no GPS in world.json yet)
        """
        # Placeholder: return empty for now
        # Future: Calculate Haversine distance for each location
        return []

    def _extract_area_metadata(self, location: dict) -> dict:
        """Extract area definitions (not items/NPCs)."""
        areas = {}
        for area_id, area_data in location.get("sublocations", {}).items():
            areas[area_id] = {
                "id": area_id,
                "name": area_data.get("name"),
                "description": area_data.get("description")
            }
        return areas
```

---

## Version Tracking & Synchronization

### Snapshot Version Strategy

**Problem**: Client receives initial AOI, then delta `world_update` events. How to ensure deltas apply to correct base state?

**Solution**: Tick-based synchronization (industry standard)

```json
// Initial AOI
{
  "type": "area_of_interest",
  "snapshot_version": 12345,
  "zone": {...}
}

// Delta update references base
{
  "type": "world_update",
  "version": 12346,
  "base_version": 12345,
  "changes": {
    "player.inventory": {
      "operation": "add",
      "item": {...}
    }
  }
}
```

### Client Behavior

1. **Receive AOI**: Store `snapshot_version = 12345`
2. **Buffer deltas**: If `update.base_version > snapshot_version`, queue it
3. **Apply deltas**: If `update.base_version == snapshot_version`, apply and increment
4. **Resync**: If version gap detected, request new AOI snapshot

### Implementation Options

**Option A: Timestamp-based**
```python
snapshot_version = int(time.time() * 1000)  # milliseconds
```
- Pro: Simple, no state to track
- Con: Not deterministic, clock skew issues

**Option B: Monotonic counter**
```python
# Per-experience version counter
version_counters[experience_id] += 1
snapshot_version = version_counters[experience_id]
```
- Pro: Deterministic, clear causality
- Con: Needs persistence, counter management

**Option C: NATS sequence numbers**
```python
# Use existing NATS message sequence
snapshot_version = nats_msg.sequence
```
- Pro: Leverages existing infrastructure
- Con: Couples to NATS implementation

**Recommendation**: Start with **Option A** (timestamp), migrate to **Option B** (counter) when multi-writer conflicts become an issue.

---

## Caching Strategy

### Problem

`world.json` changes when players interact (collect items, talk to NPCs). How to balance read performance vs. freshness?

### Solution: Event-Based Cache Invalidation

```python
class CachedWorldState:
    """
    Cache world.json with NATS event-based invalidation.
    """

    def __init__(self):
        self._cache = {}  # {experience_id: (world_data, version)}
        self._nats = None

    async def initialize(self, nats_client):
        """Subscribe to world update events."""
        self._nats = nats_client
        await self._nats.subscribe(
            "world.updates.>",
            self._handle_world_update
        )

    async def get_world(self, experience_id: str):
        """Get cached world or load fresh."""
        if experience_id not in self._cache:
            world = await self._load_from_disk(experience_id)
            version = self._get_file_version(experience_id)
            self._cache[experience_id] = (world, version)

        return self._cache[experience_id][0]

    async def _handle_world_update(self, msg):
        """NATS event handler: invalidate cache on world change."""
        experience_id = msg.data.get("experience")
        if experience_id in self._cache:
            del self._cache[experience_id]
            logger.info(f"Cache invalidated for {experience_id}")
```

**Benefits**:
- Fast reads (in-memory cache)
- Fresh data (invalidated on writes)
- Leverages existing NATS infrastructure
- Automatic cleanup on world changes

---

## WebSocket Endpoint Integration

### Updated Handler

```python
# app/services/kb/websocket_experience.py

@router.websocket("/ws/experience")
async def websocket_experience_endpoint(
    websocket: WebSocket,
    token: str,
    experience: str,
    use_case: GetAreaOfInterestUseCase = Depends(get_aoi_use_case)
):
    # Authenticate
    user = await get_current_user_ws(token)

    # Accept connection
    await websocket.accept()

    # Send connection acknowledgment
    await websocket.send_json({
        "type": "connected",
        "connection_id": str(uuid.uuid4()),
        "user_id": user.id,
        "experience": experience,
        "timestamp": int(time.time() * 1000)
    })

    # Wait for location update
    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "update_location":
                # Client sent GPS coordinates
                lat = message.get("lat")
                lng = message.get("lng")

                # Get AOI
                request = GetAOIRequest(
                    user_id=user.id,
                    experience_id=experience,
                    lat=lat,
                    lng=lng
                )
                response = await use_case.execute(request)

                if response.aoi:
                    # Send AOI to client
                    await websocket.send_json({
                        "type": "area_of_interest",
                        "snapshot_version": response.snapshot_version,
                        **response.aoi
                    })
                else:
                    # Empty response (no location nearby)
                    await websocket.send_json({
                        "type": "area_of_interest",
                        "snapshot_version": response.snapshot_version,
                        "zone": None,
                        "areas": {},
                        "player": {...}
                    })

            elif msg_type == "action":
                # Existing action handling...
                pass

            elif msg_type == "ping":
                # Existing ping handling...
                pass

    except WebSocketDisconnect:
        logger.info(f"Client {user.id} disconnected")
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_get_aoi_use_case.py

class MockWorldState(IWorldState):
    """Mock implementation for testing."""

    def __init__(self):
        self.zones = {}
        self.instances = {}
        self.templates = {}

    async def get_zone_by_geography(self, geo_id, experience_id):
        return self.zones.get((geo_id, experience_id))

    # ... other methods ...

@pytest.mark.asyncio
async def test_get_aoi_returns_zone_with_items():
    # Arrange
    mock_state = MockWorldState()
    mock_state.zones[("geo_1", "ww")] = Zone(...)
    mock_state.instances[("woander_store", "ww")] = [Instance(...)]

    use_case = GetAreaOfInterestUseCase(mock_state)
    request = GetAOIRequest(
        user_id="user_1",
        experience_id="ww",
        lat=37.906,
        lng=-122.544
    )

    # Act
    response = await use_case.execute(request)

    # Assert
    assert response.success
    assert response.aoi["zone"]["id"] == "woander_store"
    assert len(response.aoi["areas"]["spawn_zone_1"]["items"]) == 1

@pytest.mark.asyncio
async def test_get_aoi_empty_when_no_geography():
    # Arrange
    mock_state = MockWorldState()
    use_case = GetAreaOfInterestUseCase(mock_state)
    request = GetAOIRequest(
        user_id="user_1",
        experience_id="ww",
        lat=0.0,  # Middle of ocean
        lng=0.0
    )

    # Act
    response = await use_case.execute(request)

    # Assert
    assert response.success
    assert response.aoi is None  # Empty response, not error
```

### Integration Tests

```python
# tests/integration/test_websocket_aoi.py

@pytest.mark.asyncio
async def test_websocket_aoi_flow():
    """Test complete WebSocket AOI flow."""

    # Connect to WebSocket
    async with websockets.connect(WS_URL) as ws:
        # 1. Receive connected message
        msg = await ws.recv()
        data = json.loads(msg)
        assert data["type"] == "connected"

        # 2. Send location
        await ws.send(json.dumps({
            "type": "update_location",
            "lat": 37.906512,
            "lng": -122.544217
        }))

        # 3. Receive AOI
        msg = await ws.recv()
        data = json.loads(msg)
        assert data["type"] == "area_of_interest"
        assert data["zone"]["id"] == "woander_store"
        assert "snapshot_version" in data
        assert "areas" in data
        assert len(data["areas"]["spawn_zone_1"]["items"]) > 0
```

---

## Implementation Phases

### Phase 1: MVP (Week 1) ✅ COMPLETED
**Goal**: Unity receives bottles on connect

- [x] Define `IWorldState` interface (implemented in UnifiedStateManager)
- [x] Extend `UnifiedStateManager` with AOI methods (build_aoi() at line 1228)
- [x] Add `update_location` message handler to WebSocket (line 347)
- [x] Add `area_of_interest` response message (line 402)
- [x] Basic version tracking (timestamp-based, line 1321)
- [x] Integration test for WebSocket flow (tests/manual/test_websocket_experience.py)

**Success Criteria**: ✅ Unity client spawns bottles in woander_store

**Implementation Details**:
- Zone structure: `id`, `name`, `description`, `gps` (lat/lng) - NO geography_id or geofence_radius_m yet
- Areas: `id`, `name`, `description`, `items[]`, `npcs[]` - NO location/accessible_from/ambient yet
- Uses first waypoint from nearby_waypoints list (TODO: handle overlapping zones)

### Phase 2: Geography & Geofencing (Est. 1 week)
**Goal**: Multi-location support with GPS validation

**What Phase 2 Adds:**

1. **Haversine Distance Calculations**
   - Actual GPS proximity filtering (not just first waypoint)
   - `get_nearby_geographies()` with radius checking
   - Distance sorting for disambiguation

2. **Geofence Boundary Detection**
   - Each zone gets `geofence_radius_m` property
   - Server validates player is inside boundary
   - Prevents GPS spoofing/"teleporting"

3. **Zone Entry/Exit Messages**
   ```json
   {
     "type": "area_entered",
     "zone_id": "waypoint_28a",
     "snapshot_version": 12350,
     "area_of_interest": {...}
   }
   ```

4. **Overlapping Zone Disambiguation**
   - Multiple locations within radius → client receives list
   - Shows distance to each
   - Player chooses which to explore

5. **Enhanced Zone Structure**
   ```json
   {
     "zone": {
       "id": "woander_store",
       "geography_id": "mill_valley_wp_28a",
       "gps": {
         "lat": 37.906,
         "lng": -122.544,
         "geofence_radius_m": 50
       }
     }
   }
   ```

**Why Phase 2 Matters:**
- **Current limitation:** Player at GPS (0,0) still gets woander_store AOI
- **Phase 2 fix:** Validates GPS proximity, returns empty AOI if too far
- **Use Cases:** Automatic zone transitions, multi-waypoint parks, fast travel filtering

**Implementation Tasks:**
- [ ] Implement `get_nearby_geographies()` with Haversine distance
- [ ] Add geofence radius checking
- [ ] Handle multiple overlapping geofences (client disambiguation)
- [ ] Add `area_entered` message for location changes
- [ ] Server validates geofence entry
- [ ] Tests for GPS calculations

**Success Criteria**: Player moves between locations, sees different AOIs

**Real-World Example:**
```
Player at Mill Valley Park:
- 30m from "Woander's Shop" (waypoint 28A)
- 45m from "Forest Clearing" (waypoint 29B)
- 80m from "Creek Bridge" (waypoint 30C)

Phase 1: Returns Woander's Shop (first in list)
Phase 2: Returns all 3, sorted by distance
         Unity shows: "3 locations nearby"
         Player taps "Forest Clearing"
```

---

### Phase 3: Event Synchronization (Est. 1 week)
**Goal**: Prevent state desync in multiplayer scenarios

**What Phase 3 Adds:**

1. **Monotonic Version Counters**
   ```python
   # Per-experience version counter
   version_counters["wylding-woods"] = 12345

   # Each state change increments
   version_counters["wylding-woods"] += 1
   ```

   **Why?**
   - Phase 1 timestamps: Clock skew, ambiguous ordering
   - Phase 3 counters: Deterministic, clear causality

2. **Base Version Tracking**
   ```json
   // Initial AOI
   {
     "snapshot_version": 100,
     "zone": {...}
   }

   // Delta update
   {
     "type": "world_update",
     "version": 101,
     "base_version": 100,  // Must match client's snapshot
     "changes": {...}
   }
   ```

3. **Client Buffer Management**
   ```typescript
   if (update.base_version === snapshot_version) {
       applyUpdate(update);
       snapshot_version = update.version;
   } else if (update.base_version > snapshot_version) {
       bufferedUpdates.push(update);  // Out of order
   } else {
       discard(update);  // Outdated
   }
   ```

4. **Resync Mechanism**
   ```json
   // Client detects gap
   {
     "type": "request_resync",
     "last_version": 100
   }

   // Server sends fresh snapshot
   {
     "type": "area_of_interest",
     "snapshot_version": 115,
     "reason": "resync_requested"
   }
   ```

5. **Event-Based Cache Invalidation**
   ```python
   class CachedWorldState:
       async def _handle_world_update(self, nats_msg):
           """Invalidate cache when world changes."""
           experience = nats_msg.data["experience"]
           if experience in self._cache:
               del self._cache[experience]
   ```

**Why Phase 3 Matters:**

**Scenario Without Phase 3:**
- Player A collects bottle → update v101
- Player B collects bottle → update v102
- Network lag → B receives v102 before v101
- Client applies v102 on base v100 → **DESYNC**
- World state now corrupt

**Scenario With Phase 3:**
- Player B receives v102 (base_version=101)
- Client sees: "my version is 100, but this needs 101"
- **Buffers v102** and waits
- v101 arrives → applies both in order
- **State stays consistent**

**Implementation Tasks:**
- [ ] Implement monotonic version counter
- [ ] Add `base_version` to `world_update` events
- [ ] Client buffers out-of-order updates
- [ ] Add resync request mechanism
- [ ] Event-based cache invalidation
- [ ] Tests for version tracking

**Success Criteria**: No desync when multiple players interact

**Real-World Example:**
```
Initial: 5 bottles in shop (version 100)

Player A: collect_bottle_1 at 12:00:00.000
  → version 101, removes bottle_1

Player B: collect_bottle_2 at 12:00:00.005
  → version 102, removes bottle_2

Player C gets updates out of order:
  - Receives v102 first (base=101)
  - Client buffers it
  - Receives v101 (base=100)
  - Client applies v101 → v102 in sequence
  - Final state: 3 bottles remain ✅ CORRECT

Without Phase 3:
  - Applies v102 on base v100
  - Skips v101
  - Final state: 4 bottles (wrong!) ❌
```

---

### Phase Comparison

| Feature | Phase 1 (MVP) | Phase 2 (Geography) | Phase 3 (Sync) |
|---------|---------------|---------------------|----------------|
| **GPS Filtering** | Returns first waypoint | Haversine distance | Same |
| **Geofencing** | No validation | Radius checking | Same |
| **Multi-location** | Single zone only | Overlapping zones | Same |
| **Versioning** | Timestamp (ms) | Timestamp | Monotonic counter |
| **Delta Sync** | No base version | No base version | `base_version` field |
| **Out-of-order** | Breaks state | Breaks state | **Buffers updates** |
| **Resync** | Manual reconnect | Manual reconnect | **Automatic** |
| **Multiplayer** | ⚠️ Desync risk | ⚠️ Desync risk | ✅ **Safe** |

**When Do You Need Each Phase?**

**Ship with Phase 1 if:**
- Single player demo/prototype
- Controlled test locations (no GPS overlap)
- Short play sessions (rare desync)

**Need Phase 2 when:**
- Multiple real-world waypoints
- GPS accuracy matters (urban areas)
- Players can "cheat" by spoofing location

**Need Phase 3 when:**
- 2+ players in same location
- Long play sessions (hours)
- Items respawn or change frequently
- Production reliability required

### Phase 4: Database Migration (Future)
**Goal**: Replace world.json with database

- [ ] Create database schema for entities
- [ ] Implement database repositories
- [ ] Swap adapter without changing use case
- [ ] Migration script: world.json → database
- [ ] Performance benchmarks

**Success Criteria**: Same functionality, better scalability

---

## Open Questions & Risks

### Open Questions

1. **GPS accuracy**: How to handle inaccurate GPS (urban canyons, indoors)?
   - Consider: Last known good location, manual location override

2. **Multi-geofence disambiguation**: How to present choices to user?
   - Consider: Unity UI showing overlapping locations with distance

3. **Offline support**: Should client cache AOI for offline play?
   - Consider: Service worker, IndexedDB for web, local storage for mobile

4. **Version counter persistence**: Where to store monotonic counter?
   - Consider: Redis (fast), PostgreSQL (persistent), or NATS JetStream

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| GPS inaccuracy causes wrong AOI | High | Geofence overlap tolerance, manual selection |
| world.json becomes bottleneck | Medium | Implement caching, migrate to database |
| Version tracking causes desync | High | Comprehensive testing, resync mechanism |
| Template/Instance merge complexity | Medium | Start simple, add complexity as needed |
| Network latency delays AOI delivery | Low | Progressive loading already addresses this |

---

## References

### Documentation
- `docs/scratchpad/CURRENT-STATUS-2025-11-09.md` - Current implementation status
- `docs/scratchpad/waypoint-to-location-architecture-analysis.md` - Waypoint system analysis
- `Vaults/KB/users/jason@aeonia.ai/mmoirl-actual/system/data/20-entity-relationship-model.md` - Entity model
- `Vaults/KB/users/jason@aeonia.ai/mmoirl-actual/incoming/working/spot-registry.md` - Spot registry design

### Skills Used
- `architecture-patterns` (Clean Architecture, Hexagonal Architecture, DDD)
- `api-design-principles` (REST/GraphQL, message design)

### Research
- Perplexity: Pokémon GO location delivery patterns
- Perplexity: Empty response vs error for no location match
- Perplexity: Area-contains-items vs item-has-area structure
- Perplexity: Tick-based synchronization for MMOs

### Key Files
- `/app/services/kb/websocket_experience.py` - WebSocket endpoint
- `/app/services/kb/unified_state_manager.py` - State management
- `/app/services/kb/command_processor.py` - Command processing
- `/app/shared/events.py` - World update events
- `/tests/manual/test_websocket_experience.py` - Manual testing

---

## Next Steps

1. **Review this design** with team
2. **Create GitHub issue** for Phase 1 implementation
3. **Set up branch**: `feature/aoi-delivery`
4. **Implement MVP** (estimated: 3-5 days)
5. **Test with Unity client**
6. **Iterate based on feedback**

**Target Demo Date**: TBD
**Estimated Completion**: Phase 1 by end of week

---

**Last Updated**: 2025-11-10
**Status**: Ready for implementation

---

# APPENDIX

## Appendix A: Current WebSocket Message Format Analysis

*This section documents the existing WebSocket implementation to inform the new AOI design.*

### Message Structure Overview

The GAIA WebSocket implementation uses **JSON-based messages with a `type` field envelope pattern**. All messages follow a common structure with message-type-specific payloads.

### Base Structure
```json
{
  "type": "<message_type>",
  "timestamp": 1234567890000,
  ...type-specific fields...
}
```

**Key Conventions:**
- `type` field is **required** on all messages
- `timestamp` is Unix milliseconds (UTC)
- Invalid JSON or missing `type` triggers error response

---

### Client → Server Messages

#### 1. Action Commands
**File**: `/app/services/kb/websocket_experience.py:175-176`

```json
{
  "type": "action",
  "action": "<action_name>",
  ...action-specific parameters...
}
```

**Examples:**

**Collect Item:**
```json
{
  "type": "action",
  "action": "collect_bottle",
  "item_id": "bottle_of_joy_1",
  "spot_id": "woander_store.shelf_a.slot_1"
}
```

**Generic Collect:**
```json
{
  "type": "action",
  "action": "collect_item",
  "item_id": "<item_id>",
  "location": "<location_id>"
}
```

**Known Actions:**
- `collect_bottle` / `collect_item` - Pick up items from world
- `drop_item` - Drop items from inventory (not implemented)
- `interact_object` - Generic object interaction (not implemented)
- Plus LLM-based actions: `look`, `talk`, `return`, `inventory`, `unknown`

**Processing Flow** (`websocket_experience.py:210-248`):
1. Routes through `ExperienceCommandProcessor.process_command()`
2. Fast path: Registered Python handlers (e.g., `collect_item`)
3. Flexible path: LLM-based command execution via `kb_agent`
4. Returns `CommandResult` standardized response

---

#### 2. Ping (Health Check)
**File**: `/app/services/kb/websocket_experience.py:299-313`

```json
{
  "type": "ping",
  "timestamp": 1730678400000
}
```

**Response:**
```json
{
  "type": "pong",
  "timestamp": 1730678400000
}
```

---

#### 3. Chat (NPC Interaction)
**File**: `/app/services/kb/websocket_experience.py:316-342`

```json
{
  "type": "chat",
  "text": "Hello fairy, how are you?"
}
```

**Note**: Currently returns canned responses. Full LLM integration deferred.

---

### Server → Client Messages

#### 1. Connection Established
**File**: `/app/services/kb/websocket_experience.py:98-105`

```json
{
  "type": "connected",
  "connection_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "a7f4370e-0af5-40eb-bb18-fcc10538b041",
  "experience": "wylding-woods",
  "timestamp": 1730678400000,
  "message": "Connected to wylding-woods experience"
}
```

---

#### 2. Action Response
**File**: `/app/services/kb/websocket_experience.py:237-248`

```json
{
  "type": "action_response",
  "action": "collect_bottle",
  "success": true,
  "message": "You picked up the Bottle of Joy!",
  "timestamp": 1730678400000,
  "metadata": {
    "item_id": "bottle_of_joy_1",
    "item_name": "Bottle of Joy"
  }
}
```

**Based on**: `CommandResult` model (`/app/shared/models/command_result.py`)
- `success`: Boolean indicating success/failure
- `message`: `message_to_player` field from CommandResult
- `metadata`: Optional structured data from CommandResult

---

#### 3. World Update (NATS Event)
**File**: `/app/shared/events.py:11-97`

```json
{
  "type": "world_update",
  "version": "0.3",
  "experience": "wylding-woods",
  "user_id": "a7f4370e-0af5-40eb-bb18-fcc10538b041",
  "changes": {
    "world.locations.woander_store.items": {
      "operation": "remove",
      "item": {
        "id": "bottle_of_joy_3",
        "type": "collectible"
      }
    },
    "player.inventory": {
      "operation": "add",
      "item": {
        "id": "bottle_of_joy_3",
        "type": "collectible",
        "name": "Bottle of Joy"
      }
    }
  },
  "timestamp": 1730678400000,
  "metadata": {
    "source": "kb_service",
    "state_model": "shared"
  }
}
```

**Key Concepts:**
- **State delta pattern** (not full state) - follows Minecraft/WoW approach
- Operations: `add`, `remove`, `update`
- Published to NATS: `world.updates.user.{user_id}`
- Forwarded through WebSocket connection manager

**Publishing** (`/app/services/kb/unified_state_manager.py:269`)

**Forwarding** (`/app/services/kb/experience_connection_manager.py:146-160`)

---

#### 4. Quest Update (Demo/Temporary)
**File**: `/app/services/kb/websocket_experience.py:258-266`

```json
{
  "type": "quest_update",
  "quest_id": "bottle_quest",
  "status": "in_progress",
  "bottles_collected": 3,
  "bottles_total": 7,
  "timestamp": 1730678400000
}
```

**Note**: Hardcoded for demo. Comment says "TODO: This is temporary for the demo. Quest logic should be a proper command."

---

#### 5. Quest Complete
**File**: `/app/services/kb/websocket_experience.py:268-273`

```json
{
  "type": "quest_complete",
  "quest_id": "bottle_quest",
  "message": "Congratulations! You collected all the bottles!",
  "timestamp": 1730678400000
}
```

---

#### 6. NPC Speech
**File**: `/app/services/kb/websocket_experience.py:336-342`

```json
{
  "type": "npc_speech",
  "npc_id": "fairy_guide",
  "text": "Keep collecting those bottles! You're doing great!",
  "voice": "cheerful",
  "timestamp": 1730678400000
}
```

**Note**: Currently canned responses. Full LLM integration pending.

---

#### 7. Error Messages
**File**: `/app/services/kb/websocket_experience.py:345-363`

```json
{
  "type": "error",
  "code": "invalid_json",
  "message": "Message must be valid JSON",
  "timestamp": 1730678400000
}
```

**Error Codes:**
- `invalid_json` - Malformed JSON
- `missing_type` - No `type` field
- `missing_action` - Action message missing `action` field
- `unknown_message_type` - Unrecognized message type
- `processing_error` - Exception during command handling
- `not_implemented` - Feature not yet implemented

---

### WebSocket Architecture

#### Gateway Proxy
**File**: `/app/gateway/main.py:1195-1344`

**Endpoint**: `ws://localhost:8666/ws/experience?token=<jwt>&experience=<exp_id>`

**Flow**:
1. Client connects to Gateway
2. Gateway validates JWT (defense-in-depth)
3. Gateway opens backend connection to KB Service
4. Bidirectional transparent tunneling
5. Connection pooling (max 100 concurrent)

**Close Codes**:
- `1008` - Authentication failed
- `1011` - Internal server error / backend unavailable

---

#### KB Service WebSocket
**File**: `/app/services/kb/websocket_experience.py:47-125`

**Endpoint**: `/ws/experience?token=<jwt>&experience=<exp_id>`

**Flow**:
1. Authenticate JWT via `get_current_user_ws()`
2. Accept WebSocket connection
3. Register with `ExperienceConnectionManager`
4. Create NATS subscription (`world.updates.user.{user_id}`)
5. Enter message handling loop
6. Forward NATS events to client
7. Process client actions
8. Cleanup on disconnect

---

#### Connection Manager
**File**: `/app/services/kb/experience_connection_manager.py:31-285`

**Responsibilities**:
- Track active WebSocket connections
- Create persistent NATS subscriptions per connection
- Forward NATS events to WebSocket clients
- Handle disconnection cleanup

**Key Methods**:
- `connect()` - Accept connection, setup NATS subscription
- `disconnect()` - Cleanup NATS subscription, remove tracking
- `send_message()` - Send message to specific connection

---

### Message Type Summary

| Direction | Type | Purpose | Status |
|-----------|------|---------|--------|
| **Client → Server** |
| | `action` | Execute game actions | ✅ Working |
| | `ping` | Health check | ✅ Working |
| | `chat` | NPC interaction | ⚠️ Canned responses |
| **Server → Client** |
| | `connected` | Connection established | ✅ Working |
| | `action_response` | Action result | ✅ Working |
| | `world_update` | State delta (NATS) | ✅ Working |
| | `quest_update` | Quest progress | ⚠️ Demo only |
| | `quest_complete` | Quest finished | ⚠️ Demo only |
| | `npc_speech` | NPC dialogue | ⚠️ Canned responses |
| | `pong` | Health check response | ✅ Working |
| | `error` | Error notification | ✅ Working |

---

### Key Implementation Files

| Component | File Path | Lines |
|-----------|-----------|-------|
| **Gateway Proxy** | `/app/gateway/main.py` | 1195-1344 |
| **KB WebSocket Endpoint** | `/app/services/kb/websocket_experience.py` | 47-364 |
| **Connection Manager** | `/app/services/kb/experience_connection_manager.py` | 31-285 |
| **Command Processor** | `/app/services/kb/command_processor.py` | 10-46 |
| **World Update Event** | `/app/shared/events.py` | 11-97 |
| **Command Result Model** | `/app/shared/models/command_result.py` | 6-14 |
| **Manual Test** | `/tests/manual/test_websocket_experience.py` | 1-253 |

---

## Appendix B: Current WebSocket Content Payloads Analysis

*This section analyzes what data is currently sent (or not sent) in WebSocket messages.*

### 1. Welcome/Connected Message
**Location**: `/app/services/kb/websocket_experience.py:98-105`

**Current Payload**:
```json
{
    "type": "connected",
    "connection_id": "uuid-string",
    "user_id": "uuid-string",
    "experience": "wylding-woods",
    "timestamp": 1699564123000,
    "message": "Connected to wylding-woods experience"
}
```

**What's Included**: Connection metadata only

**What's Missing**:
- ❌ Player state (location, inventory)
- ❌ World state (nearby items, NPCs)
- ❌ Area of Interest data

**Gap for AOI Implementation**: This is the primary gap. Welcome message needs to include or be followed by AOI data.

---

### 2. Action Response Messages
**Location**: `/app/services/kb/websocket_experience.py:237-247`

**Current Payload**:
```json
{
    "type": "action_response",
    "action": "collect_item",
    "success": true,
    "message": "You have collected dream_bottle_1",
    "timestamp": 1699564123000,
    "metadata": {
        // Optional: handler-specific data from CommandResult.metadata
    }
}
```

**What's Included**:
- Success/failure status
- Player-facing message
- Optional metadata dictionary

**What's NOT Included**:
- State changes are NOT sent in action_response
- State changes go to separate `WorldUpdateEvent` via NATS (but Unity doesn't subscribe yet)

---

### 3. Quest Update Messages
**Location**: `/app/services/kb/websocket_experience.py:258-265`

**Current Payload** (Demo-only, hardcoded):
```json
{
    "type": "quest_update",
    "quest_id": "bottle_quest",
    "status": "in_progress",
    "bottles_collected": 3,
    "bottles_total": 7,
    "timestamp": 1699564123000
}
```

**Triggered After**: Successful `collect_item` action only

**Note**: This is temporary demo code - quest logic should be a proper command

---

### 4. World State Updates (NATS-based)
**Location**: `/app/shared/events.py:11-96`

**Schema** (NATS pub/sub, forwarded via WebSocket):
```json
{
    "type": "world_update",
    "version": "0.3",
    "experience": "wylding-woods",
    "user_id": "uuid-string",
    "changes": {
        "player.inventory": {
            "operation": "add",
            "item": {
                "id": "dream_bottle_3",
                "type": "collectible",
                "collected_at": "2025-11-09T12:34:56Z"
            }
        }
    },
    "timestamp": 1699564123000,
    "metadata": {
        "source": "kb_service",
        "state_model": "shared"
    }
}
```

**Published to**: `world.updates.user.{user_id}` NATS subject
**Published by**: `UnifiedStateManager.update_player_view()` (`/app/services/kb/unified_state_manager.py:713`)

**Current Flow**: KB Service → NATS → ExperienceConnectionManager → WebSocket client

---

### 5. Player View Structure
**Location**: `/app/services/kb/unified_state_manager.py:647-680`

**Available via `get_player_view()` but NOT sent on connection**:
```json
{
    "player": {
        "current_location": "woander_store",
        "current_sublocation": null,
        "inventory": [
            {
                "id": "dream_bottle_1",
                "type": "collectible",
                "collected_at": "2025-11-09T12:34:56Z"
            }
        ]
    }
}
```

**Gap**: This data exists but is not included in welcome message.

---

### Current Gaps for AOI Implementation

#### Gap 1: Welcome Message Missing World State
**File**: `/app/services/kb/websocket_experience.py:98-105`

**What's Missing**:
```json
{
    "type": "connected",
    // ✅ HAVE: connection_id, user_id, experience, timestamp
    // ❌ MISSING: Below fields needed for AOI
    "player": {
        "current_location": "woander_store",
        "inventory": []
    },
    "area_of_interest": {
        "location_id": "woander_store",
        "name": "Woander's Magical Shop",
        "sublocations": {
            "spawn_zone_1": {
                "items": [
                    {
                        "id": "dream_bottle_1",
                        "type": "dream_bottle",
                        "collectible": true,
                        "state": {
                            "dream_type": "peaceful",
                            "symbol": "spiral"
                        }
                    }
                ]
            }
        },
        "npcs": {
            "woander": { /* NPC data */ }
        }
    }
}
```

**Solution**: Call `state_manager.get_player_view()` and `state_manager.get_world_state()` in welcome message handler OR implement progressive loading pattern with separate `update_location` → `area_of_interest` flow.

---

#### Gap 2: No Progressive Loading Mechanism
**What's Missing**: No message type for sending new area data when player moves

**Needed Message Type** (not implemented):
```json
{
    "type": "location_entered",
    "location_id": "waypoint_28a",
    "area_of_interest": {
        // New location data
    }
}
```

**Trigger**: When player performs `move` action or GPS detects proximity

---

#### Gap 3: No Comprehensive State Retrieval Action
**Missing**: Client-initiated action to request world state

**Needed** (for debugging/recovery):
```json
// Client request
{
    "type": "action",
    "action": "get_area",
    "location_id": "woander_store"
}

// Server response
{
    "type": "area_data",
    "area_of_interest": { /* ... */ }
}
```

---

### Data Available (But Not Sent)

**From UnifiedStateManager:**
- ✅ `get_player_view()` - Player location, inventory, progress
- ✅ `get_world_state()` - All locations, items, NPCs
- ✅ World update deltas published to NATS

**From KB Content:**
- ✅ Location metadata (name, description, sublocations)
- ✅ Item metadata (type, collectible status, visual properties)
- ✅ NPC data (name, location, dialogue)

---

### Summary: What Works vs What's Missing

**✅ What Works:**
1. WebSocket connection and authentication
2. Action processing (collect_item via fast path)
3. Action response messages with success/failure
4. Quest progress tracking (demo-only)
5. NATS publishing of state changes
6. NATS forwarding to WebSocket clients

**❌ What's Missing:**
1. **Welcome message doesn't include world state** - Unity can't spawn bottles
2. **No progressive loading** - Can't send new areas as player moves
3. **No client-initiated state queries** - Can't recover from missed messages

**🎯 Priority for AOI:**
- **Highest**: Gap 1 (welcome message or separate AOI flow)
- **Medium**: Gap 2 (progressive loading with location updates)
- **Lower**: Gap 3 (state query actions)

---

**Analysis completed**: Current WebSocket implementation provides connection infrastructure and action protocol, but missing world state discovery needed for Area of Interest pattern. All required data exists in UnifiedStateManager - needs to be delivered via new message flow.

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

The core architectural and implementation claims in this document have been verified against the source code.

-   **✅ Problem Statement (Section "Problem Statement" of this document):**
    *   **Claim:** Unity AR client connects via WebSocket but receives no world state data, preventing item spawning.
    *   **Verification:** Confirmed that the initial `connected` message in `app/services/kb/websocket_experience.py` (lines 98-105) only sends connection metadata, not world state, aligning with the problem described.

-   **✅ Adapter Pattern Strategy (Section "Adapter Pattern Strategy" of this document):**
    *   **Claim:** The `UnifiedStateManager` is extended to act as an adapter for `IWorldState`.
    *   **Code Reference:** `app/services/kb/unified_state_manager.py` (lines 1226-1400, specifically the `build_aoi` method and the `IWorldState` interface implementation).
    *   **Verification:** Confirmed that `UnifiedStateManager` now contains methods like `get_zone_by_geography`, `get_instances_at_zone`, `get_template`, and `get_nearby_geographies` (even if `get_nearby_geographies` is a placeholder), which serve as the adapter layer. The `build_aoi` method orchestrates the construction of the AOI payload.

-   **✅ WebSocket Message Flow Design (Section "WebSocket Message Flow Design" of this document):**
    *   **Claim:** The `update_location` message triggers an `area_of_interest` response.
    *   **Code Reference:** `app/services/kb/websocket_experience.py` (lines 347-402).
    *   **Verification:** Confirmed the `update_location` message handler, the call to `GetAreaOfInterestUseCase.execute`, and the subsequent sending of the `area_of_interest` message to the client.

-   **✅ Area of Interest Payload Structure (Section "Area of Interest Payload Structure" of this document):**
    *   **Claim:** The AOI payload includes `zone`, `areas` (containing `items` and `npcs`), and `player` state, with template and instance data merged.
    *   **Code Reference:** `app/services/kb/unified_state_manager.py` (lines 1321-1390, specifically the `_build_aoi` method).
    *   **Verification:** Confirmed that the `_build_aoi` method constructs a dictionary matching the described schema, including the merging of template properties into instance data.

-   **✅ Version Tracking & Synchronization (Section "Version Tracking & Synchronization" of this document):**
    *   **Claim:** Snapshot versioning is implemented (initially timestamp-based).
    *   **Code Reference:** `app/services/kb/unified_state_manager.py` (lines 1392-1396, specifically the `_get_current_version` method).
    *   **Verification:** Confirmed that `_get_current_version` returns a timestamp-based integer, aligning with the Phase 1 MVP strategy.

-   **✅ Discrepancy: `initial_state` message:**
    *   **Claim (from `websocket-aoi-client-guide.md`):** An `initial_state` message is sent on connection.
    *   **Verification:** This message type was *not* found in `app/services/kb/websocket_experience.py`. The `connected` message is sent, followed by an `area_of_interest` message only after the client sends an `update_location` message. This confirms the discrepancy noted in the `state_snapshot`.

**Conclusion:** The implementation of the Area of Interest (AOI) pattern is largely consistent with the design described in this document, with the noted minor discrepancy regarding the `initial_state` message. The document accurately reflects the MVP phase of AOI delivery.
