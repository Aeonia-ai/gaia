# Quest-Driven Dynamic Spawning System

**Created**: 2025-11-13
**Status**: Design Document
**Related**: Unity-Server Integration, Wylding Woods Experience

## Overview

This document describes how to implement dynamic item spawning/hiding based on quest state, enabling NPC-driven gameplay where items appear after conversations or quest triggers.

**Use Case**: Louisa gives player a quest to collect dream bottles, which then appear in the world for collection.

---

## Current State (What Already Works)

Items have visibility controls built-in:

```json
{
  "instance_id": "dream_bottle_1",
  "template_id": "dream_bottle",
  "visible": true,        // ← Already supported!
  "collectible": true
}
```

**This means**: We can already hide/show items by changing the `visible` field!

Unity automatically respects `visible` field:
- `visible: true` → Item spawns in scene
- `visible: false` → Item doesn't spawn (or despawns if previously visible)

---

## Three Implementation Approaches

### Option A: Pre-Placed with Visibility Toggle (Simplest)

**Concept**: Items exist in world.json from the start, but hidden until quest.

**Data Structure**:
```json
{
  "spawn_zone_1": {
    "items": [
      {
        "instance_id": "dream_bottle_1",
        "template_id": "dream_bottle",
        "visible": false,           // ← Hidden until quest
        "collectible": true,
        "spawn_trigger": "quest:collect_dream_bottles"  // Metadata
      }
    ]
  }
}
```

**Quest Flow**:
1. Player talks to Louisa → `talk louisa` command
2. Louisa gives quest → Server marks quest `collect_dream_bottles` as active
3. Server updates `visible: false → true` for all dream bottles
4. Server sends AOI update → Unity spawns bottles

**Pros**:
- ✅ Simple implementation
- ✅ Items have fixed positions from the start
- ✅ Works with current architecture
- ✅ No database schema changes needed

**Cons**:
- ❌ Items "exist but hidden" (feels less magical)
- ❌ No randomization of spawn locations
- ❌ Must modify world.json to toggle visibility

---

### Option B: Dynamic Addition (More Flexible)

**Concept**: Items don't exist in world.json initially, added to runtime state on quest.

**Data Structure**:

```json
// BEFORE quest (world.json):
{
  "spawn_zone_1": {
    "items": []  // Empty!
  }
}

// AFTER quest (runtime state in memory):
{
  "spawn_zone_1": {
    "items": [
      {
        "instance_id": "dream_bottle_1_runtime",
        "template_id": "dream_bottle",
        "visible": true,
        "collectible": true,
        "spawned_by_quest": "collect_dream_bottles"
      }
    ]
  }
}
```

**Quest Flow**:
1. Player talks to Louisa
2. Louisa gives quest
3. **Server creates new items** and adds to world state (in-memory)
4. Server sends AOI update → Unity spawns bottles
5. **Persist changes** to world.json or database for next login

**Pros**:
- ✅ True dynamic spawning (items appear magically)
- ✅ Can randomize spawn locations
- ✅ Can adjust quantities based on difficulty
- ✅ Clean separation of base world vs runtime additions

**Cons**:
- ❌ More complex state management
- ❌ Need to persist runtime changes
- ❌ Requires state synchronization across player sessions

---

### Option C: Condition-Based Filtering (Most Scalable)

**Concept**: Items exist in world.json but AOI builder filters based on player state.

**Data Structure**:
```json
{
  "spawn_zone_1": {
    "items": [
      {
        "instance_id": "dream_bottle_1",
        "template_id": "dream_bottle",
        "visible": true,
        "collectible": true,
        "spawn_conditions": {
          "quest_active": "collect_dream_bottles",
          "min_level": 1,
          "not_collected": true
        }
      }
    ]
  }
}
```

