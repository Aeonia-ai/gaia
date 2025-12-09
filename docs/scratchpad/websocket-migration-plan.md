# WebSocket Migration Plan: SSE → WebSocket Real-Time Communication

**Date**: 2025-11-05
**Status**: Planning Complete, Implementation Pending
**Estimated Effort**: 9-13 hours (server) + 3-4 hours (Unity client)

---

## Executive Summary

This document outlines the migration from **Server-Sent Events (SSE)** to **WebSocket** for real-time client-server communication in the GAIA platform. This migration enables persistent connections, bidirectional communication, and autonomous world events—capabilities critical for the MMOIRL vision.

### Why Migrate?

**Current SSE Limitations** (Phase 1B):
- ❌ Per-request NATS subscriptions (created/destroyed each chat interaction)
- ❌ Events lost between requests (no autonomous world events)
- ❌ Unidirectional only (client sends HTTP POST, server streams SSE)
- ❌ High reconnection overhead for continuous updates

**WebSocket Benefits**:
- ✅ Persistent connections (one connection for entire session)
- ✅ Persistent NATS subscriptions (autonomous events delivered anytime)
- ✅ Bidirectional (single connection for send/receive)
- ✅ Lower latency (no reconnection overhead)
- ✅ Native Unity support (WebSocket is standard in Unity)

### What Changes?

**Transport Layer Only** - NATS backend architecture remains unchanged:
- KB Service publishing logic: **No changes required**
- NATS pub/sub subjects: **No changes required**
- WorldUpdateEvent schema: **No changes required**
- Unity DirectiveQueue: **No changes required** (consumes events regardless of transport)

**What Changes**:
- Chat Service: Add WebSocket endpoints + ConnectionManager
- Unity Client: Replace SSE client with WebSocket client
- Authentication: Add WebSocket-specific auth (JWT in query params)

---

## Architecture Comparison

### Current Architecture (SSE-Based)

```
┌─────────────┐         HTTP POST          ┌──────────────┐
│   Unity     │──────────chat request──────>│ Chat Service │
│   Client    │                             │              │
│             │<───────SSE stream───────────│ (creates     │
│             │   (LLM + world_update)      │  per-request │
│             │                             │  NATS sub)   │
└─────────────┘                             └──────────────┘
                                                    │
      [Connection dies after response]             │ NATS
                                                    ↓
                                             world.updates.user.*
                                             [Events lost between
                                              requests!]
```

**Flow**:
1. Client opens SSE stream for each chat message
2. Chat Service subscribes to NATS during request
3. Server streams LLM response + any world_update events
4. **Connection closes** → NATS subscription destroyed
5. **Events between requests are lost**

### Target Architecture (WebSocket-Based)

#### Current Demo Implementation (Path 1: KB Service handles WebSocket)

```
┌─────────────┐      WebSocket (persistent)  ┌──────────────┐
│   Unity     │<════════════════════════════>│ KB Service   │
│   Client     │   bidirectional messages     │ (for game    │
│             │                               │  actions)    │
│             │   - game actions              │ (persistent  │
│             │   - world_update events       │  NATS sub)   │
│             │   - quest updates             │              │
│             │   - player position           │              │
└─────────────┘                               └──────────────┘
                                                      │
        [Connection persists for session]            │ NATS
                                                      ↓
                                              world.updates.user.*
                                              [Events delivered
                                               anytime!]
```

**Flow (Current Demo)**:
1. Client opens WebSocket connection **once per session** to the KB Service.
2. KB Service subscribes to NATS **once** (persists for connection lifetime).
3. **Bidirectional messages**:
   - Client → Server: game actions (e.g., collect bottle), player position.
   - Server → Client: world_update, quest_update, action_response.
4. **Connection persists** → NATS subscription active.
5. **Autonomous events delivered** (NPCs, other players, world changes).

#### Future Production Architecture (Path 3: Dedicated Session Service)

```
┌─────────────┐      WebSocket (persistent)  ┌─────────────────┐
│   Unity     │<════════════════════════════>│ Session Service │
│   Client     │   bidirectional messages     │ (connection     │
│             │                               │  management)    │
│             │   - chat messages             │                 │
│             │   - game actions              │                 │
│             │   - world_update events       │                 │
│             │   - commands                  │                 │
│             │   - position updates          │                 │
└─────────────┘                               └─────────────────┘
                                                      │
                                                      │ NATS
                                                      ↓
                                              world.updates.user.*
                                              [Events delivered
                                               anytime!]
```

