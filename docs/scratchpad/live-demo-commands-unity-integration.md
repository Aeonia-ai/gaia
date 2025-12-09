# Live Demo Commands: Unity Integration

**Date**: 2025-11-18
**Status**: ✅ Production Ready
**Purpose**: Demo script showcasing real-time AR/VR capabilities with Unity client integration

---

## 🎯 Demo Overview

**Target Audience**: Technical stakeholders, investors, game developers
**Duration**: 2-5 minutes (scalable)
**Requirements**: Unity client running, admin@aeonia.ai logged in, server healthy

**What This Demo Shows**:
- ✅ Sub-second response times (4.5-30ms command handlers)
- ✅ Real-time Unity UI updates (inventory, world objects)
- ✅ Delta-based state synchronization (no version conflicts)
- ✅ Live world manipulation from command line
- ✅ Multi-system integration (inventory, movement, NPCs, quests)

---

## 🎬 5-Minute Full Demo Script

### **Setup Verification** (30 seconds)

```bash
# 1. Verify all services healthy
docker compose ps
# Expected: All services "Up" and healthy

# 2. Check Unity client connected
docker logs gaia-kb-service-1 --tail 20 | grep "WebSocket connected"
# Expected: Recent connection log for admin@aeonia.ai

# 3. Verify starting state
./scripts/experience/check-inventory.sh da6dbf22-3209-457f-906a-7f5c63986d3e
# Expected: 2 bottles in inventory
```

**Unity Check**: Player standing in woander_store/main_room

---

### **Act 1: Real-Time Inventory & World State** (90 seconds)

**Talking Point**: *"Watch how the AR world responds in real-time to server commands"*

```bash
# 1. Show current inventory state
./scripts/experience/test-fast-inventory.sh
# Expected: "You have: Bottle of Nature, Bottle of Joy"
# Unity: Inventory UI shows 2 bottles

# 2. Drop first bottle (inventory → world)
./scripts/experience/test-fast-drop.sh bottle_joy
# Expected: "You dropped Bottle of Joy." [<20ms response]
# Unity:
#   - Bottle GameObject spawns at player location
#   - Inventory UI updates: 2 → 1 bottle
#   - No version mismatch errors in console

# 3. Drop second bottle (show multiple world objects)
./scripts/experience/test-fast-drop.sh bottle_nature
# Expected: "You dropped Bottle of Nature."
# Unity:
#   - Second bottle spawns in world
#   - Inventory UI updates: 1 → 0 bottles

# 4. Inspect world state (show items in area)
./scripts/experience/inspect-world.sh
# Expected: Both bottles listed under woander_store/main_room/items

# 5. Collect both bottles back (world → inventory)
./scripts/experience/test-fast-collect.sh bottle_joy
# Expected: "You collected Bottle of Joy." [4.5ms response]
# Unity:
#   - bottle_joy GameObject despawns
#   - Inventory UI updates: 0 → 1

./scripts/experience/test-fast-collect.sh bottle_nature
# Expected: "You collected Bottle of Nature."
# Unity:
#   - bottle_nature GameObject despawns
#   - Inventory UI updates: 1 → 2

# 6. Verify final state matches starting state
./scripts/experience/check-inventory.sh da6dbf22-3209-457f-906a-7f5c63986d3e
# Expected: 2 bottles back in inventory
```

**Key Demo Points**:
- **Response Time**: Commands return in 4.5-20ms (1,250x faster than LLM path)
- **UI Updates**: Unity inventory count changes immediately
- **World Objects**: Bottles spawn/despawn in AR view
- **No Errors**: Zero version mismatch warnings in Unity console

---

### **Act 2: Fast Movement & Location Updates** (60 seconds)

**Talking Point**: *"Delta-based updates mean only changed data is transmitted"*

```bash
# 1. Move to different location
./scripts/experience/test-fast-go.sh clearing
# Expected: "You moved to The Clearing." [<30ms response]
# Unity:
#   - AOI update event received
#   - Zone changes from woander_store to clearing
#   - Available items change (dream bottles visible)
#   - Player position updates

# 2. Move back to shop
./scripts/experience/test-fast-go.sh woander_store
# Expected: "You moved to Woander's Dream Bottle Shop."
# Unity:
#   - Zone switches back
#   - Shop items visible again
#   - Clearing items despawn
```