**Server Logic**:
```python
async def build_aoi(self, user_id, experience, lat, lng):
    # ... load world state ...

    # Get player quest state
    player_quests = await get_player_quests(user_id)
    player_inventory = await get_player_inventory(user_id)

    # Filter items based on conditions
    visible_items = []
    for area_id, area_data in areas.items():
        for item in area_data.get("items", []):
            conditions = item.get("spawn_conditions", {})

            # Check quest requirement
            if "quest_active" in conditions:
                if conditions["quest_active"] not in player_quests:
                    continue  # Skip this item, player hasn't started quest

            # Check if already collected
            if conditions.get("not_collected"):
                if item["instance_id"] in player_inventory:
                    continue  # Skip, player already has it

            # Check level requirement
            if "min_level" in conditions:
                player_level = await get_player_level(user_id)
                if player_level < conditions["min_level"]:
                    continue

            # Item passes all conditions, include in AOI
            visible_items.append(item)

    return visible_items
```

**Pros**:
- ✅ Declarative (conditions in data, not code)
- ✅ Scales to complex conditions
- ✅ No state mutation needed
- ✅ Easy to add new condition types
- ✅ Each player sees different items based on their state

**Cons**:
- ❌ More sophisticated AOI builder logic
- ❌ Conditions can get complex
- ❌ Performance impact if checking many conditions

---

## Recommended Hybrid Approach

**Combine Options A & C** for best of both worlds:

### World Data Structure

```json
{
  "locations": {
    "woander_store": {
      "description": "Woander's mystical shop",
      "areas": {
        "spawn_zone_1": {
          "description": "A shelf displaying magical curiosities",
          "items": [
            {
              "instance_id": "dream_bottle_1",
              "template_id": "dream_bottle",
              "semantic_name": "mysterious dream bottle",
              "visible": true,
              "collectible": true,
              "spawn_conditions": {
                "quest_active": "collect_dream_bottles"
              },
              "state": {
                "glowing": true,
                "dream_type": "mysterious",
                "symbol": "spiral"
              }
            }
          ]
        },
        "spawn_zone_2": {
          "items": [
            {
              "instance_id": "dream_bottle_2",
              "template_id": "dream_bottle",
              "semantic_name": "adventurous dream bottle",
              "visible": true,
              "collectible": true,
              "spawn_conditions": {
                "quest_active": "collect_dream_bottles"
              },
              "state": {
                "glowing": true,
                "dream_type": "adventurous",
                "symbol": "star"
              }
            }
          ]
        },
        "spawn_zone_3": {
          "items": [
            {
              "instance_id": "dream_bottle_3",
              "template_id": "dream_bottle",
              "semantic_name": "joyful dream bottle",
              "visible": true,
              "collectible": true,
              "spawn_conditions": {
                "quest_active": "collect_dream_bottles"
              },
              "state": {
                "glowing": true,
                "dream_type": "joyful",
                "symbol": "moon"
              }
            }
          ]
        },
        "spawn_zone_4": {
          "items": [
            {
              "instance_id": "dream_bottle_4",
              "template_id": "dream_bottle",
              "semantic_name": "whimsical dream bottle",
              "visible": true,
              "collectible": true,
              "spawn_conditions": {
                "quest_active": "collect_dream_bottles"
              },
              "state": {
                "glowing": true,
                "dream_type": "whimsical",
                "symbol": "sun"
              }
            }
          ]
        }
      }
    }
  },
  "quests": {
    "collect_dream_bottles": {
      "id": "collect_dream_bottles",
      "name": "The Dream Collector",
      "description": "Louisa needs help collecting special dream bottles scattered around Woander's store.",
      "giver_npc": "louisa",
      "objectives": [
        {
          "type": "collect",
          "item_template": "dream_bottle",
          "quantity": 4,
          "locations": ["woander_store"]
        }
      ],
      "rewards": {
        "experience": 100,
        "items": ["dream_weaver_charm"]
      },
      "next_quest": "explore_el_paseo"
    }
  }
}
```

---

## Complete Implementation: Louisa Quest Flow

### Step 1: Player Initiates Conversation

**Player Command**:
```bash
> talk louisa
```

