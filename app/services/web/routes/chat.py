"""Chat interface routes"""
import json
from datetime import datetime
from fasthtml.components import Div, H2
from app.services.web.components.gaia_ui import (
    gaia_layout, gaia_conversation_item, gaia_message_bubble,
    gaia_chat_input, gaia_loading_spinner, gaia_error_message
)
from app.services.web.utils.gateway_client import gateway_client
from app.shared.logging import setup_service_logger

logger = setup_service_logger("chat_routes")


def setup_routes(app):
    """Setup chat routes"""
    
    @app.get("/chat")
    async def chat_index(request):
        """Main chat interface"""
        jwt_token = request.session.get("jwt_token")
        
        # Get user's conversations
        conversations = await gateway_client.get_conversations(jwt_token)
        
        # Build sidebar content
        sidebar_content = Div(
            *[gaia_conversation_item(conv) for conv in conversations],
            cls="space-y-2"
        )
        
        # Main content - empty chat area
        main_content = Div(
            Div(
                H2("Select a conversation or start a new one", 
                   cls="text-xl text-slate-400 text-center"),
                cls="flex-1 flex items-center justify-center"
            ),
            gaia_chat_input(),
            cls="flex flex-col h-full"
        )
        
        return gaia_layout(
            sidebar_content=sidebar_content,
            main_content=main_content
        )
    
    @app.get("/chat/{conversation_id}")
    async def chat_conversation(request, conversation_id: str):
        """Load specific conversation"""
        jwt_token = request.session.get("jwt_token")
        
        try:
            # Get conversation with messages
            conversation = await gateway_client.get_conversation(conversation_id, jwt_token)
            
            # Build message list
            messages = Div(
                *[
                    gaia_message_bubble(
                        msg["content"],
                        role=msg["role"],
                        timestamp=msg.get("created_at", "")
                    )
                    for msg in conversation.get("messages", [])
                ],
                id="messages",
                cls="flex-1 overflow-y-auto p-6 space-y-4"
            )
            
            # Return chat area
            return Div(
                messages,
                gaia_chat_input(),
                cls="flex flex-col h-full",
                data_conversation_id=conversation_id
            )
            
        except Exception as e:
            logger.error(f"Error loading conversation: {e}")
            return gaia_error_message("Failed to load conversation")
    
    @app.post("/chat/new")
    async def new_chat(request):
        """Create new conversation"""
        jwt_token = request.session.get("jwt_token")
        
        try:
            # Create new conversation
            conversation = await gateway_client.create_conversation(jwt_token)
            
            # Return empty chat area with new conversation ID
            return Div(
                Div(
                    id="messages",
                    cls="flex-1 overflow-y-auto p-6 space-y-4"
                ),
                gaia_chat_input(),
                cls="flex flex-col h-full",
                data_conversation_id=conversation["id"]
            )
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return gaia_error_message("Failed to create conversation")
    
    @app.post("/api/chat/send")
    async def send_message(request):
        """Send chat message"""
        jwt_token = request.session.get("jwt_token")
        form_data = await request.form()
        message = form_data.get("message")
        
        # Get conversation ID from referrer or create new
        conversation_id = request.headers.get("X-Conversation-Id")
        
        if not conversation_id:
            # Create new conversation if needed
            try:
                conversation = await gateway_client.create_conversation(jwt_token)
                conversation_id = conversation["id"]
            except Exception as e:
                logger.error(f"Error creating conversation: {e}")
                return gaia_error_message("Failed to send message")
        
        # Add user message to UI immediately
        user_message = gaia_message_bubble(
            message,
            role="user",
            timestamp=datetime.now().strftime("%I:%M %p")
        )
        
        # Add loading indicator
        loading = Div(
            gaia_loading_spinner(),
            id=f"loading-{conversation_id}",
            cls="assistant-message-placeholder"
        )
        
        # Return user message + loading indicator
        # The actual response will come via WebSocket
        return Div(
            user_message,
            loading,
            hx_trigger="load",
            hx_get=f"/api/chat/stream/{conversation_id}?message={message}",
            hx_target=f"#loading-{conversation_id}",
            hx_swap="outerHTML"
        )
    
    @app.get("/api/chat/stream/{conversation_id}")
    async def stream_response(request, conversation_id: str):
        """Stream chat response"""
        jwt_token = request.session.get("jwt_token")
        message = request.query_params.get("message")
        
        try:
            # Prepare messages for API call
            messages = [{"role": "user", "content": message}]
            
            # Start streaming response
            response_content = ""
            async for chunk in gateway_client.chat_completion_stream(messages, jwt_token):
                if chunk == "[DONE]":
                    break
                
                try:
                    data = json.loads(chunk)
                    if "choices" in data and data["choices"]:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            response_content += delta["content"]
                except json.JSONDecodeError:
                    continue
            
            # Return complete assistant message
            return gaia_message_bubble(
                response_content,
                role="assistant",
                timestamp=datetime.now().strftime("%I:%M %p")
            )
            
        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            return gaia_error_message("Failed to get response")