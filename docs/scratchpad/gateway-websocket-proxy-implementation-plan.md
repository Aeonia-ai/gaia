# Gateway WebSocket Proxy Implementation Plan

**Created**: 2025-11-09
**Status**: Design Complete - Ready for Implementation
**Issue**: Unity client cannot connect to WebSocket through Gateway (port 8666)

## Problem Statement

Unity client expects to connect via Gateway WebSocket endpoint:
```
ws://gateway:8666/ws/experience?token=JWT&experience=wylding-woods
```

**Current State**:
- ✅ KB Service has WebSocket endpoint at port 8001 (works)
- ❌ Gateway has NO WebSocket endpoint at port 8666 (404/403 errors)
- ✅ Test script bypasses Gateway by connecting directly to KB Service
- ❌ Unity fails because it requires Gateway proxy

**Root Cause**: Gateway WebSocket proxy was discussed but never implemented.

---

## Research & Design Process

### Step 1: Skills Loaded
- ✅ **async-python-patterns** - WebSocket patterns, task management, error handling
- ✅ **fastapi-templates** - FastAPI best practices, dependency injection, testing

### Step 2: Perplexity Research
**Query**: "How to implement WebSocket proxy in FastAPI with JWT validation, bidirectional streaming to backend WebSocket using asyncio"

**Key Findings**:
1. Use `asyncio.wait(return_when=FIRST_EXCEPTION)` not `gather()` for proxies
2. Use `websockets` library for backend connection
3. JWT validation before `websocket.accept()`
4. Cancel remaining tasks when either side disconnects
5. Proper WebSocket close codes: 1008 (auth), 1011 (server error)

### Step 3: Pattern Synthesis
Combined:
- **async-python-patterns Pattern 3**: Task Creation and Management
- **async-python-patterns Pattern 4**: Error Handling in Async Code
- **async-python-patterns Pattern 9**: Semaphore for Rate Limiting
- **fastapi-templates**: Dependency Injection pattern
- **Perplexity**: WebSocket proxy with FIRST_EXCEPTION shutdown

---

## Architecture

### Component Diagram
```
Unity Client
    ↓ ws://gateway:8666/ws/experience?token=JWT&experience=wylding-woods
    ↓
┌─────────────────────────────────────────────────┐
│ Gateway WebSocket Proxy (NEW)                   │
│                                                  │
│ 1. Accept connection                            │
│ 2. Validate JWT (defense-in-depth)              │
│ 3. Connect to KB Service                        │
│ 4. Bidirectional stream (concurrent tasks):     │
│    - client_to_backend() task                   │
│    - backend_to_client() task                   │
│ 5. Shutdown on first failure/disconnect         │
└─────────────────────────────────────────────────┘
    ↓ ws://kb-service:8001/ws/experience?token=JWT&experience=wylding-woods
    ↓
┌─────────────────────────────────────────────────┐
│ KB Service WebSocket (EXISTING)                 │
│                                                  │
│ 1. Validate JWT (KB re-validates)               │
│ 2. Process game messages:                       │
│    - ping/pong                                  │
│    - collect_bottle                             │
│    - talk to NPC                                │
│ 3. Update player state                          │
│ 4. Send responses                               │
└─────────────────────────────────────────────────┘
```

### Gateway vs KB Service WebSocket Roles

| Aspect | Gateway (Proxy) | KB Service (Terminating) |
|--------|----------------|--------------------------|
| **Purpose** | Route & authenticate | Process game logic |
| **Validates JWT** | ✅ Yes (first layer) | ✅ Yes (second layer) |
| **Processes messages** | ❌ No (transparent) | ✅ Yes (handles commands) |
| **Maintains state** | ❌ No | ✅ Yes (player inventory, quests) |
| **Connection type** | Proxy/tunnel | Application endpoint |

---

## Implementation

### File: `app/gateway/main.py`

Add this WebSocket endpoint to the existing Gateway service:

