# Wylding Woods - Game World Architecture

## Overview

The Wylding Woods experience demonstrates GAIA's **hybrid GPS + VPS positioning model** for MMOIRL games. Players navigate between outdoor GPS waypoints and explore detailed VPS-scanned indoor environments with centimeter-precision positioning.

**Current Status**: Phase 1 (Demo Scope) - Single VPS in-store experience at Woander's Magical Shop
**Target Date**: December 15, 2025 demo
**Architecture**: Unified experience system using `state/world.json`

---

## Architecture Model

### Spatial Hierarchy

```
Zone (GPS Region)
  └─ Venue (GPS Waypoint) ← VPS scan boundary
      └─ Area (VPS sublocation)
          └─ Point (Transform anchor)
```

### Positioning Systems

- **GPS Navigation**: Movement between outdoor waypoints (5-10m accuracy)
- **VPS Navigation**: Movement within indoor locations (1-2cm accuracy using Niantic Lightship)
- **Transform Anchors**: Named positions in VPS scans (e.g., "fairy-door-main", "spawn_zone_1")

### State Model

- **Shared World State**: Multiplayer-visible locations, NPCs, items (`state/world.json`)
- **Player State**: Personal inventory, quest progress, per-player NPC relationships (`players/{user_id}/state.json`)

---

## Woander's Magical Shop (woander_store)

**Location Type**: GPS Waypoint + VPS Interior
**GPS Coordinates**: (Configured in Unity)
**VPS Scan**: Entire shop interior with 14 transform anchors

### Sublocations (VPS Areas)

1. **entrance** - Store Entrance
   - Welcome sign (non-collectible)
   - First area players see when VPS localizes

2. **counter** - Shop Counter
   - Woander the shopkeeper (blue elf NPC)
   - Shelves with dream bottles behind counter

3. **fairy_door_main** - Main Fairy Door ⭐ **DEMO FOCUS**
   - Louisa the Dream Weaver fairy (NPC)
   - Tiny ornate door with spiral carvings
   - Primary demo interaction point

4. **spawn_zone_1** - Display Shelf Area
   - Dream bottle: "peaceful dream bottle" (spiral symbol)
   - First collection point for scavenger hunt

5. **spawn_zone_2** - Window Display
   - Dream bottle: "adventurous dream bottle" (star symbol)
   - Second collection point

6. **spawn_zone_3** - Corner Nook
   - Dream bottle: "joyful dream bottle" (moon symbol)
   - Third collection point

7. **spawn_zone_4** - Book Alcove
   - Dream bottle: "whimsical dream bottle" (sun symbol)
   - Fourth collection point

8. **fairy_house_spiral** - Spiral Fairy House
   - Return point for spiral-symbol bottle
   - Matches peaceful dreams

9. **fairy_house_star** - Star Fairy House
   - Return point for star-symbol bottle
   - Matches adventurous dreams

10. **fairy_house_moon** - Moon Fairy House
    - Return point for moon-symbol bottle
    - Matches joyful dreams

11. **fairy_house_sun** - Sun Fairy House
    - Return point for sun-symbol bottle
    - Matches whimsical dreams

12. **back_room** - Back Storage Room
    - Cluttered with magical inventory
    - Future content area

### NPCs

#### Woander
- **Type**: Shopkeeper fairy (blue elf)
- **Location**: counter
- **Personality**: Cheerful, welcoming, business-focused
- **Role**: Store proprietor, introduces shop mechanics
- **Dialogue**:
  - Greeting: "Welcome to Woander's! I'm Woander, and this is my magical shop. Looking for something special today?"
  - Browse: "Feel free to look around! We have dream bottles, fairy dust, and other enchanted items."
  - Farewell: "Come back soon! May your dreams be magical!"

#### Louisa the Dream Weaver ⭐ **DEMO FOCUS**
- **Type**: Dream Weaver fairy (Cloud Magic)
- **Location**: fairy_door_main
- **Personality**: Gentle, anxious, hopeful, worried about Neebling
- **Role**: Quest giver, emotional center of demo
- **Dialogue**:
  - Greeting: "Princess Eliška, is that you? Oh... you're not the princess. I'm Louisa, and I need your help!"
  - Quest intro: "Neebling, that mischievous blue elf, has mixed up our dreams again! Can you help me find the dream bottles?"
  - Quest active: "The bottles each have a symbol - return them to the matching fairy houses!"
  - Thanks: "Thank you so much for helping us recover our dreams!"