**Flow (Future Production)**:
1. Client opens WebSocket connection **once per session** to a dedicated Session Service.
2. Session Service manages the WebSocket connection and persistent NATS subscriptions.
3. Session Service routes messages to appropriate backend services (e.g., game actions to KB Service, chat to Chat Service) via NATS or direct calls.
4. **Connection persists** → NATS subscription active.
5. **Autonomous events delivered** (NPCs, other players, world changes).


---

## FastAPI Implementation Patterns

### Pattern 1: WebSocket Connection Manager

**File**: `app/services/chat/websocket_manager.py` (NEW)

```python
"""
WebSocket Connection Manager with Persistent NATS Subscriptions.

Design Principles:
1. One WebSocket per client session
2. One persistent NATS subscription per WebSocket
3. Automatic cleanup on disconnect
4. Heartbeat for connection health monitoring
5. Thread-safe connection registry
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Optional, Any
import asyncio
import json
import time
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections with persistent NATS subscriptions.

    Lifecycle:
    - connect(): Accept WebSocket, create NATS subscription, start heartbeat
    - disconnect(): Cleanup NATS subscription, cancel heartbeat, close socket
    - send_to_connection(): Send message to specific WebSocket
    - send_to_user(): Send message to user's active WebSocket
    """

    def __init__(self, nats_client):
        """
        Initialize connection manager.

        Args:
            nats_client: Global NATS client instance (from app.services.chat.main)
        """
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, str] = {}  # user_id → connection_id
        self.nats_subscriptions: Dict[str, Any] = {}  # connection_id → NATS subscription
        self.nats_client = nats_client
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_id: str
    ) -> None:
        """
        Accept WebSocket connection and create persistent NATS subscription.

        Steps:
        1. Accept WebSocket connection
        2. Register in connection registry
        3. Create persistent NATS subscription for user-specific subject
        4. Start heartbeat task to keep connection alive

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Authenticated user ID (from JWT)
            connection_id: Unique connection identifier (UUID)
        """
        # Accept WebSocket
        await websocket.accept()

        # Register connection
        async with self._lock:
            self.active_connections[connection_id] = websocket

            # Handle reconnection (disconnect previous connection for same user)
            if user_id in self.user_connections:
                old_connection_id = self.user_connections[user_id]
                logger.warning(
                    f"User {user_id} reconnecting, disconnecting old connection {old_connection_id}"
                )
                await self.disconnect(old_connection_id)

            self.user_connections[user_id] = connection_id

        # Create persistent NATS subscription
        from app.shared.nats_client import NATSSubjects
        nats_subject = NATSSubjects.world_update_user(user_id)

        async def nats_event_handler(msg):
            """
            NATS callback: Forward world_update events to WebSocket.

            This handler is called by NATS when events are published to
            world.updates.user.{user_id}. It remains active for the
            entire WebSocket connection lifetime.
            """
            try:
                data = json.loads(msg.data.decode())
                await self.send_to_connection(connection_id, {
                    "type": "world_update",
                    "data": data,
                    "timestamp": int(time.time() * 1000)
                })
                logger.debug(
                    f"Forwarded NATS event to WebSocket {connection_id}: "
                    f"experience={data.get('experience')}"
                )
            except Exception as e:
                logger.error(
                    f"Error forwarding NATS event to {connection_id}: {e}",
                    exc_info=True
                )

        # Subscribe to NATS (persistent for connection lifetime)
        if self.nats_client and self.nats_client.is_connected:
            try:
                subscription = await self.nats_client.subscribe(
                    nats_subject,
                    nats_event_handler
                )
                self.nats_subscriptions[connection_id] = subscription
                logger.info(
                    f"WebSocket connected: {connection_id}, "
                    f"user={user_id}, NATS subscribed: {nats_subject}"
                )
            except Exception as e:
                logger.error(f"Failed to create NATS subscription: {e}")
                # Continue without NATS (graceful degradation)
        else:
            logger.warning(
                f"NATS not available, WebSocket {connection_id} "
                "will not receive world updates"
            )

        # Start heartbeat task
        self._heartbeat_tasks[connection_id] = asyncio.create_task(
            self._heartbeat(connection_id)
        )

    async def disconnect(self, connection_id: str) -> None:
        """
        Clean up connection and NATS subscription.

        Steps:
        1. Unsubscribe from NATS (if active)
        2. Cancel heartbeat task
        3. Remove from connection registry
        4. Close WebSocket (if still open)

        Args:
            connection_id: Connection to disconnect
        """
        # Unsubscribe from NATS
        if connection_id in self.nats_subscriptions:
            subscription = self.nats_subscriptions.pop(connection_id)
            try:
                await subscription.unsubscribe()
                logger.info(f"NATS unsubscribed for connection: {connection_id}")
            except Exception as e:
                logger.error(f"Error unsubscribing from NATS: {e}")

        # Cancel heartbeat task
        if connection_id in self._heartbeat_tasks:
            task = self._heartbeat_tasks.pop(connection_id)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Remove from connection registry
        async with self._lock:
            if connection_id in self.active_connections:
                websocket = self.active_connections.pop(connection_id)
                try:
                    await websocket.close()
                except Exception:
                    pass  # Already closed

            # Remove user mapping
            user_id = next(
                (uid for uid, cid in self.user_connections.items() if cid == connection_id),
                None
            )
            if user_id and self.user_connections.get(user_id) == connection_id:
                self.user_connections.pop(user_id)

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_to_connection(
        self,
        connection_id: str,
        message: dict
    ) -> bool:
        """
        Send message to specific WebSocket connection.

        Args:
            connection_id: Target connection ID
            message: Message dict (will be JSON serialized)

        Returns:
            True if sent successfully, False otherwise
        """
        if connection_id not in self.active_connections:
            logger.warning(f"Connection {connection_id} not found")
            return False

        websocket = self.active_connections[connection_id]
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(
                f"Error sending to WebSocket {connection_id}: {e}",
                exc_info=True
            )
            # Disconnect on send failure
            await self.disconnect(connection_id)
            return False

    async def send_to_user(self, user_id: str, message: dict) -> bool:
        """
        Send message to user's active WebSocket connection.

        Args:
            user_id: Target user ID
            message: Message dict

        Returns:
            True if sent successfully, False if user not connected
        """
        connection_id = self.user_connections.get(user_id)
        if not connection_id:
            logger.debug(f"User {user_id} not connected")
            return False

        return await self.send_to_connection(connection_id, message)

    async def broadcast(self, message: dict, exclude: Optional[str] = None) -> int:
        """
        Broadcast message to all connected clients.

        Args:
            message: Message dict
            exclude: Optional connection_id to exclude from broadcast

        Returns:
            Number of clients that received the message
        """
        sent_count = 0
        for connection_id in list(self.active_connections.keys()):
            if connection_id == exclude:
                continue

            if await self.send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def _heartbeat(self, connection_id: str, interval: int = 30) -> None:
        """
        Send periodic heartbeat to keep connection alive and detect disconnects.

        Args:
            connection_id: Connection to heartbeat
            interval: Heartbeat interval in seconds (default: 30)
        """
        try:
            while connection_id in self.active_connections:
                await asyncio.sleep(interval)

                success = await self.send_to_connection(connection_id, {
                    "type": "heartbeat",
                    "timestamp": int(time.time() * 1000)
                })

                if not success:
                    # Connection failed, will be cleaned up by send_to_connection
                    break
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat cancelled for {connection_id}")
        except Exception as e:
            logger.error(
                f"Heartbeat error for {connection_id}: {e}",
                exc_info=True
            )
            await self.disconnect(connection_id)

    def get_active_connections_count(self) -> int:
        """Get count of active WebSocket connections."""
        return len(self.active_connections)

    def get_user_connection_id(self, user_id: str) -> Optional[str]:
        """Get connection ID for user, if connected."""
        return self.user_connections.get(user_id)

    def is_user_connected(self, user_id: str) -> bool:
        """Check if user has active WebSocket connection."""
        return user_id in self.user_connections
```

