# NATS Real-Time Integration Guide

**Version**: Phase 1B
**Status**: Production Ready
**Last Updated**: November 3, 2025

## Overview

GAIA Platform uses NATS pub/sub messaging for real-time world state synchronization in AR/VR experiences. This guide covers the Phase 1B implementation and provides a roadmap for future phases.

## Architecture

### Phase 1B: Per-Request Subscriptions (Current)

```
Client (Unity)                Server (Chat Service)              NATS Server
     │                              │                                 │
     ├─► POST /chat/unified ────────┤                                 │
     │    (stream=true)              │                                 │
     │                               ├──► SUBSCRIBE ───────────────────┤
     │                               │    world.updates.user.{id}      │
     │                               │                                 │
     │◄─── SSE: metadata ────────────┤                                 │
     │                               │                                 │
     │                         [NATS EVENT] ◄───────────────────────────┤
     │                               │                                 │
     │◄─── SSE: world_update ────────┤                                 │
     │◄─── SSE: narrative ───────────┤                                 │
     │◄─── SSE: done ────────────────┤                                 │
     │                               │                                 │
     │   [Stream closes]             │                                 │
     │                               ├──► UNSUBSCRIBE ─────────────────┤
     │                               │    world.updates.user.{id}      │
```

**Key Characteristics**:
- ✅ Subscriptions created per SSE streaming request
- ✅ User-specific subjects: `world.updates.user.{user_id}`
- ✅ Automatic cleanup when stream ends
- ✅ Graceful degradation if NATS unavailable
- ⚠️ Events lost between chat requests

## Implementation Details

### NATS Subjects

```python
# User-specific world updates
world.updates.user.{user_id}

# Examples:
world.updates.user.a7f4370e-0af5-40eb-bb18-fcc10538b041
```

### Event Format

World update events use this JSON format:

```json
{
  "type": "world_update",
  "event": "location_change",
  "data": {
    "location": {
      "lat": 40.7128,
      "lon": -74.0060,
      "altitude": 10.5
    },
    "timestamp": 1730678400
  }
}
```

### Server-Side Usage

**Subscribing to World Updates** (handled automatically in `unified_chat.py`):

```python
from app.shared.nats_client import NATSSubjects, get_nats_client

# Get user ID from authentication
user_id = auth.get("user_id") or auth.get("sub")

# Create NATS subject
nats_subject = NATSSubjects.world_update_user(user_id)

# Subscribe with callback
async def event_handler(data):
    # Process world update event
    await process_world_update(data)

nats_client = get_nats_client()
await nats_client.subscribe(nats_subject, event_handler)

# Cleanup when done
await nats_client.unsubscribe(nats_subject)
```

**Publishing World Updates** (for Unity/game servers):

```python
from app.shared.nats_client import NATSSubjects, get_nats_client

# Publish location change
nats_client = get_nats_client()
await nats_client.publish(
    NATSSubjects.world_update_user(user_id),
    {
        "type": "world_update",
        "event": "location_change",
        "data": {
            "location": {"lat": 40.7128, "lon": -74.0060},
            "timestamp": int(time.time())
        }
    }
)
```

### Client-Side Integration (Unity)

**C# Example** (pseudo-code for Unity integration):

```csharp
// Subscribe to SSE stream with NATS events
using (var client = new HttpClient())
{
    var request = new HttpRequestMessage(HttpMethod.Post,
        "https://api.gaia.dev/chat/unified");

    request.Headers.Add("x-api-key", apiKey);
    request.Content = new StringContent(JsonConvert.SerializeObject(new {
        message = "What do you see around here?",
        stream = true
    }), Encoding.UTF8, "application/json");

    using (var response = await client.SendAsync(request,
        HttpCompletionOption.ResponseHeadersRead))
    {
        var stream = await response.Content.ReadAsStreamAsync();
        using (var reader = new StreamReader(stream))
        {
            while (!reader.EndOfStream)
            {
                var line = await reader.ReadLineAsync();

                if (line.StartsWith("data: "))
                {
                    var json = line.Substring(6);
                    var chunk = JsonConvert.DeserializeObject<SSEChunk>(json);

                    if (chunk.type == "world_update")
                    {
                        // Handle real-time world update
                        ProcessWorldUpdate(chunk.data);
                    }
                    else if (chunk.type == "content")
                    {
                        // Handle LLM narrative
                        DisplayNarrative(chunk.content);
                    }
                }
            }
        }
    }
}
```