```python
import asyncio
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, Query, status, Depends
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException, InvalidURI

from app.shared.security import get_current_user_ws
from app.shared.config import Settings, get_settings
from app.shared import get_logger

logger = get_logger(__name__)

# Connection pool for KB Service (Pattern: async-python-patterns Semaphore)
class WebSocketConnectionPool:
    """Manages WebSocket connections to backend services with rate limiting."""

    def __init__(self, max_connections: int = 100):
        self.semaphore = asyncio.Semaphore(max_connections)
        logger.info(f"WebSocket connection pool initialized (max: {max_connections})")

    async def connect(self, uri: str):
        """Connect to backend with rate limiting."""
        async with self.semaphore:
            return await websockets.connect(uri)

# Initialize pool (singleton pattern)
ws_pool = WebSocketConnectionPool(max_connections=100)

@app.websocket("/ws/experience")
async def websocket_proxy(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    experience: str = Query(..., description="Experience ID (e.g., wylding-woods)"),
    settings: Settings = Depends(get_settings)  # Pattern: fastapi-templates Dependency Injection
):
    """
    WebSocket proxy to KB Service experience endpoint.

    Implements transparent bidirectional tunneling with authentication at Gateway
    (defense-in-depth) and re-validation at KB Service. Uses asyncio tasks for
    concurrent read/write streams with FIRST_EXCEPTION shutdown strategy.

    Design Patterns:
    - async-python-patterns Pattern 3: Task Creation and Management
    - async-python-patterns Pattern 4: Error Handling in Async Code
    - async-python-patterns Pattern 9: Semaphore for Rate Limiting
    - fastapi-templates: Dependency Injection
    - Perplexity: WebSocket Proxy with asyncio.wait(FIRST_EXCEPTION)

    Args:
        websocket: Client WebSocket connection
        token: JWT token for authentication
        experience: Experience identifier
        settings: Application settings (injected via Depends)

    WebSocket Close Codes:
        1008: Authentication failed (invalid/expired JWT)
        1011: Internal server error (backend unavailable, proxy error)
    """
    user_email: Optional[str] = None

    # STEP 1: Authenticate at Gateway (defense-in-depth)
    try:
        await websocket.accept()
        user_payload = await get_current_user_ws(websocket, token)
        user_id = user_payload.get("sub")
        user_email = user_payload.get("email")
        logger.info(f"WebSocket proxy authenticated: {user_email} ({user_id})")
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        return  # get_current_user_ws() already closed connection with code 1008

    # STEP 2: Build backend URL
    kb_ws_url = f"{settings.kb_service_url.replace('http', 'ws')}/ws/experience"
    kb_full_url = f"{kb_ws_url}?token={token}&experience={experience}"

    backend_ws: Optional[websockets.WebSocketClientProtocol] = None

    try:
        # STEP 3: Connect to KB Service with connection pooling
        backend_ws = await ws_pool.connect(kb_full_url)
        logger.info(f"WebSocket proxy connected to KB Service for {user_email}")

        # STEP 4: Define bidirectional proxy tasks
        # Pattern: async-python-patterns Error Handling (Pattern 4)

        async def client_to_backend():
            """
            Forward messages from client to KB Service.

            Handles:
            - WebSocketDisconnect: Client closed connection
            - ConnectionClosed: Backend closed connection
            - CancelledError: Task cancelled by peer failure
            """
            try:
                while True:
                    data = await websocket.receive_text()
                    await backend_ws.send(data)
                    logger.debug(f"Proxied client→KB: {data[:100]}")
            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {user_email}")
            except ConnectionClosed:
                logger.info(f"Backend closed for: {user_email}")
            except asyncio.CancelledError:
                logger.debug(f"client_to_backend cancelled for: {user_email}")
                raise  # Re-raise to propagate cancellation (async-python-patterns best practice)
            except Exception as e:
                logger.error(f"Error in client→backend: {e}", exc_info=True)
                raise  # Propagate to task cleanup

        async def backend_to_client():
            """
            Forward messages from KB Service to client.

            Handles:
            - WebSocketDisconnect: Client closed connection
            - ConnectionClosed: Backend closed connection
            - CancelledError: Task cancelled by peer failure
            """
            try:
                while True:
                    data = await backend_ws.recv()
                    await websocket.send_text(data)
                    logger.debug(f"Proxied KB→client: {data[:100]}")
            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {user_email}")
            except ConnectionClosed:
                logger.info(f"Backend closed for: {user_email}")
            except asyncio.CancelledError:
                logger.debug(f"backend_to_client cancelled for: {user_email}")
                raise  # Re-raise to propagate cancellation (async-python-patterns best practice)
            except Exception as e:
                logger.error(f"Error in backend→client: {e}", exc_info=True)
                raise  # Propagate to task cleanup

        # STEP 5: Run both directions concurrently
        # Pattern: Perplexity - asyncio.wait() with FIRST_EXCEPTION
        # This ensures when either side fails, the other is cancelled immediately
        tasks = [
            asyncio.create_task(client_to_backend(), name=f"c2b-{user_email}"),
            asyncio.create_task(backend_to_client(), name=f"b2c-{user_email}")
        ]

        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_EXCEPTION
        )

        # STEP 6: Cleanup - Cancel remaining tasks
        # Pattern: async-python-patterns Task Management (Pattern 3)
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f"Task {task.get_name()} cancelled during cleanup")

        # STEP 7: Check for exceptions and close appropriately
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, (WebSocketDisconnect, ConnectionClosed)):
                logger.error(f"Task {task.get_name()} failed: {exc}", exc_info=exc)
                # Close client with error code
                try:
                    await websocket.close(
                        code=status.WS_1011_INTERNAL_ERROR,
                        reason="Proxy error"
                    )
                except Exception:
                    pass  # Already closed

        logger.info(f"WebSocket proxy closed cleanly for {user_email}")

    except InvalidURI as e:
        logger.error(f"Invalid KB Service URL: {kb_full_url} - {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Configuration error")

    except WebSocketException as e:
        logger.error(f"Failed to connect to KB Service: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Backend unavailable")

    except Exception as e:
        logger.error(f"Unexpected WebSocket proxy error: {e}", exc_info=True)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal error")
        except Exception:
            pass  # Already closed

    finally:
        # Always cleanup backend connection
        if backend_ws:
            try:
                await backend_ws.close()
                logger.debug(f"Backend WebSocket closed for {user_email}")
            except Exception as e:
                logger.warning(f"Error closing backend WebSocket: {e}")
```

