"""
NATS client configuration and utilities for Gaia Platform microservices.
"""
import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional, Callable, Awaitable
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrTimeout, ErrNoServers

logger = logging.getLogger(__name__)

class NATSClient:
    """NATS client for inter-service communication in Gaia Platform."""
    
    def __init__(self, nats_url: Optional[str] = None):
        self.nats_url = nats_url or os.getenv('NATS_URL', 'nats://localhost:4222')
        self.nc: Optional[NATS] = None
        self._connected = False
        self._subscriptions: Dict[str, Any] = {}  # Track subject -> subscription object mapping
    
    async def connect(self) -> None:
        """Connect to NATS server."""
        if self._connected:
            return
            
        try:
            self.nc = NATS()
            await self.nc.connect(self.nats_url)
            self._connected = True
            logger.info(f"Connected to NATS at {self.nats_url}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        if self.nc and self._connected:
            await self.nc.close()
            self._connected = False
            logger.info("Disconnected from NATS")
    
    async def publish(self, subject: str, data: Any, headers: Optional[Dict[str, str]] = None) -> None:
        """Publish a message to a NATS subject."""
        if not self._connected:
            await self.connect()
        
        try:
            message_data = json.dumps(data).encode() if not isinstance(data, bytes) else data
            await self.nc.publish(subject, message_data, headers=headers)
            logger.debug(f"Published message to {subject}")
        except Exception as e:
            logger.error(f"Failed to publish to {subject}: {e}")
            raise
    
    async def subscribe(
        self,
        subject: str,
        callback: Callable[[Any], Awaitable[None]],
        queue: Optional[str] = None
    ) -> None:
        """Subscribe to a NATS subject with a callback function.

        Args:
            subject: NATS subject to subscribe to
            callback: Async callback function that receives the message data
            queue: Optional queue group name for load balancing
        """
        if not self._connected:
            await self.connect()

        async def message_handler(msg):
            try:
                data = json.loads(msg.data.decode())
                await callback(data)
            except Exception as e:
                logger.error(f"Error processing message from {subject}: {e}")

        try:
            subscription = await self.nc.subscribe(subject, cb=message_handler, queue=queue)
            self._subscriptions[subject] = subscription  # Track subscription object
            logger.info(f"Subscribed to {subject}" + (f" (queue: {queue})" if queue else ""))
        except Exception as e:
            logger.error(f"Failed to subscribe to {subject}: {e}")
            raise

    async def unsubscribe(self, subject: str) -> None:
        """Unsubscribe from a NATS subject.

        Args:
            subject: NATS subject to unsubscribe from
        """
        if subject not in self._subscriptions:
            logger.warning(f"Attempted to unsubscribe from {subject} but no active subscription found")
            return

        try:
            subscription = self._subscriptions[subject]
            await subscription.unsubscribe()
            del self._subscriptions[subject]
            logger.info(f"Unsubscribed from {subject}")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {subject}: {e}")
            # Clean up tracking even if unsubscribe fails
            if subject in self._subscriptions:
                del self._subscriptions[subject]
            raise
    
    async def request(self, subject: str, data: Any, timeout: float = 5.0) -> Any:
        """Send a request and wait for a response."""
        if not self._connected:
            await self.connect()
        
        try:
            message_data = json.dumps(data).encode() if not isinstance(data, bytes) else data
            response = await self.nc.request(subject, message_data, timeout=timeout)
            return json.loads(response.data.decode())
        except ErrTimeout:
            logger.error(f"Request to {subject} timed out")
            raise
        except Exception as e:
            logger.error(f"Failed to send request to {subject}: {e}")
            raise
    
    @property
    def is_connected(self) -> bool:
        """Check if NATS client is connected."""
        return self._connected and self.nc is not None

# Global NATS client instance
_nats_client: Optional[NATSClient] = None

def get_nats_client() -> NATSClient:
    """Get or create the global NATS client instance."""
    global _nats_client
    if _nats_client is None:
        _nats_client = NATSClient()
    return _nats_client

async def ensure_nats_connection() -> NATSClient:
    """Ensure NATS client is connected and return it."""
    client = get_nats_client()
    if not client.is_connected:
        await client.connect()
    return client

# Common NATS subjects for Gaia Platform
class NATSSubjects:
    """Standard NATS subjects used across Gaia Platform services."""
    
    # Service health and discovery
    SERVICE_HEALTH = "gaia.service.health"
    SERVICE_READY = "gaia.service.ready"
    
    # Authentication events
    AUTH_VALIDATE = "gaia.auth.validate"
    AUTH_REFRESH = "gaia.auth.refresh"
    
    # Asset events
    ASSET_GENERATION_START = "gaia.asset.generation.start"
    ASSET_GENERATION_COMPLETE = "gaia.asset.generation.complete"
    ASSET_GENERATION_FAILED = "gaia.asset.generation.failed"
    
    # Chat events
    CHAT_MESSAGE_START = "gaia.chat.message.start"
    CHAT_MESSAGE_COMPLETE = "gaia.chat.message.complete"
    CHAT_MESSAGE_FAILED = "gaia.chat.message.failed"
    
    # Service-to-service requests
    AUTH_SERVICE_REQUEST = "gaia.service.auth.request"
    ASSET_SERVICE_REQUEST = "gaia.service.asset.request"
    CHAT_SERVICE_REQUEST = "gaia.service.chat.request"

    # World updates (for MMOIRL real-time events)
    @staticmethod
    def world_update_user(user_id: str) -> str:
        """Get the NATS subject for a specific user's world updates.

        Args:
            user_id: The user ID to subscribe to

        Returns:
            Subject string in format: world.updates.user.{user_id}
        """
        return f"world.updates.user.{user_id}"

# Event data classes for type safety
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ServiceHealthEvent(BaseModel):
    service_name: str
    status: str  # "healthy", "unhealthy", "starting", "stopping"
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None

class AssetGenerationEvent(BaseModel):
    asset_id: str
    user_id: str
    asset_type: str
    status: str  # "started", "completed", "failed"
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None

class ChatMessageEvent(BaseModel):
    message_id: str
    user_id: str
    persona_id: Optional[str] = None
    status: str  # "started", "completed", "failed"
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