**Server Handler** (`app/services/kb/handlers/talk.py`):
```python
async def handle_talk(user_id: str, experience: str, npc_name: str):
    """Handle talking to an NPC."""

    # Get NPC data
    npc = await get_npc_data(experience, npc_name)

    # Get player quest state
    player_quests = await get_player_quests(user_id)

    # Determine NPC state based on quest progress
    npc_state = determine_npc_state(npc, player_quests)

    # Get appropriate dialogue
    dialogue = npc["states"][npc_state]["dialogue"]
    available_quests = npc["states"][npc_state].get("quests_available", [])

    # Build response
    response = {
        "type": "npc_dialogue",
        "npc": npc_name,
        "dialogue": dialogue,
        "options": []
    }

    # Add quest options if available
    for quest_id in available_quests:
        quest = await get_quest_data(experience, quest_id)
        response["options"].append({
            "id": f"accept_quest:{quest_id}",
            "text": f"Accept quest: {quest['name']}"
        })

    # Add generic options
    response["options"].append({"id": "goodbye", "text": "Goodbye"})

    return response
```

**Server Response**:
```json
{
  "type": "npc_dialogue",
  "npc": "louisa",
  "dialogue": "Hello traveler! I'm Louisa, the Dream Weaver. I collect special dreams and bottle them for safekeeping. Would you help me find some dream bottles scattered around Woander's store?",
  "options": [
    {"id": "accept_quest:collect_dream_bottles", "text": "Accept quest: The Dream Collector"},
    {"id": "decline_quest", "text": "Maybe later."},
    {"id": "ask_more", "text": "Tell me more about dream bottles."},
    {"id": "goodbye", "text": "Goodbye"}
  ]
}
```

---

### Step 2: Player Accepts Quest

**Player Command**:
```bash
> accept quest collect_dream_bottles
```

**Server Handler**:
```python
async def accept_quest(user_id: str, experience: str, quest_id: str):
    """Handle quest acceptance."""

    # 1. Add quest to player's active quests
    await add_active_quest(user_id, quest_id)

    # 2. Load quest data
    quest = await get_quest_data(experience, quest_id)

    # 3. Trigger quest start event (for analytics, achievements, etc.)
    await trigger_event("quest_started", {
        "user_id": user_id,
        "quest_id": quest_id,
        "experience": experience
    })

    # 4. Get player location
    player_state = await get_player_state(user_id)
    lat = player_state["location"]["lat"]
    lng = player_state["location"]["lng"]

    # 5. Build and send updated AOI (items now visible due to quest_active condition)
    aoi = await build_aoi(user_id, experience, lat, lng)
    await send_aoi_update(user_id, aoi)

    # 6. Send quest accepted confirmation
    return {
        "type": "quest_accepted",
        "quest_id": quest_id,
        "quest_name": quest["name"],
        "message": "Louisa smiles warmly. 'Thank you! Look around the store - the bottles glow with a magical light. Bring them to me when you find them all.'",
        "objectives": quest["objectives"]
    }
```

**Updated AOI Builder** (`app/services/kb/unified_state_manager.py`):
```python
async def build_aoi(self, user_id: str, experience: str, lat: float, lng: float):
    # ... existing code to load world state ...

    # Get player quest state
    player_quests = await get_player_quests(user_id)
    player_inventory = await get_player_inventory(user_id)

    # Filter items based on spawn_conditions
    for area_id, area_data in areas.items():
        filtered_items = []

        for item in area_data.get("items", []):
            # Check spawn conditions
            conditions = item.get("spawn_conditions", {})

            # Quest active requirement
            if "quest_active" in conditions:
                required_quest = conditions["quest_active"]
                if required_quest not in player_quests:
                    continue  # Skip item, quest not active

            # Not collected requirement
            if conditions.get("not_collected", False):
                if item["instance_id"] in player_inventory:
                    continue  # Skip item, already collected

            # Level requirement
            if "min_level" in conditions:
                player_level = await get_player_level(user_id)
                if player_level < conditions["min_level"]:
                    continue

            # Time of day requirement
            if "time_of_day" in conditions:
                current_hour = datetime.now().hour
                required_time = conditions["time_of_day"]
                if not check_time_condition(current_hour, required_time):
                    continue

            # Item passes all conditions
            filtered_items.append(item)

        # Update area with filtered items
        areas[area_id]["items"] = filtered_items

    # ... rest of AOI building ...
```