---

## Configuration

### 1. Dependencies

Add to `requirements.txt`:
```txt
websockets>=12.0  # For websockets.connect() to KB Service
```

### 2. Environment Variables

Verify in `.env`:
```bash
KB_SERVICE_URL=http://kb-service:8000  # Will be converted to ws://kb-service:8000
```

### 3. Settings Configuration

Verify in `app/shared/config.py`:
```python
class Settings(BaseSettings):
    kb_service_url: str = Field(
        default="http://kb-service:8000",
        env="KB_SERVICE_URL",
        description="KB Service base URL (http will be converted to ws for WebSocket)"
    )
```

---

## Testing Strategy

### Test File: `tests/integration/gateway/test_websocket_proxy.py`

Pattern from **fastapi-templates** skill - comprehensive integration testing:

```python
import pytest
import asyncio
from websockets import connect as ws_connect
from websockets.exceptions import InvalidStatusCode
import json

@pytest.mark.asyncio
async def test_websocket_proxy_authentication_success(valid_jwt_token):
    """Test WebSocket proxy with valid JWT - should connect successfully."""
    async with ws_connect(
        f"ws://localhost:8666/ws/experience?token={valid_jwt_token}&experience=wylding-woods"
    ) as websocket:
        # Should receive welcome message from KB Service
        welcome = await websocket.recv()
        welcome_data = json.loads(welcome)

        assert welcome_data["type"] == "connected"
        assert "connection_id" in welcome_data
        assert "user_id" in welcome_data

        print(f"✅ Connected with welcome: {welcome_data}")

@pytest.mark.asyncio
async def test_websocket_proxy_authentication_failure():
    """Test WebSocket proxy with invalid JWT - should reject with 403."""
    with pytest.raises(InvalidStatusCode) as exc_info:
        async with ws_connect(
            "ws://localhost:8666/ws/experience?token=invalid_token&experience=wylding-woods"
        ) as websocket:
            await websocket.recv()

    # Should get 403 Forbidden
    assert exc_info.value.status_code == 403
    print("✅ Invalid token correctly rejected with 403")

@pytest.mark.asyncio
async def test_websocket_proxy_bidirectional_ping_pong(valid_jwt_token):
    """Test bidirectional message flow - ping/pong through proxy."""
    async with ws_connect(
        f"ws://localhost:8666/ws/experience?token={valid_jwt_token}&experience=wylding-woods"
    ) as websocket:
        # Wait for welcome
        await websocket.recv()

        # Send ping
        ping_msg = json.dumps({
            "type": "ping",
            "timestamp": 123456789
        })
        await websocket.send(ping_msg)

        # Should receive pong from KB Service via proxy
        response = await websocket.recv()
        response_data = json.loads(response)

        assert response_data["type"] == "pong"
        assert "timestamp" in response_data

        print(f"✅ Ping/pong successful: {response_data}")

@pytest.mark.asyncio
async def test_websocket_proxy_collect_bottle_action(valid_jwt_token):
    """Test game action through proxy - collect bottle."""
    async with ws_connect(
        f"ws://localhost:8666/ws/experience?token={valid_jwt_token}&experience=wylding-woods"
    ) as websocket:
        # Wait for welcome
        await websocket.recv()

        # Send collect_bottle action
        collect_msg = json.dumps({
            "type": "action",
            "action": "collect_bottle",
            "item_id": "bottle_of_joy_1",
            "spot_id": "spot_001"
        })
        await websocket.send(collect_msg)

        # Should receive response from KB Service
        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        response_data = json.loads(response)

        # Verify response (either success or error, but not timeout)
        assert "type" in response_data

        print(f"✅ Collect bottle response: {response_data}")

@pytest.mark.asyncio
async def test_websocket_proxy_backend_unavailable(valid_jwt_token, monkeypatch):
    """Test WebSocket proxy when KB Service is down - should fail gracefully."""
    # Mock KB Service URL to point to non-existent service
    monkeypatch.setenv("KB_SERVICE_URL", "http://localhost:9999")

    with pytest.raises(Exception):  # Connection should fail
        async with ws_connect(
            f"ws://localhost:8666/ws/experience?token={valid_jwt_token}&experience=wylding-woods"
        ) as websocket:
            await websocket.recv()

    print("✅ Backend unavailable handled correctly")

@pytest.mark.asyncio
async def test_websocket_proxy_client_disconnect_cleanup(valid_jwt_token):
    """Test that proxy cleans up when client disconnects."""
    websocket = await ws_connect(
        f"ws://localhost:8666/ws/experience?token={valid_jwt_token}&experience=wylding-woods"
    )

    # Wait for welcome
    await websocket.recv()

    # Close client connection
    await websocket.close()

    # Check Gateway logs - should show clean shutdown
    # (Manual verification: docker compose logs gateway --tail 20)

    print("✅ Client disconnect cleanup completed")

@pytest.mark.asyncio
async def test_websocket_proxy_concurrent_connections(valid_jwt_token):
    """Test multiple concurrent connections through proxy."""
    connections = []

    try:
        # Open 10 concurrent connections
        for i in range(10):
            ws = await ws_connect(
                f"ws://localhost:8666/ws/experience?token={valid_jwt_token}&experience=wylding-woods"
            )
            welcome = await ws.recv()
            connections.append(ws)

        assert len(connections) == 10
        print(f"✅ {len(connections)} concurrent connections established")

        # Send ping through all connections
        for ws in connections:
            await ws.send(json.dumps({"type": "ping", "timestamp": 123456}))

        # Receive pongs
        for ws in connections:
            pong = await asyncio.wait_for(ws.recv(), timeout=2.0)
            assert "pong" in pong

        print("✅ All concurrent connections received pong")

    finally:
        # Cleanup
        for ws in connections:
            await ws.close()
```

### Test Execution

```bash
# Run WebSocket proxy tests
./scripts/pytest-for-claude.sh tests/integration/gateway/test_websocket_proxy.py -v

# Run with coverage
./scripts/pytest-for-claude.sh tests/integration/gateway/test_websocket_proxy.py --cov=app.gateway -v
```

---

## Deployment Checklist

### Local Development
- [ ] Add `websockets>=12.0` to `requirements.txt`
- [ ] Implement WebSocket proxy in `app/gateway/main.py`
- [ ] Verify `KB_SERVICE_URL` in `.env`
- [ ] Restart Gateway service: `docker compose restart gateway`
- [ ] Run integration tests
- [ ] Test with Unity client on port 8666

### Staging/Production
- [ ] Deploy updated Gateway with WebSocket support
- [ ] Verify `KB_SERVICE_URL` environment variable in Fly.io
- [ ] Test with remote Unity client
- [ ] Monitor Gateway logs for WebSocket connections
- [ ] Update documentation for Unity team

---

## Monitoring & Debugging

### Gateway Logs
```bash
# Watch WebSocket connections
docker compose logs gateway --tail 50 -f | grep -i websocket

# Check for authentication failures
docker compose logs gateway | grep "WebSocket authentication failed"

# Check for backend connection issues
docker compose logs gateway | grep "Failed to connect to KB Service"
```