### Pattern 2: WebSocket Endpoints

**File**: `app/services/chat/websocket_endpoints.py` (NEW)

```python
"""
WebSocket endpoints for real-time chat and world updates.

Protocol:
- Client connects with JWT authentication
- Bidirectional message flow:
  - Client → Server: chat, command, position, ping
  - Server → Client: world_update, content, metadata, heartbeat
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.services.chat.websocket_manager import ConnectionManager
from app.shared.security import get_current_user_ws
import uuid
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize connection manager (will be injected from main.py)
connection_manager: ConnectionManager = None

def init_websocket_router(manager: ConnectionManager):
    """Initialize router with connection manager (called from main.py)."""
    global connection_manager
    connection_manager = manager


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for real-time communication.

    Authentication:
    - JWT token passed as query parameter: /ws?token=<jwt_token>

    Message Protocol (Client → Server):
    {
        "type": "chat" | "command" | "position" | "ping",
        "message": str,              # for type=chat
        "command": str,               # for type=command
        "position": {...},            # for type=position
        "context": {...}              # optional
    }

    Message Protocol (Server → Client):
    {
        "type": "world_update" | "content" | "metadata" | "heartbeat" | "error",
        "data": {...},                # for type=world_update
        "content": str,               # for type=content
        "conversation_id": str,       # for type=metadata
        "timestamp": int              # milliseconds
    }
    """
    connection_id = str(uuid.uuid4())

    # Authenticate
    try:
        auth = await get_current_user_ws(websocket, token)
        user_id = auth.get("user_id") or auth.get("sub")
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=1008)  # Policy violation
        return

    # Connect and setup NATS subscription
    await connection_manager.connect(websocket, user_id, connection_id)

    try:
        # Send welcome message
        await connection_manager.send_to_connection(connection_id, {
            "type": "connected",
            "connection_id": connection_id,
            "user_id": user_id,
            "timestamp": int(time.time() * 1000)
        })

        # Message receive loop
        while True:
            # Wait for message from client
            data = await websocket.receive_json()

            message_type = data.get("type")
            logger.debug(f"WebSocket message from {connection_id}: type={message_type}")

            if message_type == "chat":
                # Handle chat message with LLM streaming
                await handle_chat_message(
                    connection_id=connection_id,
                    user_id=user_id,
                    message=data.get("message"),
                    context=data.get("context"),
                    auth=auth
                )

            elif message_type == "command":
                # Handle game command (direct KB interaction)
                await handle_command(
                    connection_id=connection_id,
                    user_id=user_id,
                    command=data.get("command"),
                    experience=data.get("experience"),
                    auth=auth
                )

            elif message_type == "position":
                # Handle position update (for multiplayer/spatial events)
                await handle_position_update(
                    user_id=user_id,
                    position=data.get("position"),
                    experience=data.get("experience")
                )

            elif message_type == "ping":
                # Respond to ping
                await connection_manager.send_to_connection(connection_id, {
                    "type": "pong",
                    "timestamp": int(time.time() * 1000)
                })

            else:
                logger.warning(f"Unknown message type: {message_type}")
                await connection_manager.send_to_connection(connection_id, {
                    "type": "error",
                    "error": f"Unknown message type: {message_type}"
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.error(
            f"WebSocket error for {connection_id}: {e}",
            exc_info=True
        )
    finally:
        await connection_manager.disconnect(connection_id)


async def handle_chat_message(
    connection_id: str,
    user_id: str,
    message: str,
    context: dict,
    auth: dict
) -> None:
    """
    Handle chat message with streaming LLM response.

    Flow:
    1. Call unified_chat.process_stream() for LLM processing
    2. Stream LLM chunks to WebSocket
    3. NATS world_update events arrive independently via persistent subscription

    Note: world_update events are NOT streamed here - they arrive via the
    NATS subscription created in ConnectionManager.connect()
    """
    from app.services.chat.unified_chat import unified_chat_handler

    try:
        # Stream LLM response through WebSocket
        async for chunk in unified_chat_handler.process_stream(
            message=message,
            auth=auth,
            context=context
        ):
            # Forward SSE chunk to WebSocket
            # chunk = {"type": "content", "content": "...", ...}
            await connection_manager.send_to_connection(connection_id, chunk)

        # Send completion marker
        await connection_manager.send_to_connection(connection_id, {
            "type": "done",
            "timestamp": int(time.time() * 1000)
        })

    except Exception as e:
        logger.error(f"Error handling chat message: {e}", exc_info=True)
        await connection_manager.send_to_connection(connection_id, {
            "type": "error",
            "error": str(e),
            "timestamp": int(time.time() * 1000)
        })


async def handle_command(
    connection_id: str,
    user_id: str,
    command: str,
    experience: str,
    auth: dict
) -> None:
    """
    Handle direct game command (KB interaction without LLM).

    Example: Client sends {"type": "command", "command": "take bottle"}
    - Executes command via KB Service
    - KB publishes world_update to NATS
    - world_update arrives via NATS subscription (not here)
    - Sends acknowledgement to client
    """
    import httpx
    from app.shared.config import settings

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.KB_SERVICE_URL}/experience/interact",
                headers={"X-API-Key": settings.API_KEY},
                json={
                    "experience": experience,
                    "user_id": user_id,
                    "message": command
                },
                timeout=30.0
            )

            if response.status_code == 200:
                result = response.json()
                await connection_manager.send_to_connection(connection_id, {
                    "type": "command_result",
                    "success": True,
                    "message": result.get("response"),
                    "timestamp": int(time.time() * 1000)
                })
            else:
                await connection_manager.send_to_connection(connection_id, {
                    "type": "error",
                    "error": f"Command failed: {response.status_code}",
                    "timestamp": int(time.time() * 1000)
                })

    except Exception as e:
        logger.error(f"Error handling command: {e}", exc_info=True)
        await connection_manager.send_to_connection(connection_id, {
            "type": "error",
            "error": str(e),
            "timestamp": int(time.time() * 1000)
        })


async def handle_position_update(
    user_id: str,
    position: dict,
    experience: str
) -> None:
    """
    Handle position update from client (future multiplayer feature).

    Future implementation:
    - Store position in Redis/database
    - Publish position updates to other nearby players via NATS
    - Enable spatial queries for multiplayer interactions
    """
    # Placeholder for future multiplayer implementation
    logger.debug(
        f"Position update received: user={user_id}, "
        f"experience={experience}, position={position}"
    )
    # TODO: Implement spatial indexing and multiplayer position broadcasting
```