**AOI Update Sent to Unity**:
```json
{
  "type": "area_of_interest",
  "zone": {
    "id": "woander_store",
    "name": "#1  INTER - Woander Storefront"
  },
  "areas": {
    "spawn_zone_1": {
      "description": "A shelf displaying various magical curiosities and glowing bottles.",
      "items": [
        {
          "instance_id": "dream_bottle_1",
          "template_id": "dream_bottle",
          "semantic_name": "mysterious dream bottle",
          "visible": true,
          "collectible": true,
          "state": {
            "glowing": true,
            "dream_type": "mysterious",
            "symbol": "spiral"
          }
        }
      ]
    },
    "spawn_zone_2": {
      "items": [
        {
          "instance_id": "dream_bottle_2",
          "template_id": "dream_bottle",
          "semantic_name": "adventurous dream bottle",
          "visible": true,
          "collectible": true,
          "state": {
            "glowing": true,
            "dream_type": "adventurous",
            "symbol": "star"
          }
        }
      ]
    }
    // ... spawn_zone_3 and spawn_zone_4 with dream bottles
  },
  "snapshot_version": 1731524000000
}
```

**Unity Response**:
- Receives AOI update with 4 dream bottles
- Detects new items not in `_activeInstances`
- Spawns bottles at their respective spawn zones
- Player sees bottles appear with glowing particle effects!

---

### Step 3: Player Collects Bottles

**Player Command**:
```bash
> collect dream_bottle_1
```

**Server Handler** (`app/services/kb/handlers/collect_item.py`):
```python
async def handle_collect_item(user_id: str, experience: str, instance_id: str):
    """Handle item collection."""

    # 1. Verify item exists and is collectible
    item = await get_item_from_world(experience, instance_id)
    if not item:
        return {"error": "Item not found"}

    if not item.get("collectible", False):
        return {"error": "This item cannot be collected"}

    # 2. Remove from world state
    await remove_item_from_world(experience, instance_id)

    # 3. Add to player inventory
    await add_to_inventory(user_id, instance_id, item)

    # 4. Check quest progress
    active_quests = await get_active_quests(user_id)
    for quest_id in active_quests:
        quest = await get_quest_data(experience, quest_id)

        # Check if this item contributes to quest objectives
        for objective in quest["objectives"]:
            if objective["type"] == "collect":
                if item["template_id"] == objective["item_template"]:
                    # Update quest progress
                    collected_count = await count_items_in_inventory(
                        user_id,
                        objective["item_template"]
                    )

                    if collected_count >= objective["quantity"]:
                        # Objective complete!
                        await update_quest_progress(user_id, quest_id, {
                            "objective_complete": True,
                            "ready_to_complete": True
                        })

    # 5. Get player location and rebuild AOI
    player_state = await get_player_state(user_id)
    aoi = await build_aoi(user_id, experience, player_state["lat"], player_state["lng"])

    # 6. Send AOI update (item removed from world)
    await send_aoi_update(user_id, aoi)

    # 7. Send collection confirmation
    return {
        "type": "item_collected",
        "instance_id": instance_id,
        "semantic_name": item.get("semantic_name", "item"),
        "message": f"You collected the {item.get('semantic_name', 'item')}!"
    }
```

**Unity Response**:
- Receives AOI update
- `dream_bottle_1` no longer in items list for spawn_zone_1
- Detects removed item in `_activeInstances`
- Despawns bottle from scene with collection particle effect
- Player sees bottle disappear

---