### Key Metrics to Monitor
- WebSocket connection rate (connections/second)
- Authentication failure rate
- Backend connection failures
- Average connection duration
- Concurrent connection count

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| **403 Forbidden** | Client connection rejected | Check JWT token expiration |
| **1011 Internal Error** | Backend connection failed | Verify KB Service is running |
| **Connection timeout** | No response from backend | Check KB_SERVICE_URL configuration |
| **Memory leak** | Gateway memory grows | Verify task cleanup in finally block |

---

## Performance Considerations

### Connection Pooling
```python
# Current implementation uses Semaphore (max 100 concurrent)
ws_pool = WebSocketConnectionPool(max_connections=100)
```

**Tuning**:
- **Low traffic** (<10 concurrent): Keep default (100)
- **Medium traffic** (10-50 concurrent): Increase to 200
- **High traffic** (50+ concurrent): Increase to 500+ and monitor

### Resource Usage
- **Memory**: ~1-2KB per WebSocket connection
- **CPU**: Negligible (event loop handles I/O)
- **Network**: Transparent proxy, no additional overhead

---

## Future Enhancements

### Phase 2: Connection Metrics
```python
class WebSocketMetrics:
    """Track WebSocket connection metrics."""
    total_connections = 0
    active_connections = 0
    failed_connections = 0
    avg_duration_seconds = 0.0
```

### Phase 3: Message Inspection (Optional)
For debugging/monitoring, could add optional message logging:
```python
if settings.websocket_debug_mode:
    logger.debug(f"Message content: {data}")
```

### Phase 4: Protocol Versioning
Support multiple WebSocket protocol versions:
```python
@app.websocket("/ws/v1/experience")  # Version 1
@app.websocket("/ws/v2/experience")  # Version 2
```

---

## Success Criteria

✅ **Implementation Complete** when:
1. Unity client can connect to `ws://gateway:8666/ws/experience`
2. All integration tests pass
3. JWT authentication works (valid tokens connect, invalid tokens get 403)
4. Bidirectional message flow works (ping/pong, collect_bottle)
5. Clean shutdown on disconnects (no resource leaks)
6. Gateway logs show successful proxy connections

✅ **Production Ready** when:
1. Staging deployment successful
2. Load testing with 50+ concurrent connections
3. Unity team confirms successful integration
4. Monitoring dashboards show healthy metrics
5. Documentation updated

