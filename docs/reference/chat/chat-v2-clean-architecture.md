# Chat Service V2: Clean Architecture Design



## Overview

A ground-up rebuild of the chat service, keeping what works and fixing fundamental architectural issues.

## Core Principles

1. **Single Source of Truth**: One way to do each thing
2. **Clear Separation**: Persona identity vs functionality
3. **Performance First**: Sub-second responses for gaming
4. **Testable**: Every component independently testable
5. **Minimal**: No experimental code, no "just in case" features

## Architecture

### 1. Message Pipeline

```
Request → Auth → Context → Persona → Filter → LLM → Response → Store
```

Each stage has a single responsibility:

```python
# Clean message pipeline
class ChatV2Pipeline:
    async def process(self, request: ChatRequest) -> ChatResponse:
        # 1. Extract user context
        context = await self.extract_context(request)
        
        # 2. Load or create conversation
        conversation = await self.ensure_conversation(context)
        
        # 3. Build message array (with filtering!)
        messages = await self.build_messages(conversation, request)
        
        # 4. Execute LLM call
        response = await self.execute_llm_call(messages, context)
        
        # 5. Store results
        await self.store_conversation_turn(conversation, request, response)
        
        return response
```

### 2. Message Array Structure

**Critical Rule**: Only ONE system message, ALWAYS first.

```python
class MessageBuilder:
    async def build_messages(
        self, 
        conversation: Conversation,
        request: ChatRequest
    ) -> List[Message]:
        messages = []
        
        # 1. System message (persona + minimal instructions)
        system_message = await self.build_system_message(
            user_id=conversation.user_id,
            persona_id=conversation.persona_id
        )
        messages.append({"role": "system", "content": system_message})
        
        # 2. Conversation history (filtered!)
        for msg in conversation.messages:
            if msg.role in ["user", "assistant"]:  # NO system messages from history
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # 3. Current user message
        messages.append({"role": "user", "content": request.message})
        
        return messages
```

### 3. Persona Integration

**Clean Separation**: Persona defines identity, not functionality.

```python
class PersonaSystem:
    async def build_system_message(
        self, 
        user_id: str, 
        persona_id: Optional[str] = None
    ) -> str:
        # Load persona
        persona = await self.load_persona(user_id, persona_id)
        
        # Persona focuses on identity
        identity_prompt = persona.prompt  # "You are Mu, a cheerful robot..."
        
        # Minimal functional instructions (if needed)
        functional_prompt = self.get_minimal_instructions()
        
        # Combine with clear separation
        return f"{identity_prompt}\n\n{functional_prompt}"
    
    def get_minimal_instructions(self) -> str:
        # Only the absolute essentials
        return """
When using tools, explain what you're doing in character.
Maintain your personality throughout all interactions.
"""
```

### 4. Routing Strategy

**Separate Routing from Identity**: Use tool availability, not system prompt instructions.

```python
class RouterV2:
    def get_tools_for_request(self, request: ChatRequest) -> List[Tool]:
        # Let tool descriptions guide usage, not system prompt
        tools = []
        
        # Always available
        tools.extend(KB_TOOLS)  # Well-described tools
        
        # Conditionally available based on context
        if self.might_need_file_ops(request.message):
            tools.append(MCP_AGENT_TOOL)
        
        if self.might_need_assets(request.message):
            tools.append(ASSET_TOOL)
            
        return tools
    
    def might_need_file_ops(self, message: str) -> bool:
        # Simple heuristics, not complex routing
        file_keywords = ["file", "directory", "folder", "read", "write"]
        return any(kw in message.lower() for kw in file_keywords)
```

### 5. Conversation Management