### Pattern 3: WebSocket Authentication

**File**: `app/shared/security.py` (UPDATE - add WebSocket auth function)

```python
"""Add WebSocket authentication to existing security.py"""

from fastapi import WebSocket, HTTPException, status, Query
from jose import JWTError, jwt
import logging

logger = logging.getLogger(__name__)

async def get_current_user_ws(
    websocket: WebSocket,
    token: str
) -> dict:
    """
    Authenticate WebSocket connection via JWT.

    Authentication Options:
    1. Token in query parameter: ws://server/ws?token=<jwt_token>
    2. Token in Sec-WebSocket-Protocol header (alternative, commented below)

    Args:
        websocket: FastAPI WebSocket instance
        token: JWT access token from query parameter

    Returns:
        Authentication dict: {"user_id": str, "email": str, ...}

    Raises:
        HTTPException: If authentication fails (closes WebSocket)
    """
    if not token:
        logger.error("WebSocket authentication failed: No token provided")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    try:
        # Decode JWT token
        from app.core.config import get_settings
        settings = get_settings()

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )

        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Return authentication result
        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "sub": user_id  # For compatibility with existing code
        }

    except JWTError as e:
        logger.error(f"WebSocket JWT validation failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

# Alternative: Token in Sec-WebSocket-Protocol header (if needed)
"""
Unity example:
Dictionary<string, string> headers = new Dictionary<string, string>();
headers["Sec-WebSocket-Protocol"] = $"access_token, {jwtToken}";
clientWebSocket.Options.SetRequestHeader("Sec-WebSocket-Protocol", headers["Sec-WebSocket-Protocol"]);

Python parsing:
protocols = websocket.headers.get("sec-websocket-protocol", "")
for protocol in protocols.split(","):
    if protocol.strip() != "access_token":
        token = protocol.strip()
        break
"""
```