### Step 4: Quest Completion

**Player Command**:
```bash
> talk louisa
```

**Server Checks**:
1. Player has 4 dream bottles in inventory (`dream_bottle` template)
2. Quest "collect_dream_bottles" is active
3. Quest objective: collect 4 dream bottles → COMPLETE
4. → Trigger quest completion flow

**Server Handler**:
```python
async def handle_talk_with_quest_completion(user_id: str, npc_name: str):
    """Handle NPC conversation with quest completion check."""

    # Get active quests
    active_quests = await get_active_quests(user_id)

    # Check if any quests are ready to complete
    completable_quests = []
    for quest_id in active_quests:
        quest_progress = await get_quest_progress(user_id, quest_id)
        if quest_progress.get("ready_to_complete"):
            quest = await get_quest_data(experience, quest_id)
            if quest["giver_npc"] == npc_name:
                completable_quests.append(quest_id)

    # Complete quests
    responses = []
    for quest_id in completable_quests:
        quest = await get_quest_data(experience, quest_id)

        # Award rewards
        await award_quest_rewards(user_id, quest["rewards"])

        # Mark quest complete
        await complete_quest(user_id, quest_id)

        # Build completion response
        responses.append({
            "type": "quest_complete",
            "quest_id": quest_id,
            "quest_name": quest["name"],
            "dialogue": get_completion_dialogue(npc_name, quest_id),
            "rewards": quest["rewards"],
            "next_quest": quest.get("next_quest")
        })

    return responses
```

**Server Response**:
```json
{
  "type": "quest_complete",
  "quest_id": "collect_dream_bottles",
  "quest_name": "The Dream Collector",
  "npc": "louisa",
  "dialogue": "You found them all! These dreams are precious - they hold the hopes and wishes of Mill Valley. As a thank you, please accept this Dream Weaver Charm. It will help you sense other magical items nearby.",
  "rewards": {
    "experience": 100,
    "items": ["dream_weaver_charm"]
  },
  "next_quest": "explore_el_paseo"
}
```

---

## Advanced Features

### A. Spawn Randomization

For procedural/roguelike content:

```json
{
  "spawn_zones": {
    "dynamic_spawn_pool": {
      "quest_trigger": "collect_dream_bottles",
      "spawn_count": 4,
      "possible_locations": [
        "spawn_zone_1",
        "spawn_zone_2",
        "spawn_zone_3",
        "spawn_zone_4",
        "entrance",
        "fairy_house_moon"
      ],
      "item_templates": ["dream_bottle"],
      "randomize": true,
      "seed": "user_id"  // Different for each player
    }
  }
}
```

**Server Logic**:
```python
def randomize_spawn_locations(spawn_pool, user_id):
    """Randomly assign items to locations."""
    import random

    # Use user_id as seed for consistency
    random.seed(hash(user_id))

    # Select random subset of locations
    locations = random.sample(
        spawn_pool["possible_locations"],
        spawn_pool["spawn_count"]
    )

    # Create items at selected locations
    spawned_items = []
    for i, location in enumerate(locations):
        item = {
            "instance_id": f"dream_bottle_{i+1}_{user_id}",
            "template_id": random.choice(spawn_pool["item_templates"]),
            "collectible": true,
            "visible": true,
            "spawned_location": location
        }
        spawned_items.append(item)

    return spawned_items
```

### B. Timed Spawning

For time-limited events or day/night cycles:

```json
{
  "instance_id": "dream_bottle_rare",
  "template_id": "dream_bottle",
  "spawn_conditions": {
    "quest_active": "collect_dream_bottles",
    "time_of_day": "night",     // Only spawns between 6pm-6am
    "day_of_week": ["friday", "saturday"],  // Weekend only
    "cooldown_hours": 24         // Respawns every 24 hours after collection
  }
}
```

