"""
WebSocket Endpoint for Real-Time Experience Interactions

FastAPI WebSocket endpoint for bidirectional communication with Unity clients.
Handles bottle collection, NPC interactions, and real-time world updates.

This is a SIMPLIFIED implementation for AEO-65 demo (Option C):
- Focus: Bottle quest functionality
- JWT authentication via query params
- Direct integration with UnifiedStateManager
- NATS-powered real-time updates

Author: GAIA Platform Team
Created: 2025-11-05 (AEO-65 Demo Implementation)
"""

# Trigger hot reload to pick up experience_connection_manager.py changes

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from datetime import datetime

from app.shared.security import get_current_user_ws
from app.services.kb.experience_connection_manager import ExperienceConnectionManager
from app.services.kb.kb_agent import kb_agent

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Global connection manager (initialized in main.py lifespan)
experience_manager: Optional[ExperienceConnectionManager] = None


def get_experience_manager() -> ExperienceConnectionManager:
    """Dependency to get experience manager."""
    if experience_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Experience manager not initialized"
        )
    return experience_manager


@router.websocket("/ws/experience")
async def websocket_experience_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    experience: str = Query(default="wylding-woods", description="Experience ID")
):
    """
    WebSocket endpoint for real-time experience interactions.

    Protocol:
    - Client sends actions: {"type": "action", "action": "collect_bottle", ...}
    - Server sends updates: {"type": "world_update", "version": "0.3", ...}
    - Server sends quest updates: {"type": "quest_update", ...}
    - Server sends NPC speech: {"type": "npc_speech", ...}

    Args:
        token: JWT token for authentication (in query params)
        experience: Experience ID (default: wylding-woods)

    Flow:
        1. Authenticate user via JWT
        2. Accept WebSocket connection
        3. Create persistent NATS subscription
        4. Enter message loop (handle client actions, forward NATS events)
        5. Clean up on disconnect
    """
    connection_id = None

    try:
        # Authenticate user
        auth = await get_current_user_ws(websocket, token)
        user_id = auth.get("user_id") or auth.get("sub")

        if not user_id:
            logger.error("WebSocket auth failed: no user_id in token")
            await websocket.close(code=1008, reason="Authentication failed")
            return

        logger.info(
            f"WebSocket authentication successful: user_id={user_id}, "
            f"experience={experience}"
        )

        # Connect WebSocket and set up NATS subscription
        connection_id = await experience_manager.connect(
            websocket=websocket,
            user_id=user_id,
            experience=experience
        )

        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "connection_id": connection_id,
            "user_id": user_id,
            "experience": experience,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            "message": f"Connected to {experience} experience"
        })

        # Enter message handling loop
        await handle_message_loop(websocket, connection_id, user_id, experience)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally: connection_id={connection_id}")
    except Exception as e:
        logger.error(
            f"WebSocket error (connection_id={connection_id}): {e}",
            exc_info=True
        )
        try:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")
        except:
            pass
    finally:
        # Clean up connection
        if connection_id and experience_manager:
            await experience_manager.disconnect(connection_id)


async def handle_message_loop(
    websocket: WebSocket,
    connection_id: str,
    user_id: str,
    experience: str
):
    """
    Main message handling loop for WebSocket connection.

    Receives client messages and dispatches to appropriate handlers.

    Args:
        websocket: WebSocket connection
        connection_id: Connection ID
        user_id: Authenticated user ID
        experience: Experience ID
    """
    while True:
        try:
            # Receive message from client
            raw_message = await websocket.receive_text()

            # Update metrics
            if connection_id in experience_manager.connection_metadata:
                experience_manager.connection_metadata[connection_id]["messages_received"] += 1

            # Parse message
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from client: {e}")
                await send_error(websocket, "invalid_json", "Message must be valid JSON")
                continue

            # Extract message type
            message_type = message.get("type")

            if not message_type:
                logger.warning(f"Message missing 'type' field: {message}")
                await send_error(websocket, "missing_type", "Message must have 'type' field")
                continue

            logger.debug(
                f"Received message: connection_id={connection_id}, "
                f"type={message_type}"
            )

            # Route message to handler
            if message_type == "action":
                await handle_action(websocket, connection_id, user_id, experience, message)
            elif message_type == "ping":
                await handle_ping(websocket, connection_id, message)
            elif message_type == "get_commands":
                await handle_get_commands(websocket, connection_id)
            elif message_type == "chat":
                await handle_chat(websocket, connection_id, user_id, experience, message)
            elif message_type == "update_location":
                await handle_update_location(websocket, connection_id, user_id, experience, message)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await send_error(
                    websocket,
                    "unknown_message_type",
                    f"Unknown message type: {message_type}"
                )

        except WebSocketDisconnect:
            # Normal disconnection
            raise
        except Exception as e:
            logger.error(
                f"Error handling message (connection_id={connection_id}): {e}",
                exc_info=True
            )
            await send_error(websocket, "processing_error", str(e))


