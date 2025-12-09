# Unified Intelligent Chat Specification

> **Status**: ✅ IMPLEMENTED - See `app/services/chat/unified_chat.py`
> **Created**: January 2025
> **Purpose**: Define a single, intelligent chat endpoint that uses LLM tool-calling for routing decisions
> **Implementation**: `app/services/chat/unified_chat.py:UnifiedChatHandler`
> **Last Updated**: 2025-12-04

## Implementation Status

**✅ This specification has been implemented** in `app/services/chat/unified_chat.py`.

**Key Implementation Points:**
- Single `UnifiedChatHandler` class consolidates all routing logic
- LLM uses `tool_choice="auto"` to decide between direct response and tool routing
- KB tools (`KB_TOOLS`) integrated directly into unified handler
- Routing tools for MCP agent and multiagent orchestration
- Services called directly (not via HTTP forwarding)

**Verified Components:**
- `app/services/chat/unified_chat.py` lines 271-331: Core routing logic
- Routing tools: `use_kb_tools`, `route_to_mcp_agent` (actual names may vary)
- KB tools integration working
- Direct response path operational

**Differences from Spec:**
- Implementation calls services directly, not via HTTP endpoints
- Some tool names/signatures may differ from this spec
- Actual code is more evolved than this initial specification

## Overview (As Designed)

Replace multiple chat endpoints (`/chat/direct`, `/chat/mcp-agent-hot`, `/chat/intelligent`, etc.) with a single unified endpoint that lets the LLM decide whether to:
1. Respond directly (no tools)
2. Route to MCP agent (for tool use)
3. Route to multi-agent orchestration (for complex analysis)

**Note**: This design has been implemented. See code for actual implementation details.

## Core Design Principle

**The LLM is the router** - Using native LLM tool-calling capabilities, not separate classification steps or pattern matching.

## Implementation

### Single Endpoint

```python
@app.post("/api/v1/chat")
async def unified_chat(
    request: ChatRequest,
    auth: dict = Depends(get_current_auth)
):
    """
    Unified intelligent chat endpoint.
    The LLM decides whether to respond directly or use specialized tools.
    """
    return await unified_chat_handler.process(request.message, auth)
```

### Unified Chat Handler

```python
class UnifiedChatHandler:
    """
    Handles all chat requests with intelligent routing via LLM tool-calling.
    """
    
    def __init__(self):
        # Pre-initialized services (hot-loaded)
        self.mcp_hot_service = hot_chat_service  # Already initialized at startup
        self.multiagent_orchestrator = multiagent_orchestrator  # Already initialized
        self.llm_client = get_llm_client()  # Direct LLM client for routing
        
        # Routing tools definition
        self.routing_tools = [
            {
                "name": "use_mcp_agent",
                "description": "Use this when the user's request requires external tools such as: reading/writing files, web search, API calls, calculations, system operations, or any interaction beyond conversation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": "Brief explanation of why MCP agent is needed"
                        }
                    },
                    "required": ["reasoning"]
                }
            },
            {
                "name": "use_multiagent_orchestration",
                "description": "Use this for complex requests that require multiple expert perspectives, cross-domain analysis, or coordinated reasoning across different specialties (technical, business, creative, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of domains needed (e.g., ['technical', 'business', 'creative'])"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Why multiple agents are needed"
                        }
                    },
                    "required": ["domains", "reasoning"]
                }
            }
        ]
    
    async def process(self, message: str, auth: dict) -> dict:
        """
        Process message with intelligent routing.
        
        Returns a standardized response format regardless of routing path.
        """
        start_time = time.time()
        
        # Build context (user info, conversation history, etc.)
        context = await self.build_context(auth)
        
        # Single LLM call for routing decision
        routing_response = await self.llm_client.chat(
            messages=[
                {
                    "role": "system", 
                    "content": self.get_routing_prompt(context)
                },
                {
                    "role": "user", 
                    "content": message
                }
            ],
            tools=self.routing_tools,
            tool_choice="auto",  # LLM decides: direct response or tool use
            model="claude-sonnet-4-5",  # Fast, smart model for routing
            max_tokens=4096
        )
        
        # Process based on LLM decision
        if routing_response.tool_calls:
            # LLM decided to use a specialized handler
            tool_call = routing_response.tool_calls[0]
            
            if tool_call.name == "use_mcp_agent":
                # Route to MCP agent for tool use
                result = await self.mcp_hot_service.process(
                    message=message,
                    context=context,
                    reasoning=tool_call.arguments.get("reasoning")
                )
                return self.format_response(result, "mcp_agent", start_time)
                
            elif tool_call.name == "use_multiagent_orchestration":
                # Route to multi-agent system
                result = await self.multiagent_orchestrator.process(
                    message=message,
                    context=context,
                    domains=tool_call.arguments.get("domains", []),
                    reasoning=tool_call.arguments.get("reasoning")
                )
                return self.format_response(result, "multiagent", start_time)
        
        else:
            # Direct response - no specialized tools needed
            return self.format_response(
                {
                    "content": routing_response.content,
                    "model": "claude-sonnet-4-5"
                },
                "direct",
                start_time
            )
    
    def get_routing_prompt(self, context: dict) -> str:
        """
        System prompt that helps LLM make routing decisions.
        """
        return f"""You are an intelligent assistant that can either respond directly or use specialized tools when needed.

Current context:
- User: {context.get('user_id')}
- Conversation: {context.get('conversation_id')}
- Message count: {context.get('message_count', 0)}

Respond directly for:
- Greetings, casual conversation
- Simple questions with straightforward answers
- Clarifications or follow-ups to previous messages
- General knowledge queries

Use tools only when the request explicitly requires:
- File operations or code analysis (use_mcp_agent)
- Web searches or API calls (use_mcp_agent)
- Complex multi-domain analysis (use_multiagent_orchestration)
- Coordinated expert reasoning (use_multiagent_orchestration)

When in doubt, prefer direct responses. Tools add latency and should only be used when truly beneficial."""
    
    def format_response(self, result: dict, route_type: str, start_time: float) -> dict:
        """
        Standardize response format across all routing paths.
        """
        execution_time = time.time() - start_time
        
        return {
            "id": f"chat-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": result.get("model", "gaia-unified"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.get("content", result.get("response", ""))
                },
                "finish_reason": "stop"
            }],
            "usage": result.get("usage", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }),
            "_metadata": {
                "route_type": route_type,
                "execution_time_ms": int(execution_time * 1000),
                "reasoning": result.get("reasoning"),
                "tools_used": result.get("tools_used", []),
                "domains": result.get("domains", [])
            }
        }
```