```python
class ConversationManagerV2:
    async def ensure_conversation(
        self, 
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> Conversation:
        if conversation_id:
            # Load existing (with user validation)
            conv = await self.load_conversation(conversation_id, user_id)
            if not conv:
                # Invalid ID, create new
                return await self.create_conversation(user_id)
            return conv
        else:
            # Create new
            return await self.create_conversation(user_id)
    
    async def create_conversation(self, user_id: str) -> Conversation:
        # Get user's persona preference
        persona_id = await self.get_user_persona(user_id)
        
        return Conversation(
            id=str(uuid4()),
            user_id=user_id,
            persona_id=persona_id,
            created_at=datetime.utcnow(),
            messages=[]  # No system messages stored!
        )
    
    async def store_turn(
        self,
        conversation: Conversation,
        user_message: str,
        assistant_message: str
    ):
        # Only store user/assistant messages
        conversation.messages.extend([
            Message(role="user", content=user_message),
            Message(role="assistant", content=assistant_message)
        ])
        await self.save_conversation(conversation)
```

### 6. Clean File Structure

```
app/services/chat/
├── v2/
│   ├── __init__.py
│   ├── chat.py              # Main entry point
│   ├── pipeline.py          # Message pipeline
│   ├── persona.py           # Persona integration  
│   ├── router.py            # Tool routing
│   ├── conversation.py      # Conversation management
│   └── models.py            # Clean data models
├── shared/
│   ├── conversation_store.py  # Reuse existing DB layer
│   └── persona_service.py     # Reuse existing persona DB
└── main.py                    # Register v2 endpoints
```

### 7. API Design

Single, clean endpoint:

```python
@app.post("/v2/chat")
async def chat_v2(
    request: ChatRequest,
    auth: Dict = Depends(get_current_auth_unified)
) -> ChatResponse:
    """
    Clean chat endpoint with proper persona support.
    
    Request:
    {
        "message": "Hello!",
        "conversation_id": "optional-uuid",
        "stream": false
    }
    
    Response:
    {
        "response": "Hello! I'm Mu, your cheerful robot companion!",
        "conversation_id": "uuid",
        "message_id": "uuid",
        "persona_id": "mu"
    }
    """
    return await chat_pipeline.process(request, auth)
```

### 8. Testing Strategy

```python
# Unit tests - each component in isolation
test_message_builder.py     # Test message array construction
test_persona_system.py      # Test persona loading/injection
test_router.py              # Test tool selection
test_conversation.py        # Test conversation management

# Integration tests - components together
test_pipeline.py            # Test full pipeline
test_persona_identity.py    # Test persona consistency

# E2E tests - full system
test_chat_e2e.py           # Test via gateway with real auth
```

## Migration Strategy

### Phase 1: Build Core (Week 1)
1. Create v2 directory structure
2. Build clean pipeline components
3. Write comprehensive tests
4. Deploy alongside v1

### Phase 2: Validate (Week 2)
1. A/B test with select users
2. Monitor performance metrics
3. Verify persona consistency
4. Fix edge cases

### Phase 3: Migrate (Week 3)
1. Switch default to v2
2. Migrate active conversations
3. Deprecate v1 endpoints
4. Clean up old code

## Key Differences from V1

1. **No system messages in history** - Prevents persona override
2. **Persona-first design** - Identity is primary, tools secondary
3. **Clean pipeline** - Each stage has one job
4. **Tool-based routing** - Let LLM decide based on available tools
5. **No orchestration complexity** - Simple is faster
6. **Test-driven** - Every component tested independently

## Performance Targets

- First response: < 500ms (hot path)
- With conversation load: < 800ms  
- Streaming first token: < 300ms
- Memory usage: < 100MB per conversation

## Success Metrics

1. **Persona Consistency**: 100% of responses maintain character
2. **Response Time**: 95th percentile < 1 second
3. **Code Simplicity**: < 2,000 lines total (vs current 13,772)
4. **Test Coverage**: > 90% for core paths
5. **Developer Velocity**: New features in hours, not days

## Conclusion

This clean architecture solves the fundamental issues:
- Personas work consistently
- No message array pollution  
- Clear separation of concerns
- Performance by design
- Testable and maintainable

The rewrite leverages everything learned from v1's evolution while avoiding the architectural traps that made it complex. This is the chat service you'd build if you started today with full knowledge of the requirements.