**NPC State Tracking** (per player):
- `greeting_given`: Whether first greeting has been shown
- `trust_level`: 0-100 relationship score (future: gates advanced content)
- `quest_active`: Whether scavenger hunt is active
- `bottles_collected`: Count of bottles returned

---

## Experience Flow

### Phase 1: Demo Scope (December 15, 2025)

**Goal**: Prove the "magical moment" - talking to a tiny fairy through VPS

**Steps**:
1. Story Ranger introduces Princess Eliška's "scrying mirror" (iPad)
2. Player scans visual code to initialize VPS localization
3. Player navigates to fairy door: `"go to fairy door main"`
4. Player looks around: `"look around"`
5. Player initiates conversation: `"talk to Louisa"`
6. Louisa responds with quest introduction
7. **Demo ends** - Phase 2 content is shown but not required

**Technical Requirements**:
- VPS scan of Woander store (complete)
- Transform anchor: "fairy-door-main" (configured)
- Louisa NPC at fairy_door_main sublocation ✅
- Natural language conversation system ✅
- Push-to-Talk UI in Unity (in progress)

### Phase 2: Full Scavenger Hunt (Post-Demo)

**Goal**: Complete gameplay loop with item collection and symbol matching

**Steps**:
1. Player accepts quest from Louisa
2. Navigate to spawn zones: `"go to display shelf"`, etc.
3. Collect dream bottles: `"take the peaceful dream bottle"`
4. Check inventory: `"check my inventory"`
5. Navigate to fairy houses: `"go to spiral fairy house"`
6. Return bottles: `"return the peaceful dream bottle"`
7. Repeat for all 4 bottles
8. Return to Louisa for completion dialogue

**Game Mechanics**:
- **Symbol Matching**: Each bottle has a symbol (spiral/star/moon/sun) that must match its fairy house
- **Inventory Management**: Players carry bottles in personal inventory
- **Quest Progression**: Global state tracks `dream_bottles_found` and `dream_bottles_required`
- **Completion Celebration**: Fairies celebrate when all bottles are returned

---

## Player State & Inventory

### Bootstrap Starting Inventory

When a new player first interacts with Wylding Woods, they receive:
- **4 dream bottles** (one of each type)
- **Fairy dust** (consumable item)

This is defined in `player-config.json` and ensures players can immediately engage with content.

### Persistent State

**Player state persists across sessions** - inventory, quest progress, and NPC relationships are saved to:
```
/Vaults/gaia-knowledge-base/players/{user_id}/wylding-woods/state.json
```

**Resetting Player State**:
- **Admin command**: `@reset player {user_id} CONFIRM` (requires admin permissions)
- **Manual deletion**: `rm -rf /Vaults/gaia-knowledge-base/players/{user_id}/`

---

## Technical Implementation

### File Structure

```
experiences/wylding-woods/
├── state/
│   └── world.json                    # Shared multiplayer world state
├── game-logic/
│   ├── look.md                       # Look/observe command
│   ├── go.md                         # Navigation command
│   ├── take.md                       # Item collection command
│   ├── talk.md                       # NPC conversation command
│   └── return.md                     # Item return command
├── admin-logic/
│   ├── @reset-experience.md          # Admin reset command
│   ├── @inspect-waypoint.md          # Admin inspection tools
│   └── ...
├── player-config.json                # Bootstrap inventory
└── waypoints/
    └── *.md                          # GPS waypoint definitions
```

### API Endpoint

**POST** `/experience/interact`

```json
{
  "experience": "wylding-woods",
  "message": "go to fairy door main",
  "user_id": "player@example.com"
}
```

**Response**:
```json
{
  "success": true,
  "narrative": "You approach the main fairy door...",
  "available_actions": ["look around", "talk to Louisa", "go back"],
  "metadata": {
    "location": "woander_store",
    "sublocation": "fairy_door_main"
  }
}
```

