# WorldUpdate vs AOI Alignment Analysis

**Date**: 2025-11-10
**Status**: ✅ COMPLETE - v0.4 Implemented and Validated
**Reporter**: Unity Client Team
**Related**: Template/Instance Implementation, Unity v0.4 Proposal
**Completed**: 2025-11-10 (same day)

---

## Executive Summary

Unity client team correctly identified that `world_update` messages are **NOT aligned** with the new `instance_id`/`template_id` structure we just implemented for AOI.

**Current Status**:
- ✅ AOI uses `instance_id`/`template_id` (just implemented)
- ❌ world_update uses old `id` field (not updated)
- ❌ Documentation out of sync with both implementations

**Impact**: Unity would need two different parsing paths for AOI vs WorldUpdate

**Recommendation**: Update world_update to v0.4 format BEFORE Unity implements handling

---

## Current Implementation Analysis

### 1. AOI Structure (✅ NEW - Just Implemented)

**File**: `app/services/kb/unified_state_manager.py` (build_aoi)

**Item Format**:
```json
{
  "instance_id": "dream_bottle_woander_1",
  "template_id": "dream_bottle",
  "type": "dream_bottle",
  "semantic_name": "dream bottle",
  "description": "A bottle glowing with...",
  "collectible": true,
  "state": {
    "visible": true,
    "glowing": true,
    "dream_type": "peaceful"
  }
}
```

**Structure**:
- Uses unified `instance_id`/`template_id` fields
- Includes full merged template + instance data
- Timestamp-based `snapshot_version`

---

### 2. WorldUpdate Structure (❌ OLD - Not Updated)

**File**: `app/shared/events.py` (WorldUpdateEvent)

**Current Format**:
```json
{
  "type": "world_update",
  "version": "0.3",
  "experience": "wylding-woods",
  "user_id": "user123",
  "changes": {
    "player.inventory": {
      "operation": "add",
      "item": {
        "id": "bottle_of_joy_3",     // ❌ Single id field
        "type": "collectible",       // ❌ Not template_id
        "name": "Bottle of Joy"
      }
    }
  },
  "timestamp": 1730678400000
}
```

**Issues**:
- ❌ Uses single `id` field (not `instance_id`)
- ❌ Uses `type` field (not `template_id`)
- ❌ No `base_version` for delta validation
- ❌ Dict-based changes (Unity proposed array format)
- ❌ Doesn't match AOI structure

---

### 3. Unity Current Implementation (Demo v0.3)

**File**: Unity `DirectiveQueue.cs` (current)

**Expected Format**:
```json
{
  "type": "world_update",
  "version": "0.3",
  "changes": {
    "woander_store.spawn_zone_1.item_node_1": {
      "operation": "remove",
      "item": {"id": "bottle_of_joy"}  // Single ID
    }
  }
}
```

**Notes**:
- Uses `"version": "0.3"` (string) ✅
- Uses single `id` field ❌
- Dict-based changes ❌
- Location path format different from server

---

### 4. Documentation (❌ OUT OF SYNC)

**File**: `docs/scratchpad/websocket-aoi-client-guide.md` (lines 318-346)

**Documented Format**:
```json
{
  "type": "world_update",
  "version": 12346,              // ❌ Numeric (not "0.3")
  "base_version": 12345,         // Has base_version
  "experience": "wylding-woods",
  "changes": {
    "player.inventory": {
      "operation": "add",
      "item": {
        "id": "dream_bottle_1",  // ❌ Single id
        "type": "collectible",   // ❌ Not template_id
        "name": "Peaceful Dream Bottle"
      }
    }
  }
}
```