### Pattern 4: Main Application Integration

**File**: `app/services/chat/main.py` (UPDATE)

```python
"""Update main.py to initialize WebSocket router"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.shared.nats_client import NATSClient

# Initialize NATS client (existing)
nats_client = NATSClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with WebSocket manager initialization."""
    # Startup
    logger.info("🚀 Starting Chat Service...")

    # Connect to NATS (existing)
    await nats_client.connect()

    # Initialize WebSocket connection manager (NEW)
    from app.services.chat.websocket_manager import ConnectionManager
    from app.services.chat.websocket_endpoints import init_websocket_router

    connection_manager = ConnectionManager(nats_client)
    init_websocket_router(connection_manager)

    logger.info("✅ WebSocket ConnectionManager initialized")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Chat Service...")
    await nats_client.disconnect()

# Create FastAPI app (existing)
app = FastAPI(
    title="Gaia Chat Service",
    description="Multi-provider LLM orchestration with WebSocket support",
    version="0.3",
    lifespan=lifespan
)

# Include existing routers
from app.services.chat.chat import router as chat_router
app.include_router(chat_router, prefix="/chat")  # SSE endpoints (legacy)

# Include WebSocket router (NEW)
from app.services.chat.websocket_endpoints import router as ws_router
app.include_router(ws_router, prefix="", tags=["websocket"])  # WebSocket at /ws

# Health check update (NEW)
@app.get("/health")
async def health_check():
    """Health check with WebSocket connection count."""
    from app.services.chat.websocket_endpoints import connection_manager

    return {
        "status": "healthy",
        "service": "chat",
        "version": "0.3",
        "nats_connected": nats_client.is_connected if nats_client else False,
        "websocket_connections": connection_manager.get_active_connections_count() if connection_manager else 0
    }
```

---

## Migration Strategy

### Phase 1: Dual Support (Weeks 1-2) ✅ **RECOMMENDED**

**Goal**: Run both SSE and WebSocket simultaneously, zero downtime

**Implementation**:
- ✅ Add WebSocket endpoints (`/ws`) alongside existing SSE (`/chat/unified`)
- ✅ Both use same NATS backend (no changes required)
- ✅ Both use same unified_chat processing logic
- ✅ Unity clients can choose transport (feature flag)

**Benefits**:
- Zero downtime migration
- Gradual rollout (Unity builds can enable WebSocket incrementally)
- Fallback if WebSocket issues discovered
- A/B testing (compare SSE vs WebSocket latency)

