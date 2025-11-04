"""
Event schemas for GAIA Platform real-time updates.

This module defines Pydantic models for events published to NATS for real-time
synchronization between server and clients (Unity AR/VR).
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal


class WorldUpdateEvent(BaseModel):
    """
    Real-time world state update event published to NATS.

    This event represents a state delta (what changed) rather than full state.
    Follows the state delta pattern used by Minecraft, Roblox, and WoW for
    efficient real-time synchronization.

    Published to: world.updates.user.{user_id}

    Example:
        {
            "type": "world_update",
            "version": "0.3",
            "experience": "wylding-woods",
            "user_id": "a7f4370e-0af5-40eb-bb18-fcc10538b041",
            "changes": {
                "world.locations.woander_store.items": {
                    "operation": "remove",
                    "item": {"id": "bottle_of_joy_3", "type": "collectible"}
                },
                "player.inventory": {
                    "operation": "add",
                    "item": {"id": "bottle_of_joy_3", "type": "collectible"}
                }
            },
            "timestamp": 1730678400000,
            "metadata": {
                "source": "kb_service",
                "state_model": "shared"
            }
        }
    """

    type: Literal["world_update"] = "world_update"
    """Event type identifier (always 'world_update')"""

    version: str = Field(default="0.3")
    """Protocol version for schema evolution and Unity compatibility"""

    experience: str
    """Experience/game identifier (e.g., 'wylding-woods')"""

    user_id: str
    """User UUID that this update applies to"""

    changes: Dict[str, Any]
    """
    State delta describing what changed. Each key is a state path, each value
    contains an 'operation' field ('add', 'remove', or 'update') and the
    relevant data.
    """

    timestamp: int
    """Unix timestamp in milliseconds when the change occurred"""

    metadata: Optional[Dict[str, Any]] = None
    """
    Optional metadata for debugging, tracing, or client-side processing hints.
    Common fields: source (service name), state_model (shared/private), trace_id
    """

    class Config:
        json_schema_extra = {
            "example": {
                "type": "world_update",
                "version": "0.3",
                "experience": "wylding-woods",
                "user_id": "a7f4370e-0af5-40eb-bb18-fcc10538b041",
                "changes": {
                    "player.inventory": {
                        "operation": "add",
                        "item": {
                            "id": "bottle_of_joy_3",
                            "type": "collectible",
                            "name": "Bottle of Joy"
                        }
                    }
                },
                "timestamp": 1730678400000,
                "metadata": {
                    "source": "kb_service",
                    "state_model": "shared"
                }
            }
        }
