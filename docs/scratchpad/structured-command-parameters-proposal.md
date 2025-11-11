# Structured Command Parameters Proposal

**Date**: 2025-11-10
**Status**: Proposal
**Context**: Unity integration needs fast, predictable command format

---

## Problem Statement

Current command system requires natural language parsing for ALL commands, even simple ones like "go to spawn_zone_1". This causes:

1. **Slow response times**: 25-30 seconds (LLM processing)
2. **Fragile patterns**: "go to [location]" works, "go [location]" doesn't
3. **Unity friction**: Structured game clients prefer structured data
4. **Unnecessary complexity**: Simple navigation shouldn't need LLM interpretation

---

## Command Complexity Analysis

### Simple Commands (No LLM Needed)

**inventory** - Zero parameters
```json
// Current (works fine)
{"action": "inventory"}

// No change needed - already simple
```

**help** - Optional topic parameter
```json
// Current
{"action": "help movement"}

// Structured (optional)
{"action": "help", "topic": "movement"}
```

### Moderate Commands (Minimal LLM)

**look** - Optional target
```json
// Current
{"action": "look around"}

// Structured
{"action": "look"}  // General look
{"action": "look", "target": "bottle"}  // Examine specific item
```

**go** - Required destination
```json
// Current (SLOW - 25-30s LLM parsing)
{"action": "go to spawn_zone_1"}

// Structured (FAST - <100ms direct execution)
{"action": "go", "target": "spawn_zone_1"}
{"action": "go", "direction": "north"}
```

**collect** - Required item
```json
// Current (SLOW)
{"action": "collect dream bottle"}

// Structured (FAST)
{"action": "collect", "target": "dream_bottle_woander_1"}
{"action": "collect", "instance_id": "dream_bottle_woander_1"}  // Exact
```

### Complex Commands (LLM Required)

**talk** - NPC + freeform message
```json
// Current (LLM REQUIRED for natural conversation)
{"action": "talk to Louisa", "message": "Tell me about the dreams"}

// Structured base + natural message
{"action": "talk", "target": "louisa", "message": "Tell me about the dreams"}
// LLM still needed for message processing, but target extraction is fast
```

---

## Proposal: Hybrid Command System

### Architecture: Two-Path Execution

```python
async def process_command(user_id: str, experience: str, message: dict):
    action = message.get("action")

    # Path 1: Structured parameters (fast)
    if "target" in message or "direction" in message or "instance_id" in message:
        return await process_structured_command(message)

    # Path 2: Natural language (slower, immersive)
    else:
        return await process_natural_language_command(message)
```

### Path 1: Structured Commands (Fast)

**No LLM parsing needed** - Direct parameter extraction

```python
async def process_structured_command(message: dict):
    """Process commands with structured parameters (no LLM parsing)."""

    action = message["action"]

    if action == "go":
        destination = message.get("target") or message.get("direction")
        # Direct execution - no markdown parsing
        return await execute_go(destination)

    elif action == "collect":
        item_id = message.get("instance_id") or message.get("target")
        # Direct execution - no markdown parsing
        return await execute_collect(item_id)

    elif action == "look":
        target = message.get("target")
        # Direct execution - simple state query
        return await execute_look(target)

    # ... etc
```

**Response Time**: <100ms (no LLM involved)

### Path 2: Natural Language (Slow but Immersive)

**LLM markdown parsing** - For natural conversation

```python
async def process_natural_language_command(message: dict):
    """Process natural language commands (LLM parsing)."""

    action_text = message["action"]

    # Load markdown specification
    markdown_spec = load_command_spec(action_text)

    # LLM interprets natural language
    result = await llm.process(
        spec=markdown_spec,
        user_input=action_text,
        player_state=...,
        world_state=...
    )

    return result
```

**Response Time**: 25-30 seconds (LLM processing)

---

## Implementation Plan

### Phase 1: Modify Command Markdown (1-2 hours)

Update each command's markdown to support structured parameters:

#### Example: go.md

```markdown
## Input Parameters

**Structured format** (recommended for Unity/programmatic clients):
- `target` (string): Sublocation name (e.g., "spawn_zone_1")
- `direction` (string): Cardinal direction (e.g., "north", "south")

**Natural language format** (for immersive gameplay):
- Extract from action string: "go to [sublocation]", "go [direction]"

**Processing logic**:
1. Check if `target` or `direction` parameter exists
2. If yes → Use structured parameter (fast path)
3. If no → Parse action string with LLM (slow path)
```

#### Example: collect.md

```markdown
## Input Parameters

**Structured format**:
- `instance_id` (string): Exact item instance ID (e.g., "dream_bottle_woander_1")
- `target` (string): Item semantic name (e.g., "dream bottle")

**Natural language format**:
- Extract from action string: "collect [item]", "take [item]"

**Processing logic**:
1. Check if `instance_id` exists → Direct collection (fastest)
2. Check if `target` exists → Search for item by name (fast)
3. Else → Parse action string with LLM (slow)
```