from app.services.kb.command_processor import command_processor
import time
import uuid


async def handle_action(
    websocket: WebSocket,
    connection_id: str,
    user_id: str,
    experience: str,
    message: Dict[str, Any]
):
    """
    Handle action message from client by passing it to the central command processor.
    """
    t0 = time.perf_counter()
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    
    action = message.get("action")
    if not action:
        await send_error(websocket, "missing_action", "Action message must have 'action' field")
        return

    logger.info(json.dumps({
        "event": "timing_analysis",
        "request_id": request_id,
        "stage": "action_received",
        "action": action,
        "user_id": user_id,
        "elapsed_ms": 0.0
    }))

    # Ensure player is initialized before processing any command
    try:
        state_manager = kb_agent.state_manager
        if not state_manager:
            raise Exception("State manager not initialized")
        await state_manager.ensure_player_initialized(experience, user_id)
    except Exception as e:
        logger.error(f"Failed to ensure player is initialized: {e}", exc_info=True)
        await send_error(websocket, "initialization_failed", str(e))
        return

    # Add request_id to the command data for downstream logging
    message["request_id"] = request_id

    # Process the command through the central processor
    result = await command_processor.process_command(user_id, experience, message, connection_id)

    # Send a response back to the client based on the result
    response_message = {
        "type": "action_response",
        "action": action,
        "success": result.success,
        "message": result.message_to_player,
        "timestamp": int(datetime.utcnow().timestamp() * 1000)
    }
    if result.metadata:
        response_message["metadata"] = result.metadata

        # Unity expects item_id at root level for visual feedback triggering
        # Extract from metadata.instance_id for collect_item, give_item, drop_item commands
        if "instance_id" in result.metadata:
            response_message["item_id"] = result.metadata["instance_id"]

    total_elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(json.dumps({
        "event": "timing_analysis",
        "request_id": request_id,
        "stage": "response_sent",
        "action": action,
        "user_id": user_id,
        "elapsed_ms": total_elapsed_ms
    }))

    await websocket.send_json(response_message)

    # TODO: This is temporary for the demo. Quest logic should be a proper command.
    if result.success and action == "collect_item":
        try:
            state_manager = kb_agent.state_manager
            updated_view = await state_manager.get_player_view(experience, user_id)
            inventory = updated_view.get("player", {}).get("inventory", [])
            bottles_collected = sum(1 for item in inventory if item.get("type") == "collectible")
            bottles_total = 7  # Hardcoded for demo

            await websocket.send_json({
                "type": "quest_update",
                "quest_id": "bottle_quest",
                "status": "in_progress" if bottles_collected < bottles_total else "complete",
                "bottles_collected": bottles_collected,
                "bottles_total": bottles_total,
                "timestamp": int(datetime.utcnow().timestamp() * 1000)
            })

            if bottles_collected >= bottles_total:
                await websocket.send_json({
                    "type": "quest_complete",
                    "quest_id": "bottle_quest",
                    "message": "Congratulations! You collected all the bottles!",
                    "timestamp": int(datetime.utcnow().timestamp() * 1000)
                })
        except Exception as e:
            logger.error(f"Error processing quest update after collect_item: {e}", exc_info=True)



async def handle_drop_item(
    websocket: WebSocket,
    user_id: str,
    experience: str,
    message: Dict[str, Any]
):
    """Handle drop item action (placeholder for demo)."""
    await send_error(websocket, "not_implemented", "drop_item not yet implemented")


async def handle_interact_object(
    websocket: WebSocket,
    user_id: str,
    experience: str,
    message: Dict[str, Any]
):
    """Handle generic object interaction (placeholder for demo)."""
    await send_error(websocket, "not_implemented", "interact_object not yet implemented")


async def handle_ping(
    websocket: WebSocket,
    connection_id: str,
    message: Dict[str, Any]
):
    """
    Handle ping message (connection health check).

    Request: {"type": "ping", "timestamp": 1234567890}
    Response: {"type": "pong", "timestamp": 1234567890}
    """
    await websocket.send_json({
        "type": "pong",
        "timestamp": message.get("timestamp", int(datetime.utcnow().timestamp() * 1000))
    })


async def handle_get_commands(
    websocket: WebSocket,
    connection_id: str
):
    """
    Handle get_commands message (protocol introspection).

    Returns JSON Schema definitions for all available commands, enabling
    self-documenting API and dynamic client capabilities.

    Design inspired by GraphQL introspection (__schema, __type queries)
    and gRPC reflection service, adapted for WebSocket real-time protocols.

    Request: {"type": "get_commands"}
    Response: {"type": "commands_schema", "commands": {...}}

    Performance: <5ms (cached schema)
    """
    from app.services.kb.command_registry import get_commands_schema_response

    timestamp = int(datetime.utcnow().timestamp() * 1000)
    response = get_commands_schema_response(timestamp)

    logger.debug(
        f"Sending commands schema (connection_id={connection_id}, "
        f"num_commands={len(response['commands'])})"
    )

    await websocket.send_json(response)