## Benefits

### 1. **Simplicity**
- One endpoint to maintain
- No pattern matching or classification code
- LLM's native intelligence makes decisions

### 2. **Performance**
- Simple messages: ~1-2s (direct response)
- Tool-needed messages: ~2-4s (MCP agent)
- Complex messages: ~4-8s (multi-agent)

### 3. **User Experience**
- Consistent API interface
- Transparent routing (via metadata)
- Natural conversation flow

### 4. **Extensibility**
- Easy to add new routing tools
- Can enhance routing prompt with user preferences
- Can add new specialized handlers

## Migration Path

### Phase 1: Implement Unified Handler
```python
# Add to app/services/chat/unified_chat.py
class UnifiedChatHandler:
    # Implementation as above
```

### Phase 2: Add New Endpoint
```python
# Add to app/services/chat/chat.py
@router.post("/unified")
async def unified_chat_endpoint(request: ChatRequest, auth = Depends(get_current_auth)):
    return await unified_chat_handler.process(request.message, auth)
```

### Phase 3: Test & Validate
- Compare responses with existing endpoints
- Measure routing accuracy
- Performance benchmarking

### Phase 4: Gradual Migration
- Update clients to use new endpoint
- Monitor usage patterns
- Deprecate old endpoints

## Example Interactions

### Simple Direct Response
```
User: "Hello, how are you today?"
LLM: [No tool calls, responds directly]
Response: "Hello! I'm doing well, thank you for asking. How can I help you today?"
Route: direct (1.2s)
```

### MCP Agent Required
```
User: "What's in my README.md file?"
LLM: [Calls use_mcp_agent tool]
Response: "I'll check your README.md file for you... [file contents]"
Route: mcp_agent (2.8s)
```

### Multi-Agent Orchestration
```
User: "Analyze the technical architecture and business implications of migrating to microservices"
LLM: [Calls use_multiagent_orchestration with domains=['technical', 'business']]
Response: "I'll analyze this from both technical and business perspectives... [comprehensive analysis]"
Route: multiagent (6.5s)
```

## Configuration

```python
# Environment variables
UNIFIED_CHAT_ENABLED=true
UNIFIED_CHAT_DEFAULT_MODEL=claude-sonnet-4-5
UNIFIED_CHAT_ROUTING_TIMEOUT_MS=500
UNIFIED_CHAT_MAX_RETRIES=2

# Feature flags
UNIFIED_CHAT_LOG_ROUTING_DECISIONS=true
UNIFIED_CHAT_CACHE_ROUTING=false  # Future optimization
```

## Monitoring & Analytics

Track key metrics:
- Route distribution (% direct vs MCP vs multiagent)
- Routing latency (time to make routing decision)
- User satisfaction per route type
- False routing rate (user corrections)

## Future Enhancements

1. **Routing Cache**: Cache routing decisions for similar messages
2. **User Preferences**: Learn user's routing preferences over time
3. **Streaming Support**: Stream responses while routing decision is made
4. **Fallback Logic**: Graceful degradation if specialized handlers fail