### Phase 2: Update Command Processor (3-4 hours)

```python
# app/services/kb/command_processor.py

class CommandProcessor:
    async def process_command(
        self,
        user_id: str,
        experience: str,
        message: dict
    ) -> CommandResult:

        action = message.get("action")

        # Detect structured vs natural language
        has_structured_params = any(
            k in message for k in ["target", "direction", "instance_id", "topic"]
        )

        if has_structured_params:
            # FAST PATH: Direct execution
            return await self._execute_structured(message)
        else:
            # SLOW PATH: LLM parsing
            return await self._execute_natural_language(message)

    async def _execute_structured(self, message: dict):
        """Execute structured commands without LLM."""

        action = message["action"]

        if action == "go":
            return await self._go_structured(message)
        elif action == "collect":
            return await self._collect_structured(message)
        elif action == "look":
            return await self._look_structured(message)
        # ... etc

    async def _go_structured(self, message: dict):
        """Execute go command with structured parameters."""

        destination = message.get("target") or message.get("direction")

        # Load player state
        player_view = await self.state_manager.get_player_view(...)

        # Validate destination
        current_location = player_view["player"]["current_location"]
        location_data = await self.state_manager.get_location(current_location)

        if destination in location_data.get("sublocations", {}):
            # Valid sublocation
            await self.state_manager.update_player_state(
                path="player.current_sublocation",
                value=destination
            )

            return CommandResult(
                success=True,
                message=f"You move to {destination}",
                state_updates={...}
            )

        else:
            return CommandResult(
                success=False,
                error="destination_not_found",
                message=f"You don't see a way to {destination}"
            )
```

### Phase 3: Update Unity Client (Unity team, 2-3 hours)

```csharp
// Unity: Send structured commands
public void MoveTo(string sublocation) {
    var message = new {
        type = "action",
        action = "go",
        target = sublocation  // ← Structured parameter
    };

    websocket.Send(JsonUtility.ToJson(message));
}

public void CollectItem(string instanceId) {
    var message = new {
        type = "action",
        action = "collect",
        instance_id = instanceId  // ← Exact instance ID
    };

    websocket.Send(JsonUtility.ToJson(message));
}
```

### Phase 4: Maintain Backward Compatibility (30 min)

Ensure natural language still works:

```python
# Both formats supported
await process_command(user_id, experience, {
    "action": "go",
    "target": "spawn_zone_1"  # ← Fast (100ms)
})

await process_command(user_id, experience, {
    "action": "go to spawn_zone_1"  # ← Slow (25-30s) but still works
})
```

---

## Performance Comparison

### Current System (All Natural Language)

```
User sends: {"action": "go to spawn_zone_1"}
↓
LLM reads go.md (375 lines) - 5s
↓
LLM parses "go to spawn_zone_1" - 10s
↓
LLM extracts destination="spawn_zone_1" - 5s
↓
LLM validates and generates narrative - 10s
↓
Total: 25-30 seconds
```

### Proposed System (Structured Parameters)

```
User sends: {"action": "go", "target": "spawn_zone_1"}
↓
Python extracts target="spawn_zone_1" - <1ms
↓
Python validates sublocation exists - 10ms
↓
Python updates state - 20ms
↓
Python generates simple response - 50ms
↓
Total: <100ms (250x faster!)
```

---

## Benefits

### For Unity Client

1. **Predictable performance**: <100ms response time
2. **Structured data**: No string parsing needed
3. **Type safety**: Clear parameter contracts
4. **Reliable**: No pattern matching failures

### For Players (Still Works!)

1. **Natural language preserved**: "talk to Louisa, tell me about dreams" still works
2. **Immersive**: Can type freely for complex interactions
3. **No breaking changes**: Existing commands continue working

### For Server

1. **Faster responses**: 250x faster for simple commands
2. **Less LLM cost**: No LLM calls for structured commands
3. **Clearer code**: Explicit parameters vs. regex parsing
4. **Easier testing**: Unit test parameters vs. integration test NL patterns

---

## Command-by-Command Recommendations

| Command | Recommendation | Structured Parameters | Natural Language? |
|---------|---------------|----------------------|-------------------|
| **inventory** | ✅ Keep as-is | None needed | Optional aliases |
| **help** | ⚡ Add optional | `topic` (optional) | Still support NL |
| **look** | ⚡ Add optional | `target` (optional) | Still support NL |
| **go** | 🚀 **HIGH PRIORITY** | `target` or `direction` | Still support NL |
| **collect** | 🚀 **HIGH PRIORITY** | `instance_id` or `target` | Still support NL |
| **talk** | ⚡ Add structured | `target` (NPC), `message` | LLM still needed for message |

