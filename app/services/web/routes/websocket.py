"""WebSocket routes for real-time chat"""
import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from app.services.web.config import settings
from app.shared.logging import setup_service_logger
from app.shared.nats_client import get_nats_client

logger = setup_service_logger("websocket_routes")


def setup_routes(app):
    """Setup WebSocket routes"""
    
    @app.websocket("/ws/chat/{conversation_id}")
    async def chat_websocket(websocket: WebSocket, conversation_id: str):
        """WebSocket endpoint for real-time chat updates"""
        await websocket.accept()
        logger.info(f"WebSocket connected for conversation {conversation_id}")
        
        # Get NATS client if enabled
        nats_client = None
        subscription = None
        
        try:
            if settings.nats_url and settings.nats_url != "disabled":
                nats_client = await get_nats_client()
                
                # Subscribe to conversation-specific events
                async def message_handler(msg):
                    try:
                        data = json.loads(msg.data.decode())
                        await websocket.send_json({
                            "type": "message",
                            "data": data
                        })
                    except Exception as e:
                        logger.error(f"Error handling NATS message: {e}")
                
                subscription = await nats_client.subscribe(
                    f"gaia.chat.{conversation_id}.*",
                    cb=message_handler
                )
            
            # Keep connection alive
            while True:
                try:
                    # Receive messages from client
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Handle different message types
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif message.get("type") == "typing":
                        # Broadcast typing indicator via NATS
                        if nats_client:
                            await nats_client.publish(
                                f"gaia.chat.{conversation_id}.typing",
                                json.dumps({
                                    "user": message.get("user"),
                                    "typing": message.get("typing", True)
                                }).encode()
                            )
                    
                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received from WebSocket")
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    break
                
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            # Cleanup
            if subscription:
                await subscription.unsubscribe()
            
            logger.info(f"WebSocket disconnected for conversation {conversation_id}")
    
    @app.websocket("/ws/notifications")
    async def notifications_websocket(websocket: WebSocket):
        """WebSocket for global notifications"""
        await websocket.accept()
        logger.info("Notifications WebSocket connected")
        
        # Get NATS client if enabled
        nats_client = None
        subscription = None
        
        try:
            if settings.nats_url and settings.nats_url != "disabled":
                nats_client = await get_nats_client()
                
                # Subscribe to user-specific notifications
                async def notification_handler(msg):
                    try:
                        data = json.loads(msg.data.decode())
                        await websocket.send_json({
                            "type": "notification",
                            "data": data
                        })
                    except Exception as e:
                        logger.error(f"Error handling notification: {e}")
                
                # TODO: Subscribe to user-specific channel based on JWT
                subscription = await nats_client.subscribe(
                    "gaia.notifications.*",
                    cb=notification_handler
                )
            
            # Keep connection alive
            while True:
                try:
                    # Simple ping/pong to keep alive
                    await asyncio.sleep(30)
                    await websocket.send_json({"type": "ping"})
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Notification WebSocket error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Notification WebSocket error: {e}")
        finally:
            # Cleanup
            if subscription:
                await subscription.unsubscribe()
            
            logger.info("Notifications WebSocket disconnected")