async def handle_chat(
    websocket: WebSocket,
    connection_id: str,
    user_id: str,
    experience: str,
    message: Dict[str, Any]
):
    """
    Handle chat message (for NPC interactions).

    This is a placeholder - full chat integration would route through
    the Chat Service for LLM processing.

    For demo: Send canned NPC responses.
    """
    text = message.get("text", "")

    logger.info(f"Chat message: user_id={user_id}, text={text}")

    # Demo: Canned fairy response
    await websocket.send_json({
        "type": "npc_speech",
        "npc_id": "fairy_guide",
        "text": "Keep collecting those bottles! You're doing great!",
        "voice": "cheerful",
        "timestamp": int(datetime.utcnow().timestamp() * 1000)
    })


async def handle_update_location(
    websocket: WebSocket,
    connection_id: str,
    user_id: str,
    experience: str,
    message: Dict[str, Any]
):
    """
    Handle location update from client.

    Client sends GPS coordinates, server responds with Area of Interest (AOI)
    containing zone data, items, NPCs, and player state for that location.

    Args:
        websocket: WebSocket connection
        connection_id: Connection ID
        user_id: Authenticated user ID
        experience: Experience ID
        message: Message containing lat/lng coordinates
    """
    # Extract GPS coordinates
    lat = message.get("lat")
    lng = message.get("lng")

    if lat is None or lng is None:
        await send_error(websocket, "missing_coordinates", "GPS coordinates required (lat, lng)")
        return

    logger.info(f"Location update: user_id={user_id}, lat={lat}, lng={lng}")

    # Find nearby locations
    from app.services.locations.location_finder import find_nearby_locations

    nearby_waypoints = await find_nearby_locations(
        lat=lat,
        lng=lng,
        radius_m=1000,  # 1km search radius
        experience=experience
    )

    # Get state manager
    state_manager = kb_agent.state_manager
    if not state_manager:
        await send_error(websocket, "server_error", "State manager not initialized")
        return

    # Build AOI
    aoi = await state_manager.build_aoi(
        experience=experience,
        user_id=user_id,
        nearby_waypoints=nearby_waypoints
    )

    if aoi:
        # SERVER IS AUTHORITATIVE: Update player's location based on GPS
        zone_id = aoi['zone']['id']

        # Set current_area to first area in zone (required for proper state updates)
        # Areas are needed for collection/drop handlers to build correct nested paths
        areas = aoi.get('areas', {})
        current_area = list(areas.keys())[0] if areas else None

        # Check if player changed zones (optimization: only send AOI on zone change)
        player_view = await state_manager.get_player_view(experience, user_id)
        previous_zone = player_view.get("player", {}).get("current_location")
        zone_changed = (previous_zone != zone_id)

        # Update player state with server-authoritative location
        logger.warning(f"[GPS-DEBUG] About to update player location: zone={zone_id}, area={current_area}")
        await state_manager.update_player_view(
            experience=experience,
            user_id=user_id,
            updates={
                "player": {
                    "current_location": zone_id,
                    "current_area": current_area,
                    "last_gps_update": int(datetime.utcnow().timestamp() * 1000)
                }
            }
        )
        logger.warning(f"[GPS-DEBUG] Player location updated successfully")

        logger.warning(f"[GPS-DEBUG] Checking zone change: previous={previous_zone}, current={zone_id}, changed={zone_changed}")

        # TEMPORARY: Always send AOI (zone change optimization removed for now)
        # TODO: Re-add optimization with proper "first GPS after connection" tracking
        logger.info(
            f"Sending AOI to user {user_id}: zone={zone_id}, "
            f"previous_zone={previous_zone}"
        )

        # Send AOI to client
        await websocket.send_json({
            "type": "area_of_interest",
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            **aoi
        })

        logger.info(
            f"Sent AOI to user {user_id}: zone={aoi['zone']['id']}, "
            f"areas={len(aoi['areas'])}"
        )

        # NOTE: Client version is initialized on connection (experience_connection_manager.py:135)
        # DO NOT update it here - that would overwrite delta tracking and invalidate buffered deltas!
        # Client version is only updated after successful delta application (update_world_state)
    else:
        # No locations nearby - send empty response (industry standard)
        await websocket.send_json({
            "type": "area_of_interest",
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            "snapshot_version": int(datetime.utcnow().timestamp() * 1000),
            "zone": None,
            "areas": {},
            "player": {
                "current_location": None,
                "current_area": None,
                "inventory": []
            }
        })
        logger.info(f"Sent empty AOI to user {user_id} (no waypoints nearby)")


async def send_error(
    websocket: WebSocket,
    error_code: str,
    error_message: str
):
    """
    Send error message to client.

    Format: {"type": "error", "code": "...", "message": "..."}
    """
    try:
        await websocket.send_json({
            "type": "error",
            "code": error_code,
            "message": error_message,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        })
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")