**Legend**:
- 🚀 High priority: Big performance gains
- ⚡ Optional: Nice to have
- ✅ No change: Already simple

---

## Testing Plan

### Test 1: Structured "go" Command

```python
# Test script: test_structured_go.py
async def test_structured_go():
    start = time.time()

    response = await send_websocket({
        "type": "action",
        "action": "go",
        "target": "spawn_zone_1"
    })

    elapsed = time.time() - start

    assert response["success"] == True
    assert elapsed < 1.0  # Should be <100ms, allow 1s buffer
    assert "spawn_zone_1" in response["message"]
```

**Expected**: <100ms response time ✅

### Test 2: Natural Language "go" Still Works

```python
async def test_natural_language_go():
    start = time.time()

    response = await send_websocket({
        "type": "action",
        "action": "go to spawn_zone_1"
    })

    elapsed = time.time() - start

    assert response["success"] == True
    assert elapsed > 10.0  # Natural language is slow
    assert elapsed < 60.0  # But completes within timeout
```

**Expected**: 25-30s response time (unchanged) ✅

### Test 3: Structured "collect" with instance_id

```python
async def test_structured_collect():
    start = time.time()

    # First, go to location (structured)
    await send_websocket({
        "action": "go",
        "target": "spawn_zone_1"
    })

    # Then collect with exact instance_id
    response = await send_websocket({
        "type": "action",
        "action": "collect",
        "instance_id": "dream_bottle_woander_1"
    })

    elapsed = time.time() - start

    assert response["success"] == True
    assert elapsed < 1.0  # Fast direct collection
    assert "world_update" event received
```

**Expected**: <100ms for collect, WorldUpdate event published ✅

---

## Migration Path

### Week 1: Server Implementation

**Day 1-2**: Update markdown specifications
- Modify go.md, collect.md, look.md
- Add "Structured Parameters" sections
- Document both formats

**Day 3-4**: Implement structured command processor
- Add parameter detection
- Add fast-path execution
- Maintain backward compatibility

**Day 5**: Testing
- Write unit tests for structured commands
- Verify natural language still works
- Performance testing

### Week 2: Unity Integration

**Day 1-2**: Unity client updates
- Update WebSocket message builders
- Use structured format for go/collect
- Test against local server

**Day 3**: Integration testing
- Unity → Server structured commands
- Verify <100ms response times
- Test edge cases

**Day 4-5**: Natural language UI (optional)
- Add chat input for immersive commands
- Route to structured vs. NL based on input

---

## Alternative Approaches Considered

### Option 1: Remove Natural Language Entirely

**Pros**: Simpler, faster, clearer
**Cons**: Loses immersive gameplay for complex interactions
**Decision**: ❌ Rejected - Natural language valuable for talk/complex commands

### Option 2: Keep All Natural Language

**Pros**: Consistent interface
**Cons**: 25-30s for simple navigation unacceptable
**Decision**: ❌ Rejected - Performance critical for Unity

### Option 3: Separate Endpoints

**Pros**: Clear separation
**Cons**: More complexity, two systems to maintain
**Decision**: ❌ Rejected - Hybrid approach better

### Option 4: Hybrid System (Proposed)

**Pros**: Fast for structured, immersive for natural
**Cons**: Two code paths to maintain
**Decision**: ✅ **ACCEPTED** - Best tradeoff

---

## Success Metrics

### Performance Targets

- **Structured go**: <100ms (currently 25-30s) ✅ 250x improvement
- **Structured collect**: <100ms (currently 25-30s) ✅ 250x improvement
- **Natural language preserved**: 25-30s (unchanged) ✅ Backward compatible

### Unity Integration

- **Response time**: <100ms for 90% of commands
- **Predictability**: 99% structured commands succeed
- **Developer experience**: Clear API, typed parameters

---

## Recommendation

✅ **IMPLEMENT HYBRID SYSTEM**

**Why**:
1. **Unity needs speed**: 25-30s unacceptable for game clients
2. **Players need immersion**: "talk to Louisa, tell me about dreams" valuable
3. **Low risk**: Backward compatible, incremental rollout
4. **High value**: 250x performance improvement for common commands

**Timeline**: 2 weeks
**Effort**: ~15-20 hours total
**Impact**: Enables Unity integration, improves UX

---

## Related Documentation

- `docs/scratchpad/markdown-command-architecture.md` - Current system architecture
- `docs/scratchpad/websocket-aoi-client-guide.md` - Unity WebSocket protocol
- `/Vaults/gaia-knowledge-base/.../game-logic/*.md` - Command specifications

---

## Next Steps

1. **Approval**: Review proposal with team
2. **Spike**: 2-hour proof of concept for "go" command
3. **Implementation**: Full implementation if spike successful
4. **Testing**: Validate performance targets
5. **Unity Integration**: Coordinate with Unity team

**Contact**: Discuss in Symphony `websockets` room