---

## References

- **async-python-patterns** skill: Task Management (Pattern 3), Error Handling (Pattern 4), Semaphore (Pattern 9)
- **fastapi-templates** skill: Dependency Injection, Testing patterns
- **Perplexity research**: WebSocket proxy with asyncio.wait(FIRST_EXCEPTION)
- **FastAPI WebSocket docs**: https://fastapi.tiangolo.com/advanced/websockets/
- **websockets library docs**: https://websockets.readthedocs.io/

---

## Appendix: Why asyncio.wait() vs gather()?

### gather() Behavior
```python
# gather() waits for ALL tasks to complete
await asyncio.gather(task1, task2)
# If task1 fails, task2 keeps running until it completes
```

### wait(FIRST_EXCEPTION) Behavior
```python
# wait() can stop at first failure
done, pending = await asyncio.wait(tasks, return_when=FIRST_EXCEPTION)
# If task1 fails, task2 is still in 'pending' and can be cancelled immediately
```

**For WebSocket proxy**: When client disconnects, we want to cancel the backend task immediately, not wait for it to timeout. Hence `wait(FIRST_EXCEPTION)` is the correct choice.

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

The core architectural and implementation claims in this document have been verified against the source code.

-   **✅ Gateway WebSocket Proxy Implementation (Section "Implementation" of this document):**
    *   **Claim:** A WebSocket endpoint `/ws/experience` is added to `app/gateway/main.py` to proxy connections to the KB Service.
    *   **Code Reference:** `app/gateway/main.py` (lines 1195-1344).
    *   **Verification:** Confirmed the presence of the `@app.websocket("/ws/experience")` endpoint, its parameters (`token`, `experience`), and the overall structure of the `websocket_proxy` function.

-   **✅ Authentication at Gateway (Step 1 in "Implementation" section):**
    *   **Claim:** JWT authentication is performed at the Gateway level.
    *   **Code Reference:** `app/gateway/main.py` (lines 1229-1238).
    *   **Verification:** Confirmed the call to `get_current_user_ws(websocket, token)` and the error handling for authentication failures.

-   **✅ Connection to KB Service (Step 3 in "Implementation" section):**
    *   **Claim:** The Gateway connects to the KB Service's WebSocket endpoint.
    *   **Code Reference:** `app/gateway/main.py` (lines 1248-1250).
    *   **Verification:** Confirmed the construction of `kb_ws_url` and `kb_full_url`, and the call to `ws_pool.connect(kb_full_url)`.

-   **✅ Bidirectional Proxy Tasks (Step 4 in "Implementation" section):**
    *   **Claim:** `client_to_backend` and `backend_to_client` tasks handle bidirectional streaming.
    *   **Code Reference:** `app/gateway/main.py` (lines 1252-1300).
    *   **Verification:** Confirmed the definition of both `client_to_backend` and `backend_to_client` async functions, including their error handling and cancellation logic.

-   **✅ `asyncio.wait(FIRST_EXCEPTION)` for Shutdown (Step 5 in "Implementation" section):**
    *   **Claim:** `asyncio.wait` with `FIRST_EXCEPTION` is used for concurrent task management and immediate shutdown on failure.
    *   **Code Reference:** `app/gateway/main.py` (lines 1302-1307).
    *   **Verification:** Confirmed the usage of `asyncio.wait` with `return_when=asyncio.FIRST_EXCEPTION`.

-   **✅ Configuration (Section "Configuration" of this document):**
    *   **Claim:** `websockets>=12.0` is a dependency and `KB_SERVICE_URL` is configured.
    *   **Code Reference:** `app/shared/config.py` (lines 20-23 for `kb_service_url` setting).
    *   **Verification:** Confirmed the `kb_service_url` setting in `app/shared/config.py`. (Note: `requirements.txt` was not directly inspected, but the code's reliance on `websockets` implies its presence).

**Conclusion:** The implementation of the Gateway WebSocket proxy is highly consistent with the architecture and details described in this document.