**Time Condition Check**:
```python
def check_time_condition(current_hour, condition):
    """Check if current time matches spawn condition."""
    if condition == "night":
        return current_hour >= 18 or current_hour < 6
    elif condition == "day":
        return 6 <= current_hour < 18
    elif condition == "morning":
        return 6 <= current_hour < 12
    elif condition == "evening":
        return 18 <= current_hour < 22
    return True
```

### C. Progressive Area Unlocking

Lock/unlock areas based on quest completion:

```json
{
  "back_room": {
    "locked": true,
    "unlock_conditions": {
      "quest_complete": "collect_dream_bottles"
    },
    "description": "A mysterious locked door. Perhaps Woander will let you in after you help Louisa?",
    "unlocked_description": "The back room of Woander's shop, filled with rare magical artifacts.",
    "items": [
      {
        "instance_id": "rare_artifact_1",
        "template_id": "ancient_scroll",
        "collectible": true,
        "visible": true
      }
    ]
  }
}
```

**AOI Builder Filtering**:
```python
def filter_locked_areas(areas, player_quests):
    """Remove locked areas from AOI if player hasn't unlocked them."""
    visible_areas = {}

    for area_id, area_data in areas.items():
        if area_data.get("locked"):
            unlock_conditions = area_data.get("unlock_conditions", {})

            # Check quest completion requirement
            if "quest_complete" in unlock_conditions:
                required_quest = unlock_conditions["quest_complete"]
                if required_quest not in player_quests["completed"]:
                    continue  # Skip locked area

        visible_areas[area_id] = area_data

    return visible_areas
```

### D. NPC State Changes

NPCs change behavior based on quest progress:

```json
{
  "npcs": {
    "louisa": {
      "name": "Louisa",
      "role": "Dream Weaver",
      "states": {
        "default": {
          "dialogue": "Hello traveler! I'm Louisa, the Dream Weaver. Would you help me collect some special dream bottles?",
          "quests_available": ["collect_dream_bottles"],
          "interactions": ["talk"]
        },
        "quest_active": {
          "dialogue": "Have you found the dream bottles yet? They should be glowing around the store.",
          "quests_available": [],
          "interactions": ["talk", "check_progress"]
        },
        "quest_complete": {
          "dialogue": "Thank you for your help! The dreams are safe now. If you're interested, I could teach you about dream weaving...",
          "quests_available": ["learn_dream_weaving", "explore_el_paseo"],
          "interactions": ["talk", "trade", "teach"],
          "shop_unlocked": true,
          "shop_inventory": [
            {"item_id": "dream_catcher", "price": 100},
            {"item_id": "memory_bottle", "price": 50}
          ]
        }
      }
    }
  }
}
```

**State Determination**:
```python
def determine_npc_state(npc, player_quests):
    """Determine NPC's current state based on player progress."""

    # Check completed quests first
    for state_name, state_data in npc["states"].items():
        if "requires_quest_complete" in state_data:
            required_quest = state_data["requires_quest_complete"]
            if required_quest in player_quests["completed"]:
                return state_name

    # Check active quests
    for state_name, state_data in npc["states"].items():
        if "requires_quest_active" in state_data:
            required_quest = state_data["requires_quest_active"]
            if required_quest in player_quests["active"]:
                return state_name

    # Default state
    return "default"
```

---

## Implementation Phases

### Phase 1: MVP - Visibility Toggle (Recommended Start)

**Goal**: Make dream bottles appear when Louisa gives quest

**Changes Needed**:
1. Add `spawn_conditions` field to dream bottle items in world.json
2. Update AOI builder to filter items based on `spawn_conditions`
3. Implement basic quest system (active quests tracked in player state)
4. Add quest acceptance to `talk` command handler

**Estimated Effort**: 2-3 hours
**Files Modified**:
- `world.json` - Add spawn_conditions to items
- `unified_state_manager.py` - Add condition filtering to build_aoi
- `handlers/talk.py` - Add quest dialogue and acceptance
- Player state schema - Add `active_quests` field

---

### Phase 2: Add Spawn Conditions

**Goal**: Declarative filtering with multiple condition types