## Testing

### Manual Testing

Use the integration test to verify NATS functionality:

```bash
# Run NATS integration test
python3 tests/manual/test_nats_sse_integration.py

# Expected output:
# ✅ SUCCESS: Found subscription during active stream
# ✅ SUCCESS: Subscription cleaned up after stream closes
# ✅ Phase 1B NATS Integration: WORKING
```

### Monitoring NATS Subscriptions

Check active NATS subscriptions:

```bash
# View all connections with subscription details
curl -s "http://localhost:8222/connz?subs=1" | jq '.connections[] | {cid, subs: .num_subs, list: .subscriptions_list}'

# Check server-level stats
curl -s http://localhost:8222/varz | jq '{subscriptions, connections, in_msgs, out_msgs}'
```

### Event Injection Testing

Inject test events for development:

```python
import asyncio
from app.shared.nats_client import NATSSubjects, get_nats_client

async def inject_test_event():
    nats_client = get_nats_client()
    await nats_client.connect()

    # Inject location change event
    await nats_client.publish(
        NATSSubjects.world_update_user("your-user-id"),
        {
            "type": "world_update",
            "event": "location_change",
            "data": {
                "location": {"lat": 40.7128, "lon": -74.0060, "altitude": 10.5},
                "timestamp": int(time.time())
            }
        }
    )

    print("✅ Test event published")

# Run with: python -m asyncio <script_name>.inject_test_event
```

## Known Limitations & Workarounds

### Limitation 1: Events Lost Between Requests

**Problem**: NATS subscriptions only exist during active SSE streams. Events sent between chat requests are lost.

