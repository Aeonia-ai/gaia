"""
Experience Connection Manager for WebSocket Connections

Manages WebSocket lifecycle for real-time experience interactions:
- Connection acceptance and cleanup
- Persistent NATS subscriptions per connection
- Message routing between NATS and WebSocket
- Graceful disconnection handling

This is a SIMPLIFIED implementation for AEO-65 demo (Option C):
- No heartbeat mechanism (add in Option B)
- Basic connection tracking only
- Demo-focused scope (bottle quest)

Author: GAIA Platform Team
Created: 2025-11-05 (AEO-65 Demo Implementation)
"""

import asyncio
import logging
import uuid
from typing import Dict, Optional, Any
from fastapi import WebSocket
from datetime import datetime

from app.shared.nats_client import NATSClient, NATSSubjects

logger = logging.getLogger(__name__)


class ExperienceConnectionManager:
    """
    Manages WebSocket connections for real-time experience interactions.

    Simplified version for AEO-65 demo - focused on bottle quest functionality.
    Production features (heartbeat, reconnection, advanced error recovery) deferred.

    Key Responsibilities:
    - Accept WebSocket connections with JWT authentication
    - Create persistent NATS subscriptions for world updates
    - Forward NATS events to WebSocket clients
    - Handle incoming player actions
    - Clean up resources on disconnect

    Architecture:
    - One WebSocket connection per player session
    - One NATS subscription per connection (world.updates.user.{user_id})
    - Direct integration with UnifiedStateManager for state changes
    """

    def __init__(self, nats_client: Optional[NATSClient] = None):
        """
        Initialize connection manager.

        Args:
            nats_client: Optional NATS client for real-time updates
                        If None, WebSocket works but no NATS events
        """
        # Track active WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}

        # Map user_id -> connection_id for quick lookup
        self.user_connections: Dict[str, str] = {}

        # Track NATS subscriptions per connection
        self.nats_subscriptions: Dict[str, Any] = {}

        # NATS client for real-time updates
        self.nats_client = nats_client

        # Connection metadata (for debugging/monitoring)
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

        logger.info("ExperienceConnectionManager initialized")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_id: Optional[str] = None,
        experience: str = "wylding-woods"
    ) -> str:
        """
        Accept WebSocket connection and set up NATS subscription.

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Authenticated user ID
            connection_id: Optional connection ID (generated if not provided)
            experience: Experience ID (default: wylding-woods)

        Returns:
            Connection ID for this session
        """
        logger.warning(f"[CONNECT-DEBUG] connect() called for user_id={user_id}, experience={experience}")

        # Generate connection ID if not provided
        if connection_id is None:
            connection_id = str(uuid.uuid4())

        # Accept WebSocket connection
        await websocket.accept()

        # Store connection
        self.active_connections[connection_id] = websocket
        self.user_connections[user_id] = connection_id

        # Initialize player state (create view file if first-time connection)
        # Do this BEFORE storing metadata so we can get current world version
        current_world_version = 0
        try:
            from app.services.kb.kb_agent import kb_agent
            if kb_agent.state_manager:
                await kb_agent.state_manager.ensure_player_initialized(experience, user_id)
                logger.debug(f"Player initialized for {user_id} in {experience}")

                # Get current world version for client tracking initialization
                try:
                    world_state = await kb_agent.state_manager.get_world_state(experience)
                    current_world_version = world_state.get("metadata", {}).get("_version", 0)
                except Exception as e:
                    logger.warning(f"Could not load world version, defaulting to 0: {e}")
                    current_world_version = 0
        except Exception as e:
            logger.error(f"Failed to initialize player {user_id}: {e}", exc_info=True)
            # Continue anyway - state operations will fail gracefully

        # Store metadata with initial snapshot_version
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "experience": experience,
            "connected_at": datetime.utcnow().isoformat() + "Z",
            "messages_sent": 0,
            "messages_received": 0,
            "snapshot_version": current_world_version  # Initialize to current world version
        }

        logger.info(
            f"WebSocket connected: connection_id={connection_id}, "
            f"user_id={user_id}, experience={experience}, "
            f"initial_version={current_world_version}"
        )

        # Create persistent NATS subscription
        logger.warning(
            f"[CONNECT-DEBUG] Checking NATS: "
            f"nats_client={'present' if self.nats_client else 'None'}, "
            f"is_connected={self.nats_client.is_connected if self.nats_client else 'N/A'}"
        )
        if self.nats_client and self.nats_client.is_connected:
            logger.warning(f"[CONNECT-DEBUG] Calling _subscribe_to_nats for connection_id={connection_id}")
            await self._subscribe_to_nats(connection_id, user_id, websocket)
        else:
            logger.warning(
                f"[CONNECT-DEBUG] NATS check FAILED - "
                f"NATS client not available for connection {connection_id} - "
                f"real-time updates disabled"
            )

        return connection_id

    async def _subscribe_to_nats(
        self,
        connection_id: str,
        user_id: str,
        websocket: WebSocket
    ) -> None:
        """
        Create persistent NATS subscription for this connection.

        Args:
            connection_id: Connection ID
            user_id: User ID
            websocket: WebSocket instance to forward events to
        """
        # Define NATS event handler
        async def nats_event_handler(event_data: Dict[str, Any]):
            """Forward NATS event to WebSocket client."""
            logger.warning(f"[WS-FORWARD-DEBUG] nats_event_handler called for connection {connection_id}, event_type={event_data.get('type')}")

            # Check if connection is still active (prevent race condition)
            if connection_id not in self.active_connections:
                logger.warning(
                    f"[WS-FORWARD-DEBUG] Skipping NATS event for closed connection: {connection_id}"
                )
                return

            try:
                logger.warning(f"[WS-FORWARD-DEBUG] Sending event to WebSocket: connection_id={connection_id}")
                # Send event to WebSocket
                await websocket.send_json(event_data)

                # Update metrics
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["messages_sent"] += 1

                logger.warning(
                    f"[WS-FORWARD-DEBUG] ✅ Forwarded NATS event to WebSocket: "
                    f"connection_id={connection_id}, "
                    f"event_type={event_data.get('type')}"
                )
            except Exception as e:
                logger.error(
                    f"[WS-FORWARD-DEBUG] ❌ Failed to forward NATS event to WebSocket "
                    f"(connection_id={connection_id}): {e}",
                    exc_info=True
                )

        # Calculate the subject we'll subscribe to
        nats_subject = NATSSubjects.world_update_user(user_id)

        # CRITICAL FIX: Clean up any existing subscriptions for this user
        # This prevents zombie subscriptions when Unity reconnects
        old_subscriptions_cleaned = 0
        for old_conn_id, old_subject in list(self.nats_subscriptions.items()):
            if old_subject == nats_subject and old_conn_id != connection_id:
                logger.warning(
                    f"[NATS-CLEANUP] Found old subscription for user {user_id}: "
                    f"old_connection={old_conn_id}, new_connection={connection_id}"
                )
                try:
                    await self.nats_client.unsubscribe(old_subject)
                    old_subscriptions_cleaned += 1
                    logger.warning(
                        f"[NATS-CLEANUP] ✅ Cleaned up old subscription: "
                        f"connection={old_conn_id}, subject={old_subject}"
                    )
                except Exception as e:
                    logger.warning(
                        f"[NATS-CLEANUP] ⚠️ Failed to cleanup old subscription "
                        f"(connection={old_conn_id}): {e}"
                    )
                # Remove from tracking regardless of unsubscribe success
                if old_conn_id in self.nats_subscriptions:
                    del self.nats_subscriptions[old_conn_id]

        if old_subscriptions_cleaned > 0:
            logger.warning(
                f"[NATS-CLEANUP] Cleaned up {old_subscriptions_cleaned} zombie "
                f"subscription(s) for user {user_id}"
            )

        try:
            # Subscribe to user-specific world updates
            logger.warning(f"[NATS-SUB-DEBUG] Attempting to subscribe to: {nats_subject}")
            await self.nats_client.subscribe(nats_subject, nats_event_handler)

            # Track subscription for cleanup
            self.nats_subscriptions[connection_id] = nats_subject

            logger.warning(
                f"[NATS-SUB-DEBUG] ✅ NATS subscription created: connection_id={connection_id}, "
                f"subject={nats_subject}"
            )
        except Exception as e:
            logger.error(
                f"[NATS-SUB-DEBUG] ❌ Failed to create NATS subscription for connection "
                f"{connection_id}: {e}", exc_info=True
            )

    async def disconnect(self, connection_id: str) -> None:
        """
        Disconnect WebSocket and clean up resources.

        Args:
            connection_id: Connection ID to disconnect
        """
        # Get metadata before cleanup
        metadata = self.connection_metadata.get(connection_id, {})
        user_id = metadata.get("user_id")

        # Clean up NATS subscription
        if connection_id in self.nats_subscriptions:
            nats_subject = self.nats_subscriptions[connection_id]

            if self.nats_client and self.nats_client.is_connected:
                try:
                    await self.nats_client.unsubscribe(nats_subject)
                    logger.info(
                        f"NATS subscription cleaned up: connection_id={connection_id}, "
                        f"subject={nats_subject}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to unsubscribe from NATS "
                        f"(connection_id={connection_id}): {e}"
                    )

            del self.nats_subscriptions[connection_id]

        # Remove connection tracking
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]

        # Log disconnect with metrics
        if connection_id in self.connection_metadata:
            logger.info(
                f"WebSocket disconnected: connection_id={connection_id}, "
                f"user_id={user_id}, "
                f"messages_sent={metadata.get('messages_sent', 0)}, "
                f"messages_received={metadata.get('messages_received', 0)}, "
                f"duration={(datetime.utcnow().isoformat() + 'Z') if 'connected_at' in metadata else 'unknown'}"
            )
            del self.connection_metadata[connection_id]

    async def send_message(
        self,
        connection_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """
        Send message to specific WebSocket connection.

        Args:
            connection_id: Connection ID
            message: Message dict to send as JSON

        Returns:
            True if sent successfully, False otherwise
        """
        if connection_id not in self.active_connections:
            logger.warning(
                f"Attempted to send message to non-existent connection: {connection_id}"
            )
            return False

        websocket = self.active_connections[connection_id]

        try:
            await websocket.send_json(message)

            # Update metrics
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["messages_sent"] += 1

            return True
        except Exception as e:
            logger.error(
                f"Failed to send message to connection {connection_id}: {e}"
            )
            return False

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for specific connection."""
        return self.connection_metadata.get(connection_id)

    def is_connected(self, user_id: str) -> bool:
        """Check if user has active WebSocket connection."""
        return user_id in self.user_connections

    def get_user_connection_id(self, user_id: str) -> Optional[str]:
        """Get connection ID for user (if connected)."""
        return self.user_connections.get(user_id)

    def get_client_version(self, connection_id: str) -> int:
        """
        Get the client's current snapshot version.

        This is the version that the client has in memory. When sending deltas,
        we must use this as the base_version to ensure the client can apply them.

        Args:
            connection_id: Connection ID

        Returns:
            Client's current snapshot_version, or 0 if not tracked
        """
        metadata = self.connection_metadata.get(connection_id, {})
        return metadata.get("snapshot_version", 0)

    def update_client_version(self, connection_id: str, snapshot_version: int) -> None:
        """
        Update the client's snapshot version after successful delta application.

        This must be called after publishing a world_update delta so we track
        what version the client is at for future deltas.

        Args:
            connection_id: Connection ID
            snapshot_version: New snapshot version after delta applied
        """
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["snapshot_version"] = snapshot_version
            logger.debug(
                f"[VERSION-TRACK] Updated client version: "
                f"connection={connection_id}, snapshot_version={snapshot_version}"
            )