**Key Demo Points**:
- **AOI (Area of Interest)**: Only relevant zone data sent to client
- **Delta Updates**: Incremental changes, not full world state
- **Sub-Second Response**: Movement feels instant in AR

---

### **Act 3: Admin Commands - Live World Building** (90 seconds)

**Talking Point**: *"Developers can inspect and modify the live world without restarting"*

```bash
# 1. List all waypoints in the experience
echo '{"type": "action", "action": "@list-waypoints"}' | \
  ./scripts/gaia_client.py --user admin@aeonia.ai --experience wylding-woods
# Expected: JSON list of 37 waypoints with GPS coordinates
# Response time: <30ms (no LLM)

# 2. Inspect specific waypoint details
echo '{"type": "action", "action": "@inspect-waypoint woander_store"}' | \
  ./scripts/gaia_client.py --user admin@aeonia.ai --experience wylding-woods
# Expected: Full waypoint data (location, areas, items, NPCs)
# Shows: Main quest bottles, Woander NPC, spawn zones

# 3. Inspect world state (alternative admin view)
./scripts/experience/inspect-world.sh
# Expected: Complete world state with all locations, items, NPCs
```

**Key Demo Points**:
- **Admin Commands**: `@` prefix for instant world inspection
- **No Restart Required**: Live world configuration
- **<30ms Response**: Admin ops as fast as player commands

---

### **Act 4: Rapid State Changes** (60 seconds)

**Talking Point**: *"Version management prevents conflicts during rapid updates"*

```bash
# Rapid drop/collect cycle (stress test version system)
./scripts/experience/test-fast-drop.sh bottle_joy && \
./scripts/experience/test-fast-collect.sh bottle_joy && \
./scripts/experience/test-fast-drop.sh bottle_nature && \
./scripts/experience/test-fast-collect.sh bottle_nature

# Expected: All 4 commands succeed without version errors
# Unity: Processes all 4 deltas sequentially, UI updates smoothly
```

**Key Demo Points**:
- **Version Lock Prevention**: Fixed in v0.4 protocol
- **Delta Batching**: Multiple updates don't cause conflicts
- **Smooth UI**: No visual glitches from rapid state changes

---

### **Act 5: NPC Interaction** (Optional - 90 seconds)

**Talking Point**: *"NPCs use LLMs for authentic dialogue with relationship tracking"*

```bash
# 1. Talk to Louisa (Dream Weaver fairy)
echo '{"type": "action", "action": "talk to louisa Hey Louisa, what dreams are you collecting?"}' | \
  ./scripts/gaia_client.py --user admin@aeonia.ai --experience wylding-woods
# Expected: LLM-generated dialogue (1-3s response)
# Louisa responds in-character about dream bottle collection

# 2. Check trust level (relationship progression)
./scripts/experience/inspect-world.sh | grep -A 10 '"louisa"'
# Expected: Shows trust level (0-100), conversation history

# 3. Accept quest (if trust is high enough)
echo '{"type": "action", "action": "accept quest from louisa"}' | \
  ./scripts/gaia_client.py --user admin@aeonia.ai --experience wylding-woods
# Expected: Quest added to player's quest_states
```

**Key Demo Points**:
- **AI-Powered NPCs**: Natural language conversations
- **Trust System**: Relationships affect quest availability
- **State Persistence**: Trust/quests saved to player view

---

## 🚀 Quick 2-Minute Demo (Copy-Paste)

**For time-constrained demos:**

```bash
# 1. Real-time inventory manipulation
./scripts/experience/test-fast-drop.sh bottle_joy      # Watch Unity spawn bottle
./scripts/experience/test-fast-collect.sh bottle_joy    # Watch Unity despawn bottle

# 2. Fast movement
./scripts/experience/test-fast-go.sh clearing          # Watch Unity load new zone
./scripts/experience/test-fast-go.sh woander_store     # Watch Unity return to shop

# 3. Admin inspection
./scripts/experience/inspect-world.sh                  # Show complete world state

# 4. Rapid updates (stress test)
./scripts/experience/test-fast-drop.sh bottle_nature && \
./scripts/experience/test-fast-collect.sh bottle_nature
```