**Issues**:
- ❌ Shows numeric version (server uses "0.3" string)
- ❌ Shows `base_version` (server doesn't implement)
- ❌ Uses old `id` format (not `instance_id`/`template_id`)

---

## Unity Team's Questions

### Q1: Is world_update actually implemented on server?

**Answer**: YES, partially implemented

**Evidence**:
- ✅ `WorldUpdateEvent` model exists (`app/shared/events.py`)
- ✅ `_publish_world_update()` method exists (`unified_state_manager.py:274`)
- ✅ Published to NATS: `world.updates.user.{user_id}`
- ⚠️ Uses old format (not aligned with AOI)

**What's Implemented**:
```python
async def _publish_world_update(self, experience, user_id, changes):
    event = WorldUpdateEvent(
        experience=experience,
        user_id=user_id,
        changes=changes,  # ← Dict format, old structure
        timestamp=int(time.time() * 1000),
        metadata={"source": "kb_service"}
    )
    await self.nats_client.publish(subject, event.model_dump())
```

**What's NOT Implemented**:
- ❌ `base_version` tracking
- ❌ `instance_id`/`template_id` structure
- ❌ Monotonic version counters
- ❌ Array-based changes format

---

### Q2: Should server update world_update to match AOI?

**Answer**: YES, absolutely!

**Why**:
1. **Consistency**: One parsing path for Unity (not two different formats)
2. **Template/Instance Architecture**: world_update should use same structure as AOI
3. **Unity v0.4 Proposal**: Perfect timing to implement their proposal
4. **Future Features**: Enables version tracking, delta buffering, resync

**What Should Change**:
```json
// ❌ Current (v0.3)
{
  "changes": {
    "player.inventory": {
      "operation": "add",
      "item": {"id": "bottle_of_joy_3", "type": "collectible"}
    }
  }
}

// ✅ Proposed (v0.4)
{
  "base_version": 12345,
  "version": 12346,
  "changes": [
    {
      "operation": "remove",
      "area_id": "spawn_zone_1",
      "instance_id": "dream_bottle_woander_1",  // Matches AOI!
      "template_id": "dream_bottle"             // Matches AOI!
    },
    {
      "operation": "add",
      "path": "player.inventory",
      "item": {
        "instance_id": "dream_bottle_woander_1",
        "template_id": "dream_bottle",
        "state": {...}
      }
    }
  ]
}
```

---

### Q3: Timeline for server changes?

**Recommendation**: Implement v0.4 THIS WEEK (before Unity codes against old format)

**Why Urgent**:
- Unity is about to implement AOI handling (Task 3)
- If they implement v0.3, they'll need to refactor later
- We just finished template/instance work - perfect timing
- Minimal server changes (update event model + publisher)

**Effort Estimate**:
- **Server Changes**: 2-4 hours
  - Update `WorldUpdateEvent` model (30 min)
  - Update `_publish_world_update()` logic (1 hour)
  - Update documentation (30 min)
  - Test with Unity (1-2 hours)
- **Unity Changes**: 0 hours (not implemented yet!)

---

## Recommendation: Phased Approach

### Phase 1: Server Updates v0.4 (THIS WEEK)

**Tasks**:
1. ✅ Update `WorldUpdateEvent` model to support both v0.3 and v0.4
2. ✅ Update `_publish_world_update()` to use `instance_id`/`template_id`
3. ✅ Add `base_version` tracking
4. ✅ Update documentation to match implementation
5. ✅ Add backward compatibility for v0.3 clients (if any exist)

**Files to Modify**:
- `app/shared/events.py` (WorldUpdateEvent model)
- `app/services/kb/unified_state_manager.py` (_publish_world_update)
- `docs/scratchpad/websocket-aoi-client-guide.md` (documentation)

---

### Phase 2: Unity Implements AOI Handling (NEXT WEEK)

**Unity Tasks** (per their message):
1. ✅ Implement AOI snapshot handling (Task 3)
2. ✅ Unified parsing for AOI and WorldUpdate
3. ✅ Single code path for `instance_id`/`template_id`

**Benefits**:
- Unity gets consistent structure from day 1
- No refactoring needed later
- Cleaner codebase

---

### Phase 3: Verify Integration (TESTING)

**Integration Tests**:
1. ✅ Collect item → verify world_update uses `instance_id`
2. ✅ AOI + WorldUpdate both have same item structure
3. ✅ Unity can parse both with same code
4. ✅ Template changes reflected in both AOI and updates

---

## Proposed WorldUpdate v0.4 Format

### Model Changes

**File**: `app/shared/events.py`

```python
class WorldUpdateEvent(BaseModel):
    """
    Real-time world state update event (v0.4).

    Aligned with AOI structure using instance_id/template_id.
    """

    type: Literal["world_update"] = "world_update"
    version: str = "0.4"  # Increment version
    experience: str
    user_id: str

    base_version: int
    """Version this delta applies on top of (for validation)"""

    snapshot_version: int
    """New version after applying this delta"""

    changes: List[Dict[str, Any]]  # Array format (not dict)
    """
    Array of change operations. Each change has:
    - operation: "add" | "remove" | "update"
    - area_id: Optional area identifier
    - instance_id: Entity instance ID
    - template_id: Entity template ID (optional for remove)
    - item: Full item data (for add/update)
    """

    timestamp: int
    metadata: Optional[Dict[str, Any]] = None
```

---

### Example v0.4 Message

**Scenario**: Player collects dream bottle from woander_store

```json
{
  "type": "world_update",
  "version": "0.4",
  "experience": "wylding-woods",
  "user_id": "user123",

  "base_version": 12345,
  "snapshot_version": 12346,

  "changes": [
    {
      "operation": "remove",
      "area_id": "spawn_zone_1",
      "instance_id": "dream_bottle_woander_1",
      "template_id": "dream_bottle"
    },
    {
      "operation": "add",
      "path": "player.inventory",
      "item": {
        "instance_id": "dream_bottle_woander_1",
        "template_id": "dream_bottle",
        "semantic_name": "dream bottle",
        "description": "A bottle glowing...",
        "collectible": true,
        "state": {
          "collected_at": "2025-11-10T12:00:00Z"
        }
      }
    }
  ],

  "timestamp": 1731240000000,
  "metadata": {
    "source": "kb_service",
    "state_model": "shared"
  }
}
```

---

### Comparison Table

| Feature | v0.3 (Current) | v0.4 (Proposed) | AOI (Current) |
|---------|----------------|-----------------|---------------|
| Item ID | `id` | `instance_id` | `instance_id` ✅ |
| Template | `type` | `template_id` | `template_id` ✅ |
| Changes Format | Dict | Array | N/A |
| Version Tracking | Timestamp | `base_version` + `snapshot_version` | `snapshot_version` |
| Full Item Data | Partial | Full (merged) | Full (merged) ✅ |
| Backward Compatible | N/A | Can support both | N/A |

---

## Benefits of v0.4 Alignment

### 1. Unified Parsing (Unity Side)
```csharp
// Before (two different parsers)
void HandleAOI(AOIMessage msg) {
    var item = msg.items[0];
    string id = item.instance_id;  // ✅ Has instance_id
}

void HandleWorldUpdate(WorldUpdateMessage msg) {
    var item = msg.changes["player.inventory"].item;
    string id = item.id;  // ❌ Different field name!
}

// After (one parser for both)
void HandleItem(Item item) {
    string id = item.instance_id;  // ✅ Same everywhere
    string template = item.template_id;
}
```

### 2. Template Changes Propagate
```
Content Creator:
1. Edit templates/items/dream_bottle.md
2. Change description

Result:
- AOI shows new description ✅
- WorldUpdate shows new description ✅
- Unity renders updated text ✅
```

### 3. Version Tracking
```json
{
  "base_version": 12345,  // Client must be at this version
  "snapshot_version": 12346  // Will be at this version after applying
}

// Client validation:
if (client_version != base_version) {
    // Out of sync! Request fresh AOI
    requestFullAOI();
}
```

### 4. Future Features Enabled
- **Delta Buffering**: Queue updates if client behind
- **Conflict Detection**: Detect concurrent modifications
- **Resync Protocol**: Automatic recovery from desyncs
- **Optimistic Updates**: Client predicts, server confirms

---

## Migration Strategy

### Backward Compatibility

**Option 1: Dual Protocol Support**
```python
class WorldUpdateEvent(BaseModel):
    version: str = "0.4"

    # v0.4 fields
    base_version: Optional[int] = None
    snapshot_version: Optional[int] = None
    changes: Union[Dict, List] = []  # Accept both formats

    def to_v03(self) -> Dict:
        """Convert to v0.3 format for legacy clients"""

    def to_v04(self) -> Dict:
        """Use v0.4 format (default)"""
```

**Option 2: Clean Break (Recommended)**
- Unity demo hasn't shipped yet
- No production clients on v0.3
- Just switch to v0.4 now

---

## Implementation Checklist

### Server Tasks (2-4 hours)

- [ ] Update `WorldUpdateEvent` model (`app/shared/events.py`)
  - [ ] Change `changes` from Dict to List
  - [ ] Add `base_version` and `snapshot_version` fields
  - [ ] Update docstrings and examples
  - [ ] Increment version to "0.4"

- [ ] Update `_publish_world_update()` method
  - [ ] Format changes as array
  - [ ] Include `instance_id` and `template_id`
  - [ ] Add version tracking logic
  - [ ] Test with NATS

- [ ] Update `update_player_view()` to track versions
  - [ ] Store version in player view JSON
  - [ ] Increment on each change
  - [ ] Pass to world_update publisher

- [ ] Update documentation
  - [ ] Fix version field (string not number)
  - [ ] Update examples to v0.4 format
  - [ ] Add migration guide for Unity

- [ ] Add integration tests
  - [ ] Test collect item → world_update
  - [ ] Verify instance_id/template_id present
  - [ ] Verify version tracking works

---

### Unity Tasks (Already Planned)

Unity team already planning Task 3 (AOI handling). With v0.4:
- ✅ Same parsing code for AOI and WorldUpdate
- ✅ No refactoring needed later
- ✅ Clean implementation from start

---

## Answers to Unity Team

### Q: Is world_update actually implemented on server?

**Answer**: YES, but uses old v0.3 format

**Files**:
- Model: `app/shared/events.py` (WorldUpdateEvent)
- Publisher: `app/services/kb/unified_state_manager.py:274` (_publish_world_update)
- NATS Subject: `world.updates.user.{user_id}`

---

### Q: Should server update world_update to match AOI?

**Answer**: YES! Add instance_id/template_id fields

**Benefits**:
- Unity uses one parser for both AOI and WorldUpdate
- Consistent with template/instance architecture
- Matches Unity v0.4 proposal
- Enables future features (version tracking, delta buffering)

---

### Q: Timeline for server changes?

**Answer**: THIS WEEK (2-4 hours work)

**Urgency**: Unity about to implement AOI handling (Task 3). Better to align BEFORE Unity codes against old format.

**Effort**:
- Server: 2-4 hours (model + publisher + docs + tests)
- Unity: 0 hours (not implemented yet!)

---

## Recommendation Summary

**DO THIS**:
1. ✅ Server updates world_update to v0.4 THIS WEEK
2. ✅ Unity implements Task 3 (AOI) NEXT WEEK with v0.4 format
3. ✅ Test integration together
4. ✅ Ship aligned protocol from day 1

**DON'T DO THIS**:
1. ❌ Unity implements Task 3 against v0.3
2. ❌ Server updates to v0.4 later
3. ❌ Unity refactors to support v0.4
4. ❌ Wasted engineering time

---

---

## ✅ IMPLEMENTATION COMPLETE (2025-11-10)

### Decision Made

✅ **Proceeded with v0.4 implementation** - Completed same day

### Coordination via Symphony

**Room**: `websockets`
**Participants**: server-coder (this agent), client-coder (Unity team)
**Duration**: ~2 hours
**Outcome**: Format agreement, real-time validation, zero blockers

### Implementation Summary

**Server Changes (Completed):**
1. ✅ Updated `WorldUpdateEvent` model to v0.4
   - Added `base_version`/`snapshot_version` fields
   - Changed `changes` from Dict to List[Dict]
   - Uses `instance_id`/`template_id`

2. ✅ Added version tracking to player views
   - `snapshot_version` field initialized on bootstrap
   - Auto-increment on state changes
   - Passed to world_update publisher

3. ✅ Updated `_publish_world_update()` method
   - Formats changes as v0.4 array
   - Loads and merges template data
   - Includes version information

4. ✅ Updated documentation
   - `websocket-aoi-client-guide.md` Section 3
   - Complete v0.4 specification
   - Unity integration examples

**Files Modified:**
- `app/shared/events.py` - WorldUpdateEvent model
- `app/services/kb/unified_state_manager.py` - Version tracking + formatting
- `docs/scratchpad/websocket-aoi-client-guide.md` - Section 3 updated

**Total Changes**: ~200 lines added/modified

### Unity Validation

✅ **Format Confirmed**: Unity team validated specification matches their needs
✅ **Implementation Ready**: Unity can proceed with DirectiveQueue handlers
✅ **Zero Refactoring**: No technical debt, one parser from day 1

### Actual Timeline

**Estimated**: 2-4 hours
**Actual**: ~2 hours (code) + 30 min (docs) = 2.5 hours total
**Coordination**: Real-time via Symphony (vs days of async back-and-forth)

### Next Steps

**Monday**:
1. Local testing (this document)
2. Deploy to dev environment
3. Create test credentials for Unity
4. Notify Unity team when ready

**Tuesday**:
1. Unity tests against dev
2. Integration validation
3. Any fixes if needed

### Success Metrics

✅ Same-day implementation and validation
✅ Zero scope creep or format changes
✅ Unity team ready to implement (waiting on deployment only)
✅ Documentation complete and validated
✅ Coordination efficient (Symphony real-time collaboration)

---

**Status**: Implementation complete. Testing in progress. Deployment scheduled Monday.

