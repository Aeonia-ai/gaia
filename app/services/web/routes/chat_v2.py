"""
Chat route v2 - Uses unified chat endpoint with conversation persistence.
This is a simplified version that relies on the chat service for all conversation management.
"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from app.services.web.utils.gateway_client import GaiaAPIClient
from app.services.web.utils.chat_service_client import ChatServiceClient
from app.services.web.components.gaia_ui import (
    gaia_message_bubble, gaia_error_message, gaia_chat_input
)
from app.shared.logging import setup_service_logger

logger = setup_service_logger("chat_v2")

# We'll still use chat service client for retrieving conversation history
chat_service_client = ChatServiceClient()


def setup_chat_v2_routes(app):
    """Setup v2 chat routes that use unified endpoint"""
    
    @app.post("/api/chat/v2/send")
    async def send_message_v2(request):
        """Send chat message using unified endpoint with conversation persistence"""
        logger.info("Chat v2 send endpoint called")
        
        try:
            # Check authentication
            jwt_token = request.session.get("jwt_token")
            user = request.session.get("user")
            
            if not user or not jwt_token:
                return gaia_error_message("Please log in to send messages")
            
            user_id = user.get("id", "dev-user-id")
            
            form_data = await request.form()
            message = form_data.get("message")
            conversation_id = form_data.get("conversation_id")
            
            logger.info(f"Received message: {message}, conversation: {conversation_id}")
            
            if not message:
                return gaia_error_message("Please enter a message")
            
            # Generate a message ID for UI updates
            import uuid
            message_id = str(uuid.uuid4())[:8]
            
            # Add user message to UI immediately
            user_message = gaia_message_bubble(
                message,
                role="user",
                timestamp=datetime.now().strftime("%I:%M %p")
            )
            
            # URL encode for SSE endpoint
            from urllib.parse import quote
            encoded_message = quote(message, safe='')
            
            # Build response HTML that uses v2 streaming
            response_html = f'''{str(user_message)}
<div id="loading-{message_id}" class="flex justify-start mb-4">
    <div class="bg-slate-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
        <div class="text-xs opacity-70 mt-2">Gaia is thinking...</div>
    </div>
</div>
<script>
(function() {{
    const welcome = document.getElementById('welcome-message');
    if (welcome) {{
        welcome.style.display = 'none';
    }}
    
    let responseContent = '';
    let responseStarted = false;
    let receivedConversationId = '{conversation_id or ""}';
    
    // Use v2 streaming endpoint
    const eventSource = new EventSource('/api/chat/v2/stream?message={encoded_message}&conversation_id={conversation_id or ""}');
    
    const timeoutId = setTimeout(() => {{
        if (!responseStarted) {{
            const loadingEl = document.getElementById('loading-{message_id}');
            if (loadingEl && loadingEl.parentNode) {{
                loadingEl.outerHTML = `<div class="flex justify-start mb-4">
                    <div class="bg-yellow-900/50 border border-yellow-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
                        <div class="flex items-center">
                            <span class="mr-2">⚠️</span>
                            <span>Response is taking longer than expected...</span>
                        </div>
                    </div>
                </div>`;
                eventSource.close();
            }}
        }}
    }}, 30000);
    
    eventSource.onmessage = function(event) {{
        if (event.data === '[DONE]') {{
            eventSource.close();
            clearTimeout(timeoutId);
            
            // Update conversation ID if we got a new one
            if (receivedConversationId && !'{conversation_id or ""}') {{
                const convInput = document.getElementById('conversation-id-input');
                if (convInput) {{
                    convInput.value = receivedConversationId;
                }}
                
                // Update browser URL
                history.pushState(null, '', '/chat/' + receivedConversationId);
            }}
            
            // Update conversation list
            htmx.ajax('GET', '/api/conversations', {{target: '#conversation-list', swap: 'innerHTML'}});
            
            if (window.GaiaToast) {{
                GaiaToast.success('Response received!', 2000);
            }}
            return;
        }}
        
        try {{
            const data = JSON.parse(event.data);
            
            if (data.conversation_id && !receivedConversationId) {{
                receivedConversationId = data.conversation_id;
            }}
            
            if (data.type === 'content' && data.content) {{
                if (!responseStarted) {{
                    responseStarted = true;
                    clearTimeout(timeoutId);
                    const loadingEl = document.getElementById('loading-{message_id}');
                    if (loadingEl) {{
                        loadingEl.outerHTML = `<div class="flex justify-start mb-4 assistant-message">
                            <div class="bg-slate-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg hover:shadow-xl transition-all duration-300">
                                <div class="message-content whitespace-pre-wrap" id="response-{message_id}"></div>
                                <div class="text-xs text-slate-400 mt-2">${{new Date().toLocaleTimeString('en-US', {{hour: 'numeric', minute: '2-digit', hour12: true}})}}</div>
                            </div>
                        </div>`;
                    }}
                }}
                
                responseContent += data.content;
                const responseEl = document.getElementById('response-{message_id}');
                if (responseEl) {{
                    responseEl.textContent = responseContent;
                }}
            }} else if (data.type === 'error') {{
                const loadingEl = document.getElementById('loading-{message_id}');
                if (loadingEl) {{
                    loadingEl.outerHTML = `<div class="flex justify-start mb-4">
                        <div class="bg-red-900/50 border border-red-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
                            <div class="flex items-center">
                                <span class="mr-2">❌</span>
                                <span>${{data.error || 'An error occurred'}}</span>
                            </div>
                        </div>
                    </div>`;
                }}
                eventSource.close();
                clearTimeout(timeoutId);
            }}
        }} catch (e) {{
            console.error('Failed to parse SSE data:', e);
        }}
    }};
    
    eventSource.onerror = function(error) {{
        console.error('EventSource error:', error);
        const loadingEl = document.getElementById('loading-{message_id}');
        if (loadingEl) {{
            loadingEl.outerHTML = `<div class="flex justify-start mb-4">
                <div class="bg-red-900/50 border border-red-700 text-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-lg">
                    <div class="flex items-center">
                        <span class="mr-2">❌</span>
                        <span>Connection error. Please try again.</span>
                    </div>
                </div>
            </div>`;
        }}
        eventSource.close();
        clearTimeout(timeoutId);
    }};
}})();
</script>'''
            
            # Return HTML immediately
            return response_html
            
        except Exception as e:
            logger.error(f"Error in send_message_v2: {e}", exc_info=True)
            return gaia_error_message(f"Failed to send message: {str(e)}")
    
    @app.get("/api/chat/v2/stream")
    async def stream_response_v2(request):
        """Stream chat response using unified endpoint with v0.3 format"""
        from starlette.responses import StreamingResponse
        
        jwt_token = request.session.get("jwt_token")
        user = request.session.get("user", {})
        
        message = request.query_params.get("message")
        conversation_id = request.query_params.get("conversation_id")
        
        # Don't pass empty string conversation_id
        if conversation_id == "":
            conversation_id = None
        
        logger.info(f"Stream v2 - message: {message}, conv: {conversation_id}")
        
        async def event_generator():
            try:
                # For simplicity, just send the current message
                # The unified endpoint will handle conversation history
                messages = [{"role": "user", "content": message}]
                
                # Track if we've sent the conversation_id
                sent_conversation_id = False
                
                # Start streaming from gateway with v0.3 format
                async with GaiaAPIClient() as client:
                    # First, make a non-streaming call to get conversation_id if we don't have one
                    if not conversation_id:
                        try:
                            response = await client.chat_completion(
                                messages=messages,
                                jwt_token=jwt_token,
                                conversation_id=conversation_id,
                                response_format="v0.3"
                            )
                            
                            # Extract conversation_id from response
                            new_conversation_id = response.get("conversation_id")
                            if new_conversation_id:
                                # Send conversation_id to client
                                yield f"data: {json.dumps({'conversation_id': new_conversation_id})}\n\n"
                                sent_conversation_id = True
                                
                                # Now stream with the conversation_id
                                async for chunk in client.chat_completion_stream(
                                    messages=messages,
                                    jwt_token=jwt_token,
                                    conversation_id=new_conversation_id,
                                    response_format="v0.3"
                                ):
                                    if chunk.strip() == "[DONE]":
                                        yield f"data: [DONE]\n\n"
                                        break
                                    
                                    try:
                                        chunk_data = json.loads(chunk)
                                        # Pass through content chunks
                                        if chunk_data.get("type") == "content":
                                            yield f"data: {chunk}\n\n"
                                        elif chunk_data.get("error"):
                                            yield f"data: {json.dumps({'type': 'error', 'error': chunk_data.get('error')})}\n\n"
                                    except json.JSONDecodeError:
                                        logger.error(f"Failed to parse chunk: {chunk}")
                                        continue
                                        
                        except Exception as e:
                            logger.error(f"Non-streaming call failed: {e}")
                            # Fall back to regular streaming
                            pass
                    
                    # If we already have conversation_id or fallback streaming
                    if conversation_id or not sent_conversation_id:
                        async for chunk in client.chat_completion_stream(
                            messages=messages,
                            jwt_token=jwt_token,
                            conversation_id=conversation_id,
                            response_format="v0.3"
                        ):
                            if chunk.strip() == "[DONE]":
                                yield f"data: [DONE]\n\n"
                                break
                            
                            try:
                                chunk_data = json.loads(chunk)
                                
                                # Handle streaming chunks
                                if chunk_data.get("type") == "content":
                                    yield f"data: {chunk}\n\n"
                                elif chunk_data.get("error"):
                                    yield f"data: {json.dumps({'type': 'error', 'error': chunk_data.get('error')})}\n\n"
                                
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse chunk: {chunk}")
                                continue
                    
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )