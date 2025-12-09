# Visibility Toggle System - Phase 1 Implementation

**Status**: ✅ Complete
**Date**: 2025-11-13
**Purpose**: Enable items to be hidden/shown dynamically through gameplay events (quest acceptance, triggers, etc.)

---

## Overview

The visibility toggle system allows items in `world.json` to start as `visible: false` and become `visible: true` when triggered by game events. This enables:
- Quest-driven item spawning (items appear when quest accepted)
- Progressive world reveal (areas unlock as story progresses)
- Dynamic content (items spawn based on time, conditions, player actions)

**Key Design Principle**: Visibility toggle is a **generic infrastructure** - it's not tied to quests. Any game system can use it (quests, admin commands, timed events, etc.).

---

## Phase 1: What We Built

### 1. World State: Items with Visibility Flag

**File**: `/kb/experiences/wylding-woods/state/world.json`

Items can now have `visible: false`:

```json
{
  "locations": {
    "woander_store": {
      "areas": {
        "spawn_zone_1": {
          "items": [
            {
              "instance_id": "dream_bottle_1",
              "template_id": "dream_bottle",
              "semantic_name": "mysterious dream bottle",
              "collectible": true,
              "visible": false,  // ← Hidden initially
              "state": {
                "glowing": true,
                "dream_type": "mysterious"
              }
            }
          ]
        }
      }
    }
  }
}
```

**Behavior**:
- `visible: false` → Item exists in world state but NOT sent in AOI messages
- `visible: true` → Item included in AOI, Unity spawns it in AR
- Default: `visible: true` if field missing (backward compatible)

---

### 2. Visibility Toggle Handler

**File**: `app/services/kb/handlers/accept_quest.py`

Fast-path command handler that toggles item visibility:

```python
async def handle_accept_quest(user_id, experience_id, command_data):
    """
    Toggles visibility of quest-related items from false → true.

    Example: Player accepts "dream_bottle_recovery" quest
    → dream_bottle_1-4 become visible
    → Unity receives WorldUpdate event
    → Bottles spawn in AR scene
    """

    # Get quest config
    quest_config = QUEST_VISIBILITY_MAP.get(quest_id)
    items_to_show = quest_config["items_to_show"]  # ["dream_bottle_1", ...]

    # Build visibility updates
    world_updates = await _build_visibility_updates(
        world_state,
        items_to_show,
        visible=True
    )

    # Publish WorldUpdate event (triggers AOI rebuild)
    await state_manager.update_world_state(
        experience=experience_id,
        updates=world_updates,
        user_id=user_id
    )
```

**Quest-to-Items Mapping**:

```python
QUEST_VISIBILITY_MAP = {
    "dream_bottle_recovery": {
        "items_to_show": [
            "dream_bottle_1",
            "dream_bottle_2",
            "dream_bottle_3",
            "dream_bottle_4"
        ],
        "required_npc": "louisa",
        "min_trust_level": 60
    }
}
```

**Important**: This mapping is **temporary** - it's hardcoded for MVP. Future phases will load quest config from markdown templates.

---

### 3. AOI Builder Integration

**File**: `app/services/kb/unified_state_manager.py:build_aoi()`

AOI builder already filters by `visible` field:

```python
def build_aoi(self, world_state, player_location):
    """Build Area of Interest message for Unity."""

    for area in location["areas"].values():
        for item in area["items"]:
            # Only include visible items
            if item.get("visible", True):  # Default true for backward compat
                aoi_items.append(item)

    return {"type": "area_of_interest", "areas": aoi_areas}
```

**No changes needed** - visibility filtering already works!

---

## How It Works: Complete Flow

```
1. WORLD INITIALIZATION
   world.json: dream_bottle_1-4 have visible: false
   → AOI builder filters them out
   → Unity receives AOI with 0 dream bottles
   → Player sees empty shop

2. QUEST ACCEPTANCE
   Player: "accept quest dream_bottle_recovery"
   → accept_quest handler updates world state:
     {
       "locations": {
         "woander_store": {
           "areas": {
             "spawn_zone_1": {
               "items": {
                 "$update": [
                   {"instance_id": "dream_bottle_1", "visible": true}
                 ]
               }
             }
           }
         }
       }
     }
   → Publishes WorldUpdate event

3. AOI REBUILD (v0.4 protocol)
   → KB Service receives WorldUpdate event
   → Rebuilds AOI with newly visible items
   → Sends area_of_interest message to Unity

4. UNITY SPAWNING
   → Unity receives AOI with 4 dream bottles
   → Spawns bottles at spawn_zone_1-4 locations
   → Player sees glowing bottles appear in AR
```