**Code Structure**:
```
app/services/chat/
├── unified_chat.py         # Shared LLM processing (unchanged)
├── chat.py                 # SSE endpoints (legacy, kept)
├── websocket_manager.py    # NEW: WebSocket connection manager
├── websocket_endpoints.py  # NEW: WebSocket /ws endpoint
└── main.py                 # Include both routers
```

### Phase 2: WebSocket Primary (Weeks 3-4)

**Goal**: Make WebSocket the default, SSE available for compatibility

**Actions**:
- Unity clients default to WebSocket
- Web clients feature-detect and prefer WebSocket (with SSE fallback)
- Monitor metrics: WebSocket adoption rate, latency comparison, error rates
- Update documentation to recommend WebSocket

**Monitoring**:
```python
# Metrics to track
websocket_connections_active (gauge)
sse_requests_total (counter)
websocket_latency_ms (histogram)
sse_latency_ms (histogram)
```

### Phase 3: WebSocket Only (Month 2+)

**Goal**: Deprecate SSE, simplify codebase

**Actions**:
- Announce SSE deprecation (give 30-60 days notice)
- Remove SSE endpoints from code
- Remove per-request NATS subscription logic
- Simplify tests (only test WebSocket)

**Rollback Plan**:
- SSE code remains in git history
- Can revert if critical issues discovered

---

## Unity Client Integration

### Unity WebSocket Client Example

```csharp
// Unity C# WebSocket client (using NativeWebSocket or similar)
using NativeWebSocket;
using UnityEngine;
using System;
using System.Collections.Generic;
using Newtonsoft.Json;

public class GaiaWebSocketClient : MonoBehaviour
{
    private WebSocket websocket;
    private string serverUrl = "ws://localhost:8666/ws";
    private string jwtToken;

    public event Action<WorldUpdateEvent> OnWorldUpdate;
    public event Action<string> OnChatContent;

    async void Start()
    {
        // Get JWT token from authentication
        jwtToken = await AuthManager.GetAccessToken();

        // Connect to WebSocket with JWT in query param
        string url = $"{serverUrl}?token={jwtToken}";
        websocket = new WebSocket(url);

        // Event handlers
        websocket.OnOpen += () =>
        {
            Debug.Log("WebSocket Connected!");
        };

        websocket.OnMessage += (bytes) =>
        {
            string message = System.Text.Encoding.UTF8.GetString(bytes);
            HandleMessage(message);
        };

        websocket.OnError += (errorMsg) =>
        {
            Debug.LogError($"WebSocket Error: {errorMsg}");
        };

        websocket.OnClose += (closeCode) =>
        {
            Debug.Log($"WebSocket Closed: {closeCode}");
        };

        // Connect
        await websocket.Connect();
    }

    void Update()
    {
        // Dispatch WebSocket messages on main thread
        #if !UNITY_WEBGL || UNITY_EDITOR
        websocket?.DispatchMessageQueue();
        #endif
    }

    void HandleMessage(string json)
    {
        var message = JsonConvert.DeserializeObject<WebSocketMessage>(json);

        switch (message.type)
        {
            case "connected":
                Debug.Log($"Connected: {message.connection_id}");
                break;

            case "world_update":
                var worldUpdate = JsonConvert.DeserializeObject<WorldUpdateEvent>(
                    message.data.ToString()
                );
                OnWorldUpdate?.Invoke(worldUpdate);
                break;

            case "content":
                OnChatContent?.Invoke(message.content);
                break;

            case "heartbeat":
                // Connection is alive
                break;

            case "pong":
                // Ping response
                break;

            case "error":
                Debug.LogError($"Server error: {message.error}");
                break;
        }
    }

    public async void SendChatMessage(string message, string experience)
    {
        var payload = new
        {
            type = "chat",
            message = message,
            context = new
            {
                experience = experience
            }
        };

        string json = JsonConvert.SerializeObject(payload);
        await websocket.SendText(json);
    }

    public async void SendPing()
    {
        var payload = new { type = "ping" };
        string json = JsonConvert.SerializeObject(payload);
        await websocket.SendText(json);
    }

    async void OnApplicationQuit()
    {
        if (websocket != null)
        {
            await websocket.Close();
        }
    }
}

[Serializable]
public class WebSocketMessage
{
    public string type;
    public string connection_id;
    public string user_id;
    public object data;
    public string content;
    public string error;
    public long timestamp;
}

[Serializable]
public class WorldUpdateEvent
{
    public string type;           // "world_update"
    public string version;        // "0.3"
    public string experience;     // "wylding-woods"
    public string user_id;
    public Dictionary<string, object> changes;
    public long timestamp;
    public Dictionary<string, string> metadata;
}
```