### Two-Pass LLM Execution

1. **Pass 1**: Logic determination (JSON output)
   - Parse player intent
   - Validate action against game rules
   - Determine state changes

2. **Pass 2**: Narrative generation (text output)
   - Generate in-character response
   - Describe scene and actions
   - Provide contextual hints

### Navigation Commands

**Within Location** (VPS navigation):
```
"go to fairy door main"
"go to display shelf"
"go to spiral fairy house"
```

**Between Locations** (GPS navigation - future):
```
"go to waypoint 28a"
"go to clearing"
```

---

## Testing

### Test Files

Located in `scripts/experience-validation/wylding-woods/`:

- **validate_woander_store_journey.py** - Complete 26-step journey test (Phase 1 + Phase 2)
- **validate_e2e_journey.py** - Single-waypoint navigation and NPC interaction
- **interactive_play.py** - Human-driven REPL for manual testing
- **test_waypoint_api.py** - Unit tests for waypoint lookup endpoint

### Testing Approach

**Incremental curl testing** (recommended):
```bash
# Test navigation
curl -X POST http://localhost:8001/experience/interact \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {API_KEY}" \
  -d '{"experience": "wylding-woods", "message": "look around", "user_id": "test@test.com"}'

# Test NPC interaction
curl -X POST http://localhost:8001/experience/interact \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {API_KEY}" \
  -d '{"experience": "wylding-woods", "message": "talk to Louisa", "user_id": "test@test.com"}'
```

### Test Data Cleanup

**Reset test user state**:
```bash
rm -rf /Users/jasonasbahr/Development/Aeonia/Vaults/gaia-knowledge-base/players/test-user@test.com
```

---

## Future Work

### Immediate (Pre-Demo)
- [ ] Unity VPS scan integration
- [ ] Push-to-Talk conversation UI
- [ ] Animation states for Louisa (idle, greeting, quest-active)
- [ ] Particle effects for dream bottles

### Post-Demo (Phase 2)
- [ ] Complete scavenger hunt implementation
- [ ] Symbol matching validation
- [ ] Quest completion celebration sequence
- [ ] Additional fairy house interactions

### Long-Term
- [ ] Multiple GPS waypoints (outdoor exploration)
- [ ] Weather-based gameplay mechanics
- [ ] Timed events and seasonal content
- [ ] Social features (multiplayer bottle trading)

---

## Related Documentation

- [Clean Slate Architecture](../../Vaults/kb/users/jason@aeonia.ai/mmoirl-actual/working/clean-slate-architecture-2025-10-31.md) - Complete spatial hierarchy design
- [In-Store Experience Specification](../../Vaults/kb/users/jason@aeonia.ai/mmoirl/experiences/wylding-woods/20-in-store-experience-specification.md) - 1600+ line technical spec
- [Demo Script](../../Vaults/kb/users/jason@aeonia.ai/mmoirl/experiences/wylding-woods/demo-script.md) - Narrative flow and dialogue
- [Demo Todos](../../Vaults/kb/users/jason@aeonia.ai/mmoirl/experiences/wylding-woods/2025-10-25-142856-louisa-demo-todos.md) - December 15 milestone tracking

---

## Key Design Decisions

### Why Hybrid GPS + VPS?

- **GPS**: Scalable outdoor exploration without creating every square meter
- **VPS**: Magical precision experiences at key venues (1-2cm accuracy)
- **Hybrid**: Best of both worlds - exploration at scale with curated moments

### Why Single Location for Demo?

- **Scope Management**: Proving one magical moment is better than half-finishing multiple
- **Technical Risk**: VPS is new - focus on getting one location perfect
- **Narrative Focus**: Louisa's emotional story needs no dilution

### Why Symbol Matching Mechanic?

- **Spatial Exploration**: Forces players to explore entire VPS environment
- **Pattern Recognition**: Accessible puzzle mechanic for all ages
- **Emergent Gameplay**: Players can collect in any order, return in any order

---

**Last Updated**: 2025-11-01
**Status**: Phase 1 (Demo) ready for Unity integration
**Maintainer**: Jason Bahr (jason@aeonia.ai)