---

## Files Changed

### New Files

| File | Purpose |
|------|---------|
| `app/services/kb/handlers/accept_quest.py` | Visibility toggle handler (Phase 1 MVP) |
| `docs/scratchpad/visibility-toggle-system-implementation.md` | This document |
| `docs/scratchpad/quest-driven-dynamic-spawning-system.md` | Future phases design |

### Modified Files

| File | Changes |
|------|---------|
| `world.json` | Set dream_bottle_1-4 `visible: false` |
| `templates/quests/dream_bottle_recovery.md` | Updated quest flow to use "give to Louisa" |
| `give_item.py` | Kept simple (reverted quest logic) |

---

## Testing the System

### Manual Test

```bash
# 1. Start server
docker compose up

# 2. Connect Unity client, update GPS to Woander's Store location
# Expect: No dream bottles visible

# 3. Accept quest via WebSocket or HTTP
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "experience": "wylding-woods",
    "command": "accept quest dream_bottle_recovery"
  }'

# 4. Check Unity client
# Expect: 4 dream bottles spawn in AR scene
```

### Integration Test (Future)

```python
async def test_visibility_toggle():
    """Test dream bottle visibility toggle on quest acceptance."""

    # Initially invisible
    aoi = await build_aoi(user_id, "woander_store")
    assert "dream_bottle_1" not in get_item_ids(aoi)

    # Accept quest
    await handle_accept_quest(user_id, "wylding-woods", {
        "quest_id": "dream_bottle_recovery"
    })

    # Now visible
    aoi = await build_aoi(user_id, "woander_store")
    assert "dream_bottle_1" in get_item_ids(aoi)
    assert "dream_bottle_2" in get_item_ids(aoi)
    assert len(get_item_ids(aoi)) == 4
```

---

## Design Decisions

### Why NOT Put Logic in give_item.py?

**User Feedback**: "give should not be the container for quests or evaluate when quests are done"

**Decision**: Keep `give` command pure and simple:
- ✅ Transfer item from player to NPC
- ✅ Validate proximity
- ❌ NO quest tracking
- ❌ NO reward distribution
- ❌ NO progress counting

Quest completion will be handled by future quest system (Phase 2-4).

### Why Separate visibility_toggle from Quests?

Visibility toggle is **generic infrastructure** that can be used by:
- Quests (Phase 2)
- Admin commands (`@spawn-items`, `@hide-items`)
- Timed events (items appear at certain times)
- Story triggers (items unlock when player learns information)
- Environmental conditions (items spawn during rain, night, etc.)

Making it generic now prevents tight coupling to quest system.

---

## Limitations & Future Work

### Phase 1 Limitations

1. **Hardcoded Quest Mapping**: `QUEST_VISIBILITY_MAP` is hardcoded in Python
   - **Future**: Load from quest template markdown files

2. **No Quest Progress Tracking**: Quest system not implemented
   - **Future**: Separate quest service tracks objectives, rewards

3. **No Visibility Conditions**: Can't express "show if trust > 50"
   - **Future**: Declarative spawn_conditions (Phase 2)

4. **Per-Player State**: All players see same visibility
   - **Future**: Per-player visibility based on quest state (Phase 3)

5. **No Visibility Hiding**: Can only toggle false → true
   - **Future**: Bidirectional toggle, timed visibility, respawning

---

## What's Next?

See `quest-driven-dynamic-spawning-system.md` for:
- **Phase 2**: Spawn conditions (`spawn_conditions` field with declarative rules)
- **Phase 3**: Advanced conditions (trust, time, quest chains)
- **Phase 4**: Dynamic spawning (runtime item creation, randomization)
- **Phase 5**: Quest system integration (progress tracking, rewards, completion)

---

## Key Takeaways

✅ **Phase 1 Complete**: Visibility toggle infrastructure working
✅ **Generic Design**: Not tied to quests, usable by any system
✅ **Clean Separation**: Commands stay focused, quest logic separate
✅ **Unity Ready**: No Unity changes needed, works with existing AOI system
✅ **Backward Compatible**: Items default to `visible: true`

**Next Step**: Design and implement quest tracking system separately from visibility toggle.