### Unity DirectiveQueue Integration

```csharp
// DirectiveQueue consumes events (unchanged - transport-agnostic)
public class DirectiveQueueManager : MonoBehaviour
{
    private GaiaWebSocketClient wsClient;

    void Start()
    {
        wsClient = GetComponent<GaiaWebSocketClient>();
        wsClient.OnWorldUpdate += ProcessWorldUpdate;
    }

    void ProcessWorldUpdate(WorldUpdateEvent evt)
    {
        // Same logic as SSE implementation - DirectiveQueue is transport-agnostic
        foreach (var change in evt.changes)
        {
            string category = change.Key;  // "world", "player", etc.
            var updates = change.Value as Dictionary<string, object>;

            foreach (var update in updates)
            {
                string path = update.Key;
                var operation = update.Value as Dictionary<string, object>;

                // Process directive
                ProcessDirective(category, path, operation);
            }
        }
    }

    void ProcessDirective(string category, string path, Dictionary<string, object> operation)
    {
        // Existing DirectiveQueue logic (unchanged)
        // ...
    }
}
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_websocket_manager.py
import pytest
from app.services.chat.websocket_manager import ConnectionManager
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_connection_manager_lifecycle():
    """Test WebSocket connection and NATS subscription lifecycle."""
    nats_client = Mock()
    nats_client.is_connected = True
    nats_client.subscribe = AsyncMock(return_value=Mock())

    manager = ConnectionManager(nats_client)

    # Mock WebSocket
    websocket = Mock()
    websocket.accept = AsyncMock()
    websocket.close = AsyncMock()
    websocket.send_json = AsyncMock()

    # Connect
    await manager.connect(websocket, "user-123", "conn-abc")

    # Verify NATS subscription created
    nats_client.subscribe.assert_called_once()
    assert manager.get_active_connections_count() == 1
    assert manager.is_user_connected("user-123")

    # Disconnect
    await manager.disconnect("conn-abc")

    # Verify cleanup
    assert manager.get_active_connections_count() == 0
    assert not manager.is_user_connected("user-123")

@pytest.mark.asyncio
async def test_send_to_connection():
    """Test sending messages to specific WebSocket."""
    nats_client = Mock()
    nats_client.is_connected = False  # Graceful degradation

    manager = ConnectionManager(nats_client)

    websocket = Mock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()

    await manager.connect(websocket, "user-123", "conn-abc")

    # Send message
    success = await manager.send_to_connection("conn-abc", {
        "type": "test",
        "data": "hello"
    })

    assert success
    websocket.send_json.assert_called_once()
```

### Integration Tests

```python
# tests/integration/test_websocket_e2e.py
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
import asyncio

@pytest.mark.asyncio
async def test_websocket_chat_flow(test_app, test_user):
    """
    End-to-end test: Connect WebSocket, send chat message, receive response.
    """
    from fastapi.testclient import TestClient

    with TestClient(test_app) as client:
        # Get JWT token
        token = await get_test_token(test_user)

        # Connect WebSocket
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            # Receive connected message
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "connection_id" in data

            # Send chat message
            websocket.send_json({
                "type": "chat",
                "message": "Hello GAIA",
                "context": {"experience": "wylding-woods"}
            })

            # Receive metadata
            data = websocket.receive_json()
            assert data["type"] == "metadata"

            # Receive content chunks
            content_received = False
            while True:
                data = websocket.receive_json()
                if data["type"] == "content":
                    content_received = True
                elif data["type"] == "done":
                    break

            assert content_received

@pytest.mark.asyncio
async def test_nats_world_update_delivery(test_app, test_user):
    """
    Test that NATS world_update events are delivered via WebSocket.
    """
    # This test requires:
    # 1. WebSocket connection
    # 2. Trigger KB state change (publishes to NATS)
    # 3. Verify world_update arrives via WebSocket

    # Implementation depends on test infrastructure
    # See tests/integration/test_nats_world_updates.py for similar pattern
```

### Load Testing

```python
# tests/load/test_websocket_concurrent.py
import asyncio
import websockets
import time

async def test_concurrent_connections():
    """Test 100 concurrent WebSocket connections."""
    async def connect_client(client_id: int):
        uri = f"ws://localhost:8666/ws?token={get_token(client_id)}"

        async with websockets.connect(uri) as websocket:
            # Receive connected message
            msg = await websocket.recv()

            # Send ping every 5 seconds
            for _ in range(10):
                await websocket.send('{"type":"ping"}')
                response = await websocket.recv()
                await asyncio.sleep(5)

    # Create 100 concurrent connections
    tasks = [connect_client(i) for i in range(100)]
    await asyncio.gather(*tasks)
```

---

## Performance Considerations