**Total Time**: ~2 minutes
**Commands**: 7 total
**Systems Shown**: Inventory, movement, admin commands, version management

---

## 📊 Performance Metrics (For Technical Audiences)

### Command Response Times

| Command | Handler | Response Time | LLM Used? |
|---------|---------|---------------|-----------|
| `drop <item>` | `handle_drop_item()` | <20ms | ❌ No |
| `collect <item>` | `handle_collect_item()` | 4.5ms | ❌ No |
| `go <location>` | `handle_go()` | <30ms | ❌ No |
| `inventory` | `handle_inventory()` | <10ms | ❌ No |
| `@list-waypoints` | `handle_admin_list_waypoints()` | <30ms | ❌ No |
| `@inspect-waypoint` | `handle_admin_inspect_waypoint()` | <30ms | ❌ No |
| `talk to <npc>` | LLM-powered | 1-3s | ✅ Yes |

### End-to-End Latency (Command → Unity UI Update)

- **Best Case**: ~45ms (server processing + network + Unity)
- **Typical**: ~60-80ms
- **Worst Case**: ~100ms (complex deltas, many objects)

### Event Publishing Latency

- NATS publish: <2ms
- NATS → WebSocket forward: <10ms
- Unity delta application: ~5-15ms
- Unity GameObject updates: ~10-20ms
- **Total pipeline**: <50ms server-side

---

## 🎯 Demo Talking Points

### **Technical Architecture Highlights**

**1. Hybrid Command Routing**:
- Simple commands (drop, collect, go): Direct Python handlers (4.5-30ms)
- Complex commands (talk, examine): LLM-powered (1-3s)
- Single routing decision per command (intelligent_chat_routing.py)

**2. Version Management**:
- Snapshot versions track state changes
- Base version + delta model prevents conflicts
- Fixed in v0.4: AOI uses player_view's snapshot_version

**3. Delta-Based Updates**:
- Only changed data transmitted to clients
- Operations: add, remove, update
- Unity applies deltas incrementally (no full state sync)

**4. Type-Based Filtering**:
- Items tagged with `type: "collectible"`
- Unity filters inventory: `item.Type == "collectible"`
- Enables category-based UI (bottles, weapons, tools, etc.)

**5. NATS Pub/Sub**:
- User-specific subjects: `world.updates.user.{user_id}`
- WebSocket forwards NATS events to clients
- Verified working with comprehensive debug logging

### **System Capabilities**

✅ **Git-Synchronized Knowledge Bases**:
- World templates stored in Git
- Auto-sync with Obsidian vaults
- Version control for game content

✅ **Per-Player State Isolation**:
- Each player has private view.json
- Shared world state + individual progress
- No cross-player data leakage

✅ **Admin Command System**:
- `@` prefix for developer commands
- Zero LLM latency (<30ms)
- Live world inspection/modification

✅ **NPC Dialogue System**:
- LLM-powered authentic conversations
- Trust level (0-100) tracks relationships
- Quest availability gated by trust

✅ **Quest System**:
- State persistence in player view
- Event-driven progression
- NPC integration for quest givers

---

## 🔍 What to Watch in Unity Console

### Expected Logs (Successful Demo)

```
✓ WebSocket connected to server
✓ Initial AOI received: zone=woander_store, snapshot_version=1763428712288
✓ Inventory updated: 2 bottles out of 2 total items
✓ World update received: type=world_update, changes=1
✓ Delta applied: base_version=1763428712288, new_version=1763428720001
✓ GameObject spawned: bottle_joy at position (x, y, z)
✓ Inventory updated: 1 bottles out of 1 total items
```

### Red Flags (Problems)

```
❌ Version mismatch - delta buffered (base: 100, current: 102)
❌ Cannot add item bottle_joy: already exists in main_room
❌ Inventory filter returned 0 items (missing type field)
❌ WebSocket disconnected: connection refused
❌ NATS event not received (forwarding issue)
```

---

## 🛠️ Troubleshooting During Demo