**Impact**:
- ❌ Cannot handle autonomous world events (NPC movements, weather changes)
- ❌ Cannot support multi-player scenarios (other players' actions)
- ❌ Time-based events only work during active conversations

**Workaround (Phase 1B)**:
```
Design conversational interactions where:
1. Player initiates all interactions
2. Events happen during those interactions
3. No autonomous world changes between requests
```

**Solution (Phase 2)**: Persistent WebSocket connections

### Limitation 2: No Event Replay

**Problem**: If client disconnects and reconnects, missed events are gone forever.

**Impact**:
- ❌ Cannot sync state after network loss
- ❌ No offline support
- ❌ Cannot reconstruct game state from event history

**Workaround (Phase 1B)**:
```
Use stateless interactions:
1. Request full state on each chat interaction
2. No expectation of state continuity
3. Treat each request as fresh context
```

**Solution (Phase 3)**: NATS JetStream for event replay

## Migration Path

### Phase 2: WebSocket + Persistent Subscriptions

**Target**: Q1 2026

```
Client connects once → NATS subscription persists → Server pushes anytime

Benefits:
✅ Autonomous world events (NPCs move without player action)
✅ Multi-player support (see other players' actions)
✅ Time-based events (weather, day/night cycles)
✅ Lower latency (no SSE request overhead)
```

**Implementation**:
```python
# WebSocket endpoint for persistent connection
@app.websocket("/ws/world")
async def websocket_world_updates(websocket: WebSocket, user_id: str):
    await websocket.accept()

    # Create persistent NATS subscription
    nats_subject = NATSSubjects.world_update_user(user_id)

    async def forward_to_websocket(data):
        await websocket.send_json(data)

    await nats_client.subscribe(nats_subject, forward_to_websocket)

    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    finally:
        # Cleanup on disconnect
        await nats_client.unsubscribe(nats_subject)
```

### Phase 3: JetStream Event Sourcing

**Target**: Q2 2026

```
Events stored on disk → Replay on reconnect → Full game state reconstruction

Benefits:
✅ Event replay (catch up after disconnect)
✅ Offline sync (download missed events)
✅ Audit logs (debug + analytics)
✅ Time travel (replay game state at any point)
```

**Implementation**:
```python
import nats
from nats.js.api import StreamConfig, ConsumerConfig

# Create JetStream stream for world events
js = nc.jetstream()
await js.add_stream(
    StreamConfig(
        name="WORLD_UPDATES",
        subjects=["world.updates.user.*"],
        retention="limits",
        max_age=86400,  # 24 hours
        storage="file"
    )
)

# Subscribe with delivery guarantee
psub = await js.pull_subscribe(
    "world.updates.user.a7f4370e-0af5-40eb-bb18-fcc10538b041",
    "my-consumer"
)

# Replay events from 1 hour ago
msgs = await psub.fetch(batch=100)
for msg in msgs:
    process_event(msg.data)
    await msg.ack()
```

## Troubleshooting

### Issue: Subscriptions Not Appearing in NATS

**Symptom**: `curl http://localhost:8222/connz` shows no subscriptions

**Solution**: Use `?subs=1` parameter:
```bash
curl "http://localhost:8222/connz?subs=1"
```

### Issue: AuthenticationResult 'get' Error

**Symptom**: `AttributeError: 'AuthenticationResult' object has no attribute 'get'`

**Solution**: Ensure Phase 1B code is deployed (added `.get()` method for compatibility)

### Issue: Subscription Object 'sid' Error

**Symptom**: `'Subscription' object has no attribute 'sid'`

**Solution**: Ensure Phase 1B fix is deployed (use subscription objects, not `.sid`)

### Issue: Events Not Received

**Checklist**:
1. ✅ NATS server running? `curl http://localhost:8222/varz`
2. ✅ Chat Service connected? Check logs for "Connected to NATS"
3. ✅ Subscription created? Check logs for "Subscribed to NATS: world.updates.user.*"
4. ✅ Event published to correct subject? Must match user_id exactly
5. ✅ SSE stream still active? Subscriptions destroyed when stream closes

## Performance Considerations

### Subscription Overhead

- **Creation**: ~5-10ms per subscription
- **Event delivery**: <1ms latency
- **Cleanup**: ~2-5ms per unsubscribe

**Impact**: Negligible for Phase 1B (per-request subscriptions)

### Scaling Limits

- **NATS Core**: Handles 1M+ messages/sec
- **Connections**: 100K+ concurrent connections per server
- **Subscriptions**: 10M+ active subscriptions

**Bottleneck**: Not NATS, but SSE connection limits (100-500 per server)

## Security

### Subject Access Control

**Phase 1B**: No access control (trust-based)
- All authenticated users can subscribe to any `world.updates.user.*` subject
- Security through obscurity (user_id is UUID)

**Phase 2**: NATS authorization
```nats
# NATS authorization config
authorization {
  users = [
    {
      user: "chat-service",
      password: "$SECRET",
      permissions: {
        publish: "world.updates.user.*",
        subscribe: "world.updates.user.*"
      }
    }
  ]
}
```

## References

- [NATS Documentation](https://docs.nats.io/)
- [NATS JetStream](https://docs.nats.io/nats-concepts/jetstream)
- [Phase 1B Implementation](docs/scratchpad/2025-11-03-1538-nats-implementation-progress.md)
- [Integration Test](tests/manual/test_nats_sse_integration.py)
- [Architecture Overview](docs/_internal/architecture-overview.md)

## Quick Command Reference

```bash
# Test NATS integration
python3 tests/manual/test_nats_sse_integration.py

# Monitor NATS subscriptions
curl -s "http://localhost:8222/connz?subs=1" | jq

# Check NATS server stats
curl -s http://localhost:8222/varz | jq

# Check Chat Service NATS status
curl -s http://localhost:8002/health | jq .nats_connected

# Inject test event (Python)
python3 -c "import asyncio; from app.shared.nats_client import *; asyncio.run(get_nats_client().publish('world.updates.user.YOUR_ID', {'test': 'event'}))"
```

---

**Need Help?** Check [Architecture Overview](docs/_internal/architecture-overview.md) or [Implementation Status](docs/_internal/phase-reports/IMPLEMENTATION_STATUS.md)
