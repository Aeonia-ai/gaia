# CRITICAL: AOI Field Name Mismatch Issue

**Date**: 2025-11-10
**Status**: 🔴 BLOCKING ISSUE - Unity Integration Broken
**Priority**: P0 - Fix Before Demo

---

## Problem Summary

Documentation shows `instance_id` but implementation uses `id`. Unity developers following docs will fail to collect items.

---

## The Three-Way Mismatch

### 1. Source Data (world.json)
```json
{
  "id": "dream_bottle_1",    // ← Actual field
  "type": "dream_bottle",
  "collectible": true
}
```

### 2. AOI Response (what server actually sends)
```json
{
  "id": "dream_bottle_1",    // ← Passes through from world.json
  "type": "dream_bottle",
  "collectible": true
}
```

### 3. Documentation (what we told Unity)
```json
{
  "instance_id": "dream_bottle_1",  // ← WRONG! Field doesn't exist!
  "template_id": "dream_bottle"
}
```

### 4. Handler Expectation (collect_item.py:17)
```python
item_id = command_data.get("item_id")  // ← Expects "item_id"!
```

**Result**: Nothing matches! Collection fails! ❌

---

## Root Cause

**Documentation was aspirational (v0.4 design) not actual (v0.3 implementation).**

- Docs show what we WANT (instance_id/template_id)
- Code has what we HAVE (id)
- Handler expects something else (item_id)

---

## Immediate Fix (Emergency - Do NOW)

### Update Client Documentation

**File**: `docs/scratchpad/websocket-aoi-client-guide.md`

**Change all item examples from:**
```json
{
  "instance_id": "dream_bottle_1",  // ❌ WRONG
  "template_id": "dream_bottle"
}
```

**To:**
```json
{
  "id": "dream_bottle_1",           // ✅ CORRECT (matches world.json)
  "type": "dream_bottle"
}
```

### Unity Action Message Format

**Unity should send:**
```json
{
  "type": "action",
  "action": "collect_item",
  "item_id": "dream_bottle_1",      // ← Use "item_id" not "instance_id"
  "location": "woander_store"
}
```

---

## Proper Fix (Next Week - With v0.4)

### 1. Normalize AOI Builder

```python
# unified_state_manager.py build_aoi()
# Make items match NPCs structure
for item in area_data.get("items", []):
    normalized_item = {
        "instance_id": item.get("id"),    # Map id → instance_id
        "template_id": item.get("id"),    # Same for MVP
        "type": item.get("type"),
        # ... other fields
    }
    areas[area_id]["items"].append(normalized_item)
```

### 2. Dual-Support Handler

```python
# handlers/collect_item.py
# Accept both during migration
item_id = command_data.get("instance_id") or command_data.get("item_id")
```

### 3. WorldUpdate v0.4 Alignment

```python
{
  "type": "world_update",
  "version": "0.4",
  "changes": [{
    "operation": "remove",
    "area_id": "spawn_zone_1",
    "instance_id": "dream_bottle_1"  // Consistent with AOI
  }]
}
```

---

## Action Items

**CRITICAL (Today):**
- [ ] Update client guide documentation (all item examples)
- [ ] Notify Unity team of field name changes
- [ ] Test collect_item with corrected field names
- [ ] Verify demo works end-to-end

**Important (Next Week):**
- [ ] Implement AOI normalization
- [ ] Add dual-field support to handler
- [ ] Update WorldUpdate to v0.4 format
- [ ] Re-test with normalized structure

---

## Testing Checklist

**Before Demo:**
- [ ] Unity receives AOI with `"id"` field
- [ ] Unity sends `{"item_id": "..."}` in collect action
- [ ] Handler successfully processes collection
- [ ] World update confirms item removed
- [ ] Inventory shows collected item

**After v0.4:**
- [ ] Unity receives AOI with `"instance_id"` field
- [ ] Unity can send either `instance_id` or `item_id`
- [ ] Handler normalizes to instance_id internally
- [ ] WorldUpdate uses instance_id consistently

---

## Current vs Target Structure

### Current (v0.3 - Reality)
```json
// AOI item structure
{
  "id": "dream_bottle_1",
  "type": "dream_bottle",
  "collectible": true,
  "state": {...}
}

// Collect action
{"action": "collect_item", "item_id": "dream_bottle_1"}

// WorldUpdate
{"changes": {"location.area.id": {"operation": "remove", "item": {"id": "..."}}}}
```

### Target (v0.4 - Unified)
```json
// AOI item structure
{
  "instance_id": "dream_bottle_1",
  "template_id": "dream_bottle",
  "collectible": true,
  "state": {...}
}

// Collect action
{"action": "collect_item", "instance_id": "dream_bottle_1"}

// WorldUpdate
{"changes": [{"operation": "remove", "area_id": "spawn_zone_1", "instance_id": "..."}]}
```

---

## NPCs Already Use Correct Structure!

**NPCs are already normalized:**
```python
# unified_state_manager.py:1294-1298
areas[area_id]["npcs"].append({
    "instance_id": f"{npc_id}_1",    // ✅ Uses instance_id!
    "template_id": npc_id,           // ✅ Uses template_id!
    **npc_data
})
```

**We just need items to match NPCs!**

---

**Status**: 🔴 Awaiting emergency documentation fix
**Next Update**: After Unity team notified
