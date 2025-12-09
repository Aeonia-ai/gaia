# Manual Tests

This directory contains manual testing scripts for validating system behavior that requires human observation or multi-terminal coordination.

## Purpose

Manual tests are used when:
- Testing requires observing real-time events across multiple terminals
- Validating interactive behavior (SSE streaming, NATS pub/sub)
- Debugging integration issues before automating tests
- Exploratory testing of new features

These are NOT automated test suites - they require manual execution and observation.

## Available Tests

### `get_test_jwt.py`

**Purpose**: Generate test JWT tokens for authentication in manual tests.

**Usage**:
```bash
# Get JWT token for pytest@aeonia.ai (test user)
JWT_TOKEN=$(python3 tests/manual/get_test_jwt.py 2>/dev/null | tail -1)

# Use in curl/scripts
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8001/api/endpoint
```

**Output**: Prints JWT token to stdout (stderr contains auth details).

---

### `test_websocket_experience.py`

**Purpose**: Validate WebSocket real-time experience interactions for the AEO-65 demo (Friday deadline).

**What It Tests**:
- WebSocket connection with JWT authentication
- Bottle collection mechanics (hardcoded demo actions)
- NATS world_update event reception
- Quest progression (bottle quest demo)
- Connection lifecycle (ping/pong, graceful shutdown)

**Requirements**:
- Docker services running (`docker compose up`)
- KB Service with WebSocket endpoint at `ws://localhost:8001/ws/experience`
- Test user created in Supabase (`pytest@aeonia.ai`)

**Usage**:
```bash
# Basic run (auto-fetches JWT token)
python3 tests/manual/test_websocket_experience.py --url ws://localhost:8001/ws/experience

# With explicit token
JWT_TOKEN=$(python3 tests/manual/get_test_jwt.py 2>/dev/null | tail -1)
python3 tests/manual/test_websocket_experience.py --url ws://localhost:8001/ws/experience --token "$JWT_TOKEN"

# Test remote deployment
python3 tests/manual/test_websocket_experience.py --url wss://gaia-kb-dev.fly.dev/ws/experience
```

**What to Validate**:
- ✅ WebSocket connects with JWT auth (query param: `?token=...&experience=wylding-woods`)
- ✅ Welcome message received with connection_id and user_id
- ✅ Ping/pong heartbeat works
- ✅ Bottle collection succeeds (action response with success=true)
- ✅ Quest updates received (progress tracking)
- ✅ NATS world_update events arrive (<100ms latency)
- ⚠️ First-run player initialization (may show "Player view not found" error once)

**Current Limitations** (AEO-65 Demo - Fixed Post-Demo):
- **Only 3 hardcoded actions**: `collect_bottle`, `drop_item`, `interact_object`
- **No natural language commands**: `help`, `talk`, `look`, `go`, etc. NOT supported
- **No LLM processing**: Bypasses markdown-driven command system for speed
- **HTTP endpoint required** for complex interactions (talk to NPCs, help commands)

**Post-Demo**: Command Bus architecture will unify HTTP and WebSocket (see `docs/scratchpad/command-system-refactor-proposal.md`)

**Expected Output**:
```
🔗 Connecting to WebSocket: ws://localhost:8001/ws/experience
✅ WebSocket connected successfully!
📨 Welcome message received
🏓 Sending ping...
✅ Pong received
🍾 Collecting first bottle (bottle_of_joy_1)...
   ✅ Action response: success=True
   🎯 Quest update: 1/7 bottles
🍾 Collecting bottle 2...
   🎯 Progress: 2/7 (status: in_progress)
...
✅ ALL TESTS PASSED
```

**Troubleshooting**:
```bash
# Check WebSocket endpoint is running
docker compose logs kb-service | grep "WebSocket"

# Verify JWT token is valid
python3 tests/manual/get_test_jwt.py

# Test with verbose output
python3 tests/manual/test_websocket_experience.py --url ws://localhost:8001/ws/experience -v

# Check player state files
ls -la /data/repository/experiences/wylding-woods/players/

# Reset player state if needed
rm /data/repository/experiences/wylding-woods/players/b18c47d8-3bb5-46be-98d4-c3950aa565a5/*
```

**Alternative Testing Methods**:

Using `websocat` (interactive):
```bash
# Install websocat
brew install websocat

# Get JWT and connect
JWT=$(python3 tests/manual/get_test_jwt.py 2>/dev/null | tail -1)
websocat "ws://localhost:8001/ws/experience?experience=wylding-woods&token=$JWT"

# Type commands (JSON):
{"type": "ping"}
{"type": "action", "action": "collect_bottle", "item_id": "bottle_of_joy_1"}
```

