"""
Event schemas for GAIA Platform real-time updates.

This module defines Pydantic models for events published to NATS for real-time
synchronization between server and clients (Unity AR/VR).
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal, List


class WorldUpdateEvent(BaseModel):
    """
    Real-time world state update event published to NATS (v0.4).

    This event represents a state delta (what changed) rather than full state.
    Follows the state delta pattern used by Minecraft, Roblox, and WoW for
    efficient real-time synchronization.

    v0.4 Changes:
    - Uses instance_id/template_id (matches AOI structure)
    - Array-based changes format (not dict)
    - Version tracking with base_version/snapshot_version
    - Full template data merged into items

    Published to: world.updates.user.{user_id}

    Example (collect item):
        {
            "type": "world_update",
            "version": "0.4",
            "experience": "wylding-woods",
            "user_id": "a7f4370e-0af5-40eb-bb18-fcc10538b041",
            "base_version": 12345,
            "snapshot_version": 12346,
            "changes": [
                {
                    "operation": "remove",
                    "area_id": "spawn_zone_1",
                    "instance_id": "dream_bottle_woander_1"
                },
                {
                    "operation": "add",
                    "area_id": null,
                    "path": "player.inventory",
                    "item": {
                        "instance_id": "dream_bottle_woander_1",
                        "template_id": "dream_bottle",
                        "semantic_name": "dream bottle",
                        "description": "A bottle glowing with inner light...",
                        "collectible": true,
                        "state": {"collected_at": "2025-11-10T12:00:00Z"}
                    }
                }
            ],
            "timestamp": 1731240000000,
            "metadata": {
                "source": "kb_service",
                "state_model": "shared"
            }
        }
    """

    type: Literal["world_update"] = "world_update"
    """Event type identifier (always 'world_update')"""

    version: str = Field(default="0.4")
    """Protocol version for schema evolution and Unity compatibility"""

    experience: str
    """Experience/game identifier (e.g., 'wylding-woods')"""

    user_id: str
    """User UUID that this update applies to"""

    base_version: int
    """
    Version number this delta applies on top of. Client must be at this version
    to safely apply the delta. If client version != base_version, client should
    request fresh AOI snapshot.
    """

    snapshot_version: int
    """
    New version number after applying this delta. Client should update their
    local version to this value after successfully applying changes.
    """

    changes: List[Dict[str, Any]]
    """
    Array of change operations. Each change contains:
    - operation: "add" | "remove" | "update"
    - area_id: Area identifier (null for inventory)
    - path: Optional explicit path (e.g., "player.inventory")
    - instance_id: Entity instance ID (required)
    - template_id: Entity template ID (optional for remove)
    - item: Full item data with template properties merged (for add/update)
    - metadata: Optional metadata (reason, actor, etc.)
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
                "version": "0.4",
                "experience": "wylding-woods",
                "user_id": "a7f4370e-0af5-40eb-bb18-fcc10538b041",
                "base_version": 12345,
                "snapshot_version": 12346,
                "changes": [
                    {
                        "operation": "remove",
                        "area_id": "spawn_zone_1",
                        "instance_id": "dream_bottle_woander_1"
                    },
                    {
                        "operation": "add",
                        "area_id": None,
                        "path": "player.inventory",
                        "item": {
                            "instance_id": "dream_bottle_woander_1",
                            "template_id": "dream_bottle",
                            "semantic_name": "dream bottle",
                            "description": "A bottle glowing with inner light...",
                            "collectible": True,
                            "state": {"collected_at": "2025-11-10T12:00:00Z"}
                        }
                    }
                ],
                "timestamp": 1731240000000,
                "metadata": {
                    "source": "kb_service",
                    "state_model": "shared"
                }
            }
        }
