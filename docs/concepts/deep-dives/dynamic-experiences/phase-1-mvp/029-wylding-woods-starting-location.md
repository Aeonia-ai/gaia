# Wylding Woods Starting Location Configuration

**Status:** ✅ Implemented
**Date:** October 27, 2025
**Related:** [028-waypoint-name-resolution.md](./028-waypoint-name-resolution.md)

## Overview

Changed the starting location for the Wylding Woods experience from Dream Weaver's Clearing (waypoint_28a) to Woander Store Area (waypoint_28a_store) to provide a better onboarding experience for new players.

## Motivation

**Previous Experience:**
- Players spawned at Dream Weaver's Clearing (waypoint_28a)
- No immediate NPC interaction
- Quest-focused area without tutorial context

**New Experience:**
- Players spawn at Woander Store Area (waypoint_28a_store)
- Immediate access to Woander NPC (shop keeper)
- Natural tutorial flow: shop → quest items → delivery
- Better narrative introduction to the world

## Changes Made

### 1. KB Repository Update

**File:** `/kb/experiences/wylding-woods/locations.json`

Added `"starting_waypoint": true` field to mark the default spawn location:

```json
{
  "waypoint_28a_store": {
    "waypoint_id": "waypoint_28a_store",
    "name": "Woander Store Area",
    "starting_waypoint": true,  // ← NEW FIELD
    "gps": {
      "latitude": 37.906233,
      "longitude": -122.547721,
      "radius": 50
    },
    "description": "The entrance to Woander's mystical shop where magical items and curiosities are sold. This is where your adventure in the Wylding Woods begins.",  // ← UPDATED
    "locations": {
      "woander_store": {
        "location_id": "woander_store",
        "name": "Woander's Shop",
        "description": "A magical shop filled with mysterious artifacts and enchanted items.",
        "default_sublocation": "entrance",
        "sublocations": {
          "entrance": {
            "sublocation_id": "entrance",
            "name": "Store Entrance",
            "description": "The welcoming entrance to Woander's magical emporium.",
            "interactable": true
          },
          "counter": {
            "sublocation_id": "counter",
            "name": "Shop Counter",
            "description": "The main counter where Woander conducts business.",
            "interactable": true,
            "npc": "woander"
          },
          "back_room": {
            "sublocation_id": "back_room",
            "name": "Back Storage Room",
            "description": "A cluttered room filled with magical inventory.",
            "interactable": false
          }
        }
      }
    }
  }
}
```

**Git Commit:** `173e0be - "Set Woander Store as starting waypoint for Wylding Woods experience"`

### 2. Test Script Updates

#### `test_player_commands_wylding_woods.py`

**Changes:**
- Line 23: Changed default waypoint parameter from `"waypoint_28a"` to `"waypoint_28a_store"`
- Line 23: Changed default sublocation from `"center"` to `"entrance"`
- Line 94: Updated admin command waypoint reference
- Line 118: Updated header text to reflect new starting location

```python
# Before:
def player_cmd(command, waypoint="waypoint_28a", sublocation="center", desc=""):

# After:
def player_cmd(command, waypoint="waypoint_28a_store", sublocation="entrance", desc=""):
```

#### `play_wylding_woods.py`

**Changes:**
- Lines 17-18: Changed starting waypoint and sublocation
- Line 151: Updated welcome message
- Lines 110-111: Updated example location commands in help text

```python
# Before:
current_waypoint = "waypoint_28a"
current_sublocation = "center"
print("   You are at the Dream Weaver's Clearing.\n")

# After:
current_waypoint = "waypoint_28a_store"
current_sublocation = "entrance"
print("   You are at Woander's Mystical Store.\n")
```

### 3. Service Updates

Restarted KB service to load updated locations.json:
```bash
docker compose restart kb-service
```

## Starting Waypoint Convention

### New Field: `starting_waypoint`

**Purpose:** Mark the default spawn location for an experience

**Type:** Boolean (optional)

**Usage:**
```json
{
  "waypoint_id": "waypoint_28a_store",
  "starting_waypoint": true,  // ← Marks this as the starting location
  "name": "Woander Store Area",
  ...
}
```

**Query Pattern:**
```python
# Find starting waypoint for an experience
def get_starting_waypoint(experience: str) -> Optional[Dict]:
    locations = load_locations_json(experience)
    for waypoint in locations.values():
        if waypoint.get("starting_waypoint") == True:
            return waypoint
    return None  # No starting waypoint defined
```

**Client Integration:**
- Unity client can query for `starting_waypoint: true` to determine spawn location
- Web client can use this for "Start Experience" button
- Chat CLI can use this for default location context

## How to Play from New Starting Location

### Via Interactive Script

```bash
cd /Users/jasonasbahr/Development/Aeonia/Server/gaia
python3 scripts/testing/wylding-woods/play_wylding_woods.py
```

**Starting Context:**
- Waypoint: `waypoint_28a_store`
- Sublocation: `entrance`
- Description: "Woander's Mystical Store"

**First Commands:**
```
🎮 > look around
🎮 > /goto counter
🎮 > talk to Woander
```

### Via GAIA Chat CLI (Mu Persona)

```bash
# 1. Start GAIA CLI
python3 scripts/gaia_client.py --env local --persona mu

# 2. Set game context
You: I'm playing wylding-woods. I'm at waypoint_28a_store, at the entrance to Woander's Store.

# 3. Play naturally
You: Look around
You: Go to the counter
You: Talk to Woander
You: What do you have for sale?
```

**Important:** Remind Mu of your location when moving:
```
You: I'm at the counter now. Talk to Woander
You: I'm at shelf_1 now. Look around
```