**Changes Needed**:
1. Implement condition checking for:
   - `quest_active`
   - `not_collected`
   - `min_level`
   - `time_of_day`
2. Add condition evaluation framework

**Estimated Effort**: 1-2 hours
**Files Modified**:
- `unified_state_manager.py` - Enhanced condition checking

---

### Phase 3: Dynamic Spawning & Randomization

**Goal**: Runtime item creation with procedural placement

**Changes Needed**:
1. Implement spawn pool system
2. Add randomization logic
3. Persist runtime-spawned items
4. Add cooldown/respawn mechanics

**Estimated Effort**: 4-5 hours
**Files Modified**:
- `unified_state_manager.py` - Add dynamic spawning
- Player state - Track spawned items and cooldowns
- Database schema - Add runtime item tracking

---

### Phase 4: Full Quest System

**Goal**: Complete quest framework with dependencies, branches, rewards

**Changes Needed**:
1. Quest definition schema
2. Objective tracking system
3. Reward distribution
4. Quest chains and dependencies
5. Quest UI/notification system

**Estimated Effort**: 8-10 hours
**Files Modified**:
- New: `quest_manager.py`
- New: `quest_schema.json`
- Database schema - Add quest tables
- Multiple handler files for quest commands

---

## Testing Checklist

### Phase 1 Testing

- [ ] Dream bottles don't appear in AOI before quest
- [ ] Player can talk to Louisa
- [ ] Player can accept quest
- [ ] Dream bottles appear in AOI after accepting quest
- [ ] Unity spawns bottles correctly
- [ ] Player can collect bottles
- [ ] Unity despawns collected bottles
- [ ] Player can return to Louisa after collecting all
- [ ] Quest completes successfully
- [ ] Rewards are awarded
- [ ] Bottles don't reappear for same player

### Phase 2 Testing

- [ ] Level-gated items only appear for eligible players
- [ ] Time-based items spawn/despawn at correct times
- [ ] Already-collected items don't reappear
- [ ] Multiple conditions work together (AND logic)

### Phase 3 Testing

- [ ] Randomization produces different layouts per player
- [ ] Randomization is consistent for same player
- [ ] Cooldowns prevent immediate respawn
- [ ] Items respawn after cooldown expires

### Phase 4 Testing

- [ ] Quest chains unlock in correct order
- [ ] Branching quests work correctly
- [ ] Quest UI shows progress
- [ ] Rewards handle inventory limits
- [ ] Failed quests can be retried

---

## Unity Integration

**No Unity code changes required!** Unity automatically handles all spawning/despawning based on AOI updates.

### Unity's Automatic Handling

**When items become visible:**
```csharp
// Unity's ApplySnapshot detects new items
foreach (var item in aoi.items) {
    if (!_activeInstances.ContainsKey(item.instance_id)) {
        SpawnItem(areaId, item);  // Spawn with particle effect
    }
}
```

**When items are removed:**
```csharp
// Unity's ApplySnapshot detects removed items
var currentInstanceIds = aoi.items.Select(i => i.instance_id);
var removedItems = _activeInstances.Keys.Except(currentInstanceIds);

foreach (var instanceId in removedItems) {
    DespawnItem(instanceId);  // Despawn with particle effect
}
```

### Optional Unity Enhancements

**Quest Notification UI**:
- Show "New Quest!" popup when quest accepted
- Display quest objectives in HUD
- Show progress (2/4 bottles collected)

**Visual Effects**:
- Spawn animation when bottles appear
- Glowing outline for quest items
- Collection particle effect
- Quest completion celebration

**Audio**:
- Quest accepted sound
- Item spawn sound
- Collection sound
- Quest complete fanfare

---

## Database Schema

### Player Quest State

```sql
CREATE TABLE player_quests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    experience VARCHAR(255) NOT NULL,
    quest_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'active', 'completed', 'failed'
    progress JSONB DEFAULT '{}',
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    UNIQUE(user_id, experience, quest_id)
);

CREATE INDEX idx_player_quests_user_status
    ON player_quests(user_id, status);
```