### Issue: Unity Not Receiving Updates

**Quick Diagnosis**:
```bash
# Check if server publishing events
docker logs gaia-kb-service-1 --tail 50 | grep "Published world_update"

# Check if WebSocket connected
docker logs gaia-kb-service-1 --tail 50 | grep "WebSocket connected"
```

**Likely Causes**:
1. Unity client not connected to WebSocket
2. NATS subscription not active
3. Unity message handler not processing world_update type

### Issue: Version Mismatch Errors

**Quick Fix**: Restart Unity client to get fresh AOI with correct version

**Root Cause**: AOI version != player_view version (fixed in v0.4)

### Issue: Inventory Shows 0 Bottles

**Quick Diagnosis**:
```bash
# Check if bottles have type field
cat /kb/players/da6dbf22-3209-457f-906a-7f5c63986d3e/wylding-woods/view.json | \
  jq '.player.inventory[0].type'
# Expected: "collectible"
```

**Fix**: Reset experience to apply world.template.json with type fields

---

## 📚 Related Documentation

- `command-line-testing-drop-collect.md` - Detailed testing guide for drop/collect
- `websocket-aoi-client-guide.md` - WebSocket protocol v0.4 specification
- `admin-command-architecture-and-reset.md` - Admin command system and reset behavior
- `fast-go-command-complete.md` - Movement command implementation

---

## 🎬 Pre-Demo Checklist

**Before Starting Demo**:

- [ ] All Docker services healthy (`docker compose ps`)
- [ ] Unity client connected and showing game world
- [ ] Player at woander_store/main_room location
- [ ] Player has 2 bottles in inventory (bottle_nature, bottle_joy)
- [ ] No version mismatch errors in Unity console
- [ ] Background event monitor running (optional): `./scripts/experience/monitor-all-events.sh`

**Reset to Clean State** (if needed):
```bash
./scripts/experience/reset-experience.sh
# Expected: All 4 bottles restored to world, player views cleared
```

---

## 💡 Demo Tips

**Timing**:
- Pause 2-3 seconds between commands for Unity to render updates
- Let stakeholders see the UI change before next command
- For rapid demo, chain commands with `&&`

**Narration**:
- Call out response times: "That was 4.5 milliseconds"
- Point to Unity screen: "Watch the inventory UI in the top-right"
- Explain what's happening: "Server published a delta, Unity applied it"

**Failure Recovery**:
- If command fails, show troubleshooting: `inspect-world.sh`
- Explain error messages: "Version mismatch means..."
- Reset if needed: "Let me restore to clean state"

**Technical Deep Dive** (if audience is technical):
- Show NATS events: `./scripts/experience/monitor-all-events.sh`
- Display player view JSON: `cat /kb/players/.../view.json | jq`
- Explain version management: "AOI snapshot_version matches delta base_version"

---

## 🎯 Key Takeaways for Stakeholders

**For Investors**:
- Sub-second response times enable real-time AR/VR gameplay
- Git-synchronized content means rapid iteration (no app updates)
- AI-powered NPCs create dynamic, engaging experiences

**For Developers**:
- Fast command handlers bypass LLM latency (4.5ms vs 1-3s)
- Admin commands enable live debugging without restarts
- WebSocket protocol v0.4 prevents version conflicts

**For Game Designers**:
- Natural language NPC interactions feel authentic
- Trust system creates emergent gameplay (relationship progression)
- Quest system integrates seamlessly with world state

**For Technical Architects**:
- Delta-based updates minimize bandwidth (mobile-friendly)
- Per-player state isolation enables massive multiplayer
- NATS pub/sub scales horizontally (add more servers)

---

## 🔮 Future Demo Enhancements

**Potential Additions** (not yet implemented):

- Multi-player demo (two clients seeing each other's actions)
- Voice-to-text NPC conversations (mobile AR use case)
- Real-time location sync (GPS-based player movement)
- Quest completion flow (show full quest lifecycle)
- Leaderboards and achievements (social features)

---

**Last Updated**: 2025-11-18
**Tested With**: Unity 2022.3 LTS, GAIA Platform v0.4
**Status**: ✅ Production Ready - All commands verified working