### Connection Limits

**Per-service limits**:
- FastAPI/Uvicorn: ~10,000 connections per worker (async I/O)
- NATS: 1M+ messages/sec (easily handles 10,000 persistent subscriptions)
- Docker: No inherent limits (depends on host resources)

**Scaling strategy**:
- Horizontal: Multiple chat service instances behind load balancer
- Connection affinity: Sticky sessions (same user → same instance)
- NATS handles message routing across instances automatically

### Memory Usage

**Per WebSocket connection**:
- WebSocket object: ~1KB
- NATS subscription: ~500 bytes
- Heartbeat task: ~500 bytes
- **Total: ~2KB per connection**

**1000 concurrent connections**: ~2MB memory overhead (negligible)

### Latency Comparison

**SSE (per-request)**:
```
User action → HTTP POST → SSE stream → Response
Overhead: ~50-100ms (connection setup per request)
```

**WebSocket (persistent)**:
```
User action → WebSocket send → Response
Overhead: ~5-10ms (no reconnection)
```

**Projected improvement**: **5-10x latency reduction** for interactive commands

---

## Rollback Plan

If WebSocket issues are discovered after migration:

### Immediate Rollback (Same Day)

```bash
# Revert to previous deployment
git revert <websocket-commit-sha>
./scripts/deploy.sh --env production --services chat
```

### Gradual Rollback (Week 1-2)

- Keep both SSE and WebSocket active
- Add feature flag: `ENABLE_WEBSOCKET=false`
- Unity clients fall back to SSE
- Monitor for stability, re-enable WebSocket when fixed

### Code Rollback Points

1. **WebSocket endpoints only**: Remove `websocket_endpoints.py`, keep SSE
2. **Connection manager only**: Keep endpoints, remove persistent subscriptions
3. **Full rollback**: Remove all WebSocket code, restore SSE-only

---

## Success Criteria

### Phase 1 Complete When:
- [ ] WebSocket endpoints deployed and accessible
- [ ] ConnectionManager handles connect/disconnect lifecycle
- [ ] NATS subscriptions persist for WebSocket lifetime
- [ ] Both SSE and WebSocket work simultaneously
- [ ] Health check shows WebSocket connection count
- [ ] Unit tests pass (connection lifecycle, message sending)

### Phase 2 Complete When:
- [ ] Unity clients successfully connect via WebSocket
- [ ] Autonomous world events delivered (tested with manual NATS publish)
- [ ] Latency measurements show <50ms for WebSocket messages
- [ ] Error rate <0.1% for WebSocket connections
- [ ] Load testing: 100 concurrent connections stable

### Phase 3 Complete When:
- [ ] 90%+ clients using WebSocket (SSE usage <10%)
- [ ] SSE endpoints removed from codebase
- [ ] Documentation updated (only WebSocket documented)
- [ ] Operational runbooks updated (only WebSocket troubleshooting)

---

## Documentation Updates Required

After implementation, update these files:

1. **`docs/scratchpad/nats-world-updates-implementation-analysis.md`**
   - Add banner: "Transport layer superseded by WebSocket, see websocket-migration-plan.md"
   - Update Phase 2 section to reference WebSocket implementation

2. **`docs/scratchpad/PHASE-1B-ACTUAL-COMPLETION.md`**
   - Update Phase 2 section with link to this document
   - Mark SSE implementation as "Legacy - use for reference only"

3. **`docs/scratchpad/simulation-architecture-overview.md`**
   - Update line 16: Replace "Server-Sent Events (SSE)" with "WebSocket connections"
   - Update latency projections (WebSocket lower than SSE)

4. **`docs/scratchpad/TODO.md`**
   - Add Phase 5: WebSocket Migration (this document)
   - Mark Phase 1A/1B as complete dependencies

5. **`docs/api/chat-endpoints.md`** (main docs, if exists)
   - Document WebSocket protocol
   - Mark SSE endpoints as deprecated (Phase 3)

---

## References

### Related Scratchpad Documents
- `nats-world-updates-implementation-analysis.md` - Original NATS architecture (SSE-based)
- `PHASE-1B-ACTUAL-COMPLETION.md` - SSE implementation status
- `simulation-architecture-overview.md` - High-level architecture
- `TODO.md` - Phase tracking

### External Resources
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [NATS Python Client](https://github.com/nats-io/nats.py)
- [Unity NativeWebSocket](https://github.com/endel/NativeWebSocket)
- [WebSocket Protocol RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)

---

**Document Status**: ✅ Planning Complete
**Next Step**: Implement Phase 1 (Dual Support)
**Owner**: Server team + Unity team (client integration)
**Timeline**: 9-13 hours server implementation + 3-4 hours Unity client
