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
            elif message_type == "chat":
                await handle_chat(websocket, connection_id, user_id, experience, message)
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


async def handle_action(
    websocket: WebSocket,
    connection_id: str,
    user_id: str,
    experience: str,
    message: Dict[str, Any]
):
    """
    Handle action message from client.

    Actions include:
    - collect_bottle: Pick up a bottle from the world
    - drop_item: Drop an item from inventory
    - interact_object: Generic object interaction

    Args:
        websocket: WebSocket connection
        connection_id: Connection ID
        user_id: User ID
        experience: Experience ID
        message: Action message dict
    """
    action = message.get("action")

    if not action:
        await send_error(websocket, "missing_action", "Action message must have 'action' field")
        return

    logger.info(
        f"Processing action: connection_id={connection_id}, "
        f"action={action}, user_id={user_id}"
    )

    try:
        # Route to specific action handler
        if action == "collect_bottle":
            await handle_collect_bottle(websocket, user_id, experience, message)
        elif action == "drop_item":
            await handle_drop_item(websocket, user_id, experience, message)
        elif action == "interact_object":
            await handle_interact_object(websocket, user_id, experience, message)
        else:
            logger.warning(f"Unknown action: {action}")
            await send_error(websocket, "unknown_action", f"Unknown action: {action}")

    except Exception as e:
        logger.error(f"Action handler error (action={action}): {e}", exc_info=True)
        await send_error(websocket, "action_failed", str(e))


async def handle_collect_bottle(
    websocket: WebSocket,
    user_id: str,
    experience: str,
    message: Dict[str, Any]
):
    """
    Handle bottle collection action.

    Expected message format:
    {
        "type": "action",
        "action": "collect_bottle",
        "item_id": "bottle_of_joy_3",
        "spot_id": "woander_store.shelf_a.slot_1"
    }

    Response format:
    {
        "type": "action_response",
        "action": "collect_bottle",
        "success": true,
        "item_id": "bottle_of_joy_3"
    }

    Side effects:
    - UnifiedStateManager updates world state
    - NATS world_update event published automatically
    - Quest progress updated if applicable
    """
    item_id = message.get("item_id")
    spot_id = message.get("spot_id")

    if not item_id:
        await send_error(websocket, "missing_item_id", "collect_bottle requires 'item_id'")
        return

    logger.info(
        f"Collecting bottle: user_id={user_id}, item_id={item_id}, spot_id={spot_id}"
    )

    try:
        # Get state manager
        state_manager = kb_agent.state_manager
        if not state_manager:
            raise Exception("State manager not initialized")

        # Load current player view (auto-bootstraps on first access)
        player_view = await state_manager.get_player_view(experience, user_id)

        # Build state update: remove from world, add to inventory
        updates = {
            "player": {
                "inventory": {
                    "$append": {
                        "id": item_id,
                        "type": "collectible",
                        "collected_at": datetime.utcnow().isoformat() + "Z"
                    }
                }
            }
        }

        # Update player view (this triggers NATS publish automatically!)
        updated_view = await state_manager.update_player_view(
            experience=experience,
            user_id=user_id,
            updates=updates
        )

        # Send success response
        await websocket.send_json({
            "type": "action_response",
            "action": "collect_bottle",
            "success": True,
            "item_id": item_id,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        })

        # Check quest progress
        inventory = updated_view.get("player", {}).get("inventory", [])
        bottles_collected = sum(1 for item in inventory if item.get("type") == "collectible")

        # TODO: Get bottles_total from quest config
        bottles_total = 7  # Hardcoded for demo

        # Send quest update
        await websocket.send_json({
            "type": "quest_update",
            "quest_id": "bottle_quest",
            "status": "in_progress" if bottles_collected < bottles_total else "complete",
            "bottles_collected": bottles_collected,
            "bottles_total": bottles_total,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        })

        # Win condition
        if bottles_collected >= bottles_total:
            await websocket.send_json({
                "type": "quest_complete",
                "quest_id": "bottle_quest",
                "message": "Congratulations! You collected all the bottles!",
                "timestamp": int(datetime.utcnow().timestamp() * 1000)
            })

        logger.info(
            f"Bottle collected successfully: user_id={user_id}, "
            f"item_id={item_id}, bottles_collected={bottles_collected}/{bottles_total}"
        )

    except Exception as e:
        logger.error(f"Failed to collect bottle: {e}", exc_info=True)
        await send_error(websocket, "collection_failed", str(e))


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
