# app/services/kb/command_registry.py
"""
Command registry with JSON Schema definitions for protocol introspection.

Provides self-documenting API capabilities inspired by GraphQL introspection
and gRPC reflection, adapted for WebSocket real-time protocols.

Usage:
    from app.services.kb.command_registry import get_command_schemas

    schemas = get_command_schemas()
    # Returns dict of command name -> JSON Schema
"""

from typing import Dict, Any


# JSON Schema definitions for all fast commands
# Format: JSON Schema draft-07 for maximum tooling compatibility
COMMAND_SCHEMAS: Dict[str, Any] = {
    "go": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Navigate Command",
        "description": "Move between areas within your current location",
        "type": "object",
        "required": ["type", "action", "destination"],
        "properties": {
            "type": {
                "const": "action",
                "description": "Message type"
            },
            "action": {
                "const": "go",
                "description": "Command name"
            },
            "destination": {
                "type": "string",
                "description": "Target area ID within current location"
            }
        },
        "examples": [{
            "type": "action",
            "action": "go",
            "destination": "spawn_zone_1"
        }],
        "metadata": {
            "avg_response_time_ms": 6,
            "response_types": ["action_response", "world_update"]
        }
    },

    "collect_item": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Collect Item Command",
        "description": "Pick up an item from the world",
        "type": "object",
        "required": ["type", "action", "instance_id"],
        "properties": {
            "type": {"const": "action"},
            "action": {"const": "collect_item"},
            "instance_id": {
                "type": "string",
                "description": "Unique identifier of the item to collect"
            }
        },
        "examples": [{
            "type": "action",
            "action": "collect_item",
            "instance_id": "dream_bottle_1"
        }],
        "metadata": {
            "avg_response_time_ms": 5,
            "response_types": ["action_response", "world_update"],
            "validation": [
                "Player must be in same location/area as item",
                "Item must be collectible: true"
            ]
        }
    },

    "drop_item": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Drop Item Command",
        "description": "Drop an item from inventory into the world at your current location",
        "type": "object",
        "required": ["type", "action", "instance_id"],
        "properties": {
            "type": {"const": "action"},
            "action": {"const": "drop_item"},
            "instance_id": {
                "type": "string",
                "description": "Item identifier from player inventory"
            }
        },
        "examples": [{
            "type": "action",
            "action": "drop_item",
            "instance_id": "health_potion_1"
        }],
        "metadata": {
            "avg_response_time_ms": 7,
            "response_types": ["action_response", "world_update"],
            "validation": [
                "Item must exist in player inventory"
            ]
        }
    },

    "examine": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Examine Item Command",
        "description": "Inspect an item for detailed information (read-only, no state change)",
        "type": "object",
        "required": ["type", "action", "instance_id"],
        "properties": {
            "type": {"const": "action"},
            "action": {"const": "examine"},
            "instance_id": {
                "type": "string",
                "description": "Item identifier to examine"
            }
        },
        "examples": [{
            "type": "action",
            "action": "examine",
            "instance_id": "dream_bottle_2"
        }],
        "metadata": {
            "avg_response_time_ms": 3,
            "response_types": ["action_response"],
            "search_order": "Player inventory → current area → current location"
        }
    },

    "use_item": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Use Item Command",
        "description": "Consume or activate an item from inventory",
        "type": "object",
        "required": ["type", "action", "instance_id"],
        "properties": {
            "type": {"const": "action"},
            "action": {"const": "use_item"},
            "instance_id": {
                "type": "string",
                "description": "Item identifier from inventory to use"
            }
        },
        "examples": [{
            "type": "action",
            "action": "use_item",
            "instance_id": "health_potion_1"
        }],
        "metadata": {
            "avg_response_time_ms": 4,
            "response_types": ["action_response", "world_update"],
            "effects": [
                "Health restoration: Updates player.stats.health",
                "Status effects: Adds to player.status_effects[]",
                "Consumables: Removed from inventory after use"
            ]
        }
    },

    "inventory": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Inventory List Command",
        "description": "Get formatted list of items in player inventory (read-only)",
        "type": "object",
        "required": ["type", "action"],
        "properties": {
            "type": {"const": "action"},
            "action": {"const": "inventory"}
        },
        "examples": [{
            "type": "action",
            "action": "inventory"
        }],
        "metadata": {
            "avg_response_time_ms": 2,
            "response_types": ["action_response"]
        }
    },

    "give_item": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Give Item Command",
        "description": "Transfer item from player to NPC or another player",
        "type": "object",
        "required": ["type", "action", "instance_id", "target_npc_id"],
        "properties": {
            "type": {"const": "action"},
            "action": {"const": "give_item"},
            "instance_id": {
                "type": "string",
                "description": "Item identifier from inventory to give"
            },
            "target_npc_id": {
                "type": "string",
                "description": "NPC identifier to receive the item"
            }
        },
        "examples": [{
            "type": "action",
            "action": "give_item",
            "instance_id": "dream_bottle_1",
            "target_npc_id": "louisa"
        }],
        "metadata": {
            "avg_response_time_ms": 5,
            "response_types": ["action_response"],
            "validation": [
                "Item must be in player inventory",
                "Player must be in same location/area as target",
                "NPC must exist (player-to-player transfer not yet implemented)"
            ]
        }
    },

    "update_location": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Update Location Command",
        "description": "Send GPS coordinates to receive nearby Area of Interest (AOI)",
        "type": "object",
        "required": ["type", "gps"],
        "properties": {
            "type": {"const": "update_location"},
            "gps": {
                "type": "object",
                "required": ["latitude", "longitude"],
                "properties": {
                    "latitude": {
                        "type": "number",
                        "minimum": -90,
                        "maximum": 90,
                        "description": "GPS latitude in decimal degrees"
                    },
                    "longitude": {
                        "type": "number",
                        "minimum": -180,
                        "maximum": 180,
                        "description": "GPS longitude in decimal degrees"
                    },
                    "accuracy": {
                        "type": "number",
                        "description": "GPS accuracy in meters (optional)"
                    }
                }
            }
        },
        "examples": [{
            "type": "update_location",
            "gps": {
                "latitude": 37.7749,
                "longitude": -122.4194,
                "accuracy": 10
            }
        }],
        "metadata": {
            "avg_response_time_ms": 15,
            "response_types": ["area_of_interest"]
        }
    },

    "ping": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Ping Command",
        "description": "Health check / connection keep-alive",
        "type": "object",
        "required": ["type"],
        "properties": {
            "type": {"const": "ping"},
            "timestamp": {
                "type": "integer",
                "description": "Client timestamp in milliseconds (optional)"
            }
        },
        "examples": [{
            "type": "ping",
            "timestamp": 1730678400000
        }],
        "metadata": {
            "avg_response_time_ms": 1,
            "response_types": ["pong"]
        }
    }
}


def get_command_schemas() -> Dict[str, Any]:
    """
    Get all command schemas for protocol introspection.

    Returns:
        Dict mapping command name to JSON Schema definition
    """
    return COMMAND_SCHEMAS


def get_commands_schema_response(timestamp: int) -> Dict[str, Any]:
    """
    Build complete commands_schema message for client.

    Args:
        timestamp: Current timestamp in milliseconds

    Returns:
        Complete commands_schema message ready to send to client
    """
    return {
        "type": "commands_schema",
        "timestamp": timestamp,
        "schema_version": "1.0",
        "commands": COMMAND_SCHEMAS
    }