### Via Test Script

```bash
cd /Users/jasonasbahr/Development/Aeonia/Server/gaia
python3 scripts/testing/wylding-woods/test_player_commands_wylding_woods.py
```

**Tests automatically use new starting location:**
- All player commands default to `waypoint_28a_store/entrance`
- Pre-setup commands reset to Woander Store
- Section headers reflect new starting location

## Waypoint Details

### Woander Store Area (waypoint_28a_store)

**GPS Coordinates:**
- Latitude: 37.906233
- Longitude: -122.547721
- Radius: 50 meters

**Sublocations:**
1. **entrance** (starting sublocation)
   - The welcoming entrance to Woander's magical emporium
   - Interactable: Yes

2. **counter**
   - The main counter where Woander conducts business
   - Interactable: Yes
   - NPC: Woander (shop keeper)

3. **back_room**
   - A cluttered room filled with magical inventory
   - Interactable: No (future expansion)

**Connected Waypoints:**
- waypoint_28a (Dream Weaver's Clearing) - Quest destination

## Narrative Flow

### Old Flow (waypoint_28a start)
```
Player spawns → Dream Weaver's Clearing → Find NPCs → Get quest → Return
```

### New Flow (waypoint_28a_store start)
```
Player spawns → Woander's Shop → Meet Woander → Learn about dream bottles →
Travel to Dream Weaver's Clearing → Collect bottles → Return to fairy doors
```

**Benefits:**
- ✅ Immediate NPC interaction (Woander)
- ✅ Clear tutorial flow (shop → quest → delivery)
- ✅ Better world-building (economic hub → magical locations)
- ✅ Natural progression (safe zone → adventure zone)

## Testing

### Verify Starting Location

```bash
# 1. Test interactive gameplay
python3 scripts/testing/wylding-woods/play_wylding_woods.py

# Expected output:
# 🌲 Welcome to the Wylding Woods!
#    You are at Woander's Mystical Store.

# 2. Run test suite
python3 scripts/testing/wylding-woods/test_player_commands_wylding_woods.py

# Expected: All tests pass with waypoint_28a_store context
```

### Verify KB Service

```bash
# Check KB service loaded updated locations.json
curl -X POST http://localhost:8001/game/command \
  -H "Content-Type: application/json" \
  -H "X-API-Key: hMzhtJFi26IN2rQlMNFaVx2YzdgNTL3H8m-ouwV2UhY" \
  -d '{
    "command": "look around",
    "experience": "wylding-woods",
    "user_context": {
      "user_id": "test@example.com",
      "waypoint": "waypoint_28a_store",
      "sublocation": "entrance",
      "role": "player"
    }
  }'

# Expected: Narrative about Woander's Store entrance
```

## Future Enhancements

### 1. Starting Waypoint Query Endpoint

Add endpoint to KB service:
```python
@router.get("/experiences/{experience}/starting-waypoint")
async def get_starting_waypoint(experience: str):
    """Get the starting waypoint for an experience."""
    locations = load_locations_json(experience)
    for waypoint_id, waypoint in locations.items():
        if waypoint.get("starting_waypoint"):
            return {
                "waypoint_id": waypoint_id,
                "waypoint": waypoint
            }
    return {"error": "No starting waypoint defined"}
```

**Unity Integration:**
```csharp
// Fetch starting waypoint on experience load
var response = await GetAsync($"/experiences/wylding-woods/starting-waypoint");
var startingWaypoint = JsonUtility.FromJson<Waypoint>(response);
SpawnPlayerAt(startingWaypoint.gps);
```

### 2. Multiple Starting Waypoints

Support different starting locations based on player level or choices:

```json
{
  "waypoint_28a_store": {
    "starting_waypoint": true,
    "starting_conditions": {
      "player_level": "beginner",
      "prerequisite_quest": null
    }
  },
  "waypoint_advanced_area": {
    "starting_waypoint": true,
    "starting_conditions": {
      "player_level": "advanced",
      "prerequisite_quest": "complete_tutorial"
    }
  }
}
```

### 3. Starting Location Tutorial

Add tutorial dialogue when player first spawns:

```json
{
  "waypoint_28a_store": {
    "starting_waypoint": true,
    "tutorial": {
      "enabled": true,
      "npc": "woander",
      "dialogue": [
        "Welcome to the Wylding Woods, traveler!",
        "I'm Woander, keeper of this shop.",
        "The Dream Weaver needs help collecting scattered dream bottles...",
        "Would you be willing to help?"
      ]
    }
  }
}
```

## Related Documentation

- [028-waypoint-name-resolution.md](./028-waypoint-name-resolution.md) - Waypoint lookup methods
- [022-location-tracking-admin-commands.md](./022-location-tracking-admin-commands.md) - Location system architecture
- [009-game-command-developer-guide.md](./009-game-command-developer-guide.md) - Game command processing

## Summary

**What Changed:**
- ✅ Starting waypoint moved from waypoint_28a to waypoint_28a_store
- ✅ Added `starting_waypoint: true` convention to locations.json
- ✅ Updated all test scripts to use new starting location
- ✅ Committed changes to KB repository (git commit 173e0be)

**Impact:**
- Better player onboarding with immediate NPC interaction
- Clear tutorial flow from shop → quest → completion
- Established pattern for marking starting waypoints
- Foundation for Unity/web client spawn logic

**Location:**
- File: `/kb/experiences/wylding-woods/locations.json`
- Waypoint ID: `waypoint_28a_store`
- GPS: 37.906233, -122.547721
- Starting Sublocation: `entrance`
