# Unity Bottle Display Fix - Session Notes
**Date:** 2025-11-13
**Branch:** `feature/unified-experience-system`

## Problem Summary

Unity client was unable to receive bottles from the server, showing error:
```
❌ WebSocketExperienceClient: Server error - 'str' object has no attribute 'get' (code: processing_error)
```

## Root Cause

**Critical Bug in `build_aoi()` (unified_state_manager.py:1437)**

The `build_aoi()` method expected items to be dictionaries:
```python
instance_id = item_instance.get("instance_id")  # Fails if item_instance is a string
```

But world.json stored items as **strings**:
```json
"items": ["bottle_joy", "bottle_mystery"]  // Array of strings, not objects
```

This caused the server to crash when Unity requested Area of Interest (AOI) data after sending location updates.

## Solution

**Added type checking in `build_aoi()`** (app/services/kb/unified_state_manager.py:1437-1444):
```python
# Handle items stored as strings (e.g., "bottle_joy")
if isinstance(item_instance, str):
    instance_id = item_instance
    template_id = item_instance  # Use instance_id as template_id
    item_instance = {"instance_id": instance_id, "template_id": template_id}
else:
    instance_id = item_instance.get("instance_id") or item_instance.get("id")
    template_id = item_instance.get("template_id") or item_instance.get("type")
```

**Response time:** <5ms (no performance impact)

## Additional Fixes

### 1. Restored Correct Bottle Names
World state had been overwritten by template restoration at 1:26 AM, reverting custom bottle names.

**Restored from git commit 5fc7ea0:**
- spawn_zone_1: `bottle_mystery` (was: `dream_bottle_1`)
- spawn_zone_2: `bottle_energy` (was: `dream_bottle_2`)
- spawn_zone_3: `bottle_joy` (was: `dream_bottle_3`)
- spawn_zone_4: `bottle_nature` (was: `dream_bottle_4`)

### 2. Hidden Welcome Sign
Removed `welcome_sign` from entrance area by setting `visible: false` in world.json.

## Commits

**Server (gaia):**
1. `2fe9d56` - fix(kb): Handle items stored as strings in build_aoi
2. `7083a7c` - feat(kb): Add admin command system for world building

**KB (gaia-knowledge-base):**
1. `792455b` - feat(wylding): Hide welcome sign from entrance area

## Related Work: Admin Command System

Also implemented during this session (separate feature):

**Commands:**
- `@examine` - JSON introspection of items/locations/areas (<5ms)
- `@where` - Show current location context with all items (<5ms)
- `@edit` - Real-time property editing (has same string/dict issue, needs same fix)

**Implementation:**
- `admin_command_router.py` - Routes all @ commands
- `command_processor.py` - Intercepts @ prefix before fast-path
- Test scripts for each command

**Known Issues:**
- Admin commands `@examine` and `@edit` still fail with same string/dict error
- Need to apply same `isinstance(str)` fix to admin handlers

## Testing Status

✅ **Unity should now:**
- Connect to WebSocket successfully
- Send location updates without errors
- Receive AOI with correct bottle names
- Display and collect bottles

⚠️ **Admin commands:**
- `@where` - ✅ Working (1.9ms response time)
- `@examine` - ❌ Needs string/dict fix
- `@edit` - ❌ Needs string/dict fix

## Next Steps

1. Apply same `isinstance(str)` check to admin command handlers
2. Test Unity bottle collection end-to-end
3. Verify AOI data structure matches Unity expectations
4. Document bottle template requirements

## Technical Notes

**AOI Architecture:**
- Pull-based: Unity must send `{"type": "update_location", "lat": X, "lng": Y}`
- Server responds with `{"type": "area_of_interest", ...}` containing bottles
- Hot reload enabled - code changes take effect immediately without restart

**Data Model Evolution:**
- Items can be stored as strings (simple) or objects (complex)
- Template loader merges instance data with markdown templates
- Type coercion allows backward compatibility with both formats
