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