### Player Inventory

```sql
CREATE TABLE player_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    experience VARCHAR(255) NOT NULL,
    instance_id VARCHAR(255) NOT NULL,
    template_id VARCHAR(255) NOT NULL,
    item_data JSONB NOT NULL,
    acquired_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, experience, instance_id)
);

CREATE INDEX idx_player_inventory_user
    ON player_inventory(user_id, experience);
```

### Runtime Spawned Items (Phase 3)

```sql
CREATE TABLE runtime_spawned_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    experience VARCHAR(255) NOT NULL,
    instance_id VARCHAR(255) NOT NULL,
    template_id VARCHAR(255) NOT NULL,
    location_id VARCHAR(255) NOT NULL,
    area_id VARCHAR(255) NOT NULL,
    item_data JSONB NOT NULL,
    spawned_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP, -- For temporary/timed spawns
    cooldown_until TIMESTAMP, -- For respawn cooldowns
    UNIQUE(user_id, experience, instance_id)
);

CREATE INDEX idx_runtime_spawned_user_exp
    ON runtime_spawned_items(user_id, experience);

CREATE INDEX idx_runtime_spawned_cooldown
    ON runtime_spawned_items(cooldown_until)
    WHERE cooldown_until IS NOT NULL;
```

---

## Open Questions

1. **Persistence Strategy**: Should quest state persist in database or Redis cache?
   - Database: Durable, slower
   - Redis: Fast, requires backup strategy

2. **Multi-Player Considerations**:
   - Should items disappear for all players when one collects?
   - Or should each player have their own instance?
   - Recommended: Per-player instances (better for quest progression)

3. **Respawn Mechanics**:
   - Should quest items respawn if player abandons quest?
   - Should there be a cooldown before respawn?
   - Recommended: No respawn until quest accepted again

4. **Item Ownership**:
   - Can multiple players collect the same item instance?
   - Recommended: Each player sees their own instance

5. **Performance**:
   - How many conditions can we check per AOI build without impacting performance?
   - Should we cache filtered AOI results?
   - Recommended: Cache AOI for 5-10 seconds per user

---

## Related Documentation

- [NPC Interaction System](npc-interaction-system.md)
- [Admin Command System](../concepts/deep-dives/dynamic-experiences/phase-1-mvp/000-admin-commands-quick-start.md)
- [Unified State Model](../reference/unified-state-model-deep-dive.md)
- [WebSocket AOI Protocol](websocket-aoi-client-guide.md)

---

## Next Steps

1. **Review this design** with team
2. **Choose initial approach** (recommend Phase 1: Visibility Toggle)
3. **Update world.json** with spawn_conditions for dream bottles
4. **Implement AOI filtering** in unified_state_manager.py
5. **Add basic quest system** (active quest tracking)
6. **Test with Unity** client
7. **Iterate** based on feedback

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

This document proposes a design for a quest-driven dynamic spawning system. The verification confirms that this design has **NOT** been implemented.

-   **✅ Option A (Visibility Toggle):** The basic mechanism for this option exists. The `visible` field is part of the item data structure, and the `@edit` command can modify it. However, the logic to tie this visibility to quest state is not implemented.
-   **❌ Option B (Dynamic Addition):** **NOT IMPLEMENTED**. The `UnifiedStateManager` does not have a dedicated method for dynamically adding new items to the world state at runtime based on quest triggers.
-   **❌ Option C (Condition-Based Filtering):** **NOT IMPLEMENTED**. The `build_aoi` method in `app/services/kb/unified_state_manager.py` does not contain any logic for filtering items based on a `spawn_conditions` field.

**Conclusion:** This document is a design proposal that has not been implemented. The current system does not have a mechanism for dynamically spawning or hiding items based on quest state. The proposed features, such as the `spawn_conditions` field and the corresponding filtering logic in the AOI builder, do not exist in the codebase.