Using Python one-liner:
```python
python3 << 'EOF'
import asyncio, websockets, json

async def test():
    token = "YOUR_JWT"
    uri = f"ws://localhost:8001/ws/experience?experience=wylding-woods&token={token}"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"type": "action", "action": "collect_bottle", "item_id": "bottle_1"}))
        print(await ws.recv())

asyncio.run(test())
EOF
```

---

### `test_nats_subscriber.py`

**Purpose**: Validate NATS world_update event publishing from KB Service (Phase 1 implementation).

**Requirements**:
- Docker services running (`docker compose up`)
- NATS container accessible at `localhost:4222`
- KB Service configured to publish world_update events

**Usage**:
```bash
# Terminal 1: Run subscriber
python tests/manual/test_nats_subscriber.py

# Terminal 2: Trigger state changes
./scripts/test.sh --local chat "take dream bottle"

# Observe events in Terminal 1
```

**What to Validate**:
- ✅ Events arrive within sub-100ms of state change
- ✅ Event payload matches WorldUpdateEvent schema
- ✅ Subject includes correct user_id: `world.updates.user.{user_id}`
- ✅ Changes delta contains expected state updates
- ✅ Graceful degradation if NATS is down

**Troubleshooting**:
```bash
# Check NATS container status
docker compose ps nats

# Check NATS logs
docker compose logs nats

# Test NATS connectivity
docker compose exec nats nats server check connection
```

---

### `test_nats_sse_integration.py`

**Purpose**: Validate end-to-end NATS + SSE streaming integration (Phase 1B).

**What It Tests**:
- SSE stream establishment from Chat Service
- NATS world_update event subscription during stream
- Real-time event forwarding to SSE clients
- Latency measurement (<200ms target)
- Multi-user event isolation

**Requirements**:
- Docker services running (`docker compose up`)
- Chat Service with SSE streaming at `http://localhost:8002`
- KB Service publishing NATS events
- NATS container accessible

**Usage**:
```bash
# Run integration test
python3 tests/manual/test_nats_sse_integration.py

# Test specific user
python3 tests/manual/test_nats_sse_integration.py --user-id "specific-user-uuid"
```

**What to Validate**:
- ✅ SSE stream connects and receives events
- ✅ NATS events forwarded to correct SSE stream
- ✅ Latency <200ms from KB state change to SSE client
- ✅ Event filtering by user_id (isolation)
- ✅ Graceful stream cleanup on disconnect

**Related Documentation**:
- [Phase 1B Implementation](../../docs/scratchpad/PHASE-1B-ACTUAL-COMPLETION.md)
- [SSE Streaming Architecture](../../docs/scratchpad/websocket-architecture-decision.md)

## Best Practices

1. **Document Expected Behavior**: Each manual test should clearly state what you expect to see
2. **Include Troubleshooting**: Add common issues and their solutions
3. **Automate When Stable**: Once behavior is validated, consider automating the test
4. **Keep Scripts Simple**: Manual tests should be easy to run and understand
5. **Version Control**: Include manual tests in git for team collaboration

## Converting to Automated Tests

When a manual test becomes stable and repeatable, convert it to an automated integration test:

```python
# tests/integration/test_nats_world_updates.py

async def test_world_update_published():
    """Automated version of test_nats_subscriber.py validation."""
    # Subscribe to NATS
    events_received = []

    async def handler(msg):
        events_received.append(json.loads(msg.data.decode()))

    await nats_client.subscribe("world.updates.user.*", cb=handler)

    # Trigger state change
    response = await client.post("/kb/experience/interact", json={
        "message": "take dream bottle",
        "experience": "wylding-woods"
    })

    # Wait for event
    await asyncio.sleep(0.2)

    # Assert event received
    assert len(events_received) == 1
    assert events_received[0]["type"] == "world_update"
```

## Adding New Manual Tests

1. Create a new Python script in this directory
2. Add docstring explaining purpose, usage, and expected output
3. Make script executable: `chmod +x tests/manual/your_test.py`
4. Document the test in this README
5. Include troubleshooting tips

## Related Documentation

- [Phase 1 Implementation Guide](../../docs/scratchpad/nats-world-updates-implementation-analysis.md#phase-1-implementation-guide)
- [Testing Guide](../../docs/testing/TESTING_GUIDE.md)
- [NATS Architecture](../../docs/scratchpad/nats-world-updates-implementation-analysis.md)
