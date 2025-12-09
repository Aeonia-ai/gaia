# ADR-004: Enabling Personas in Gaia Chat Service with TDD

## Status
Implemented

## Context
- Persona code exists in gaia chat service but router is commented out
- Database tables have been created with default "Mu" persona
- We want to enable personas using Test-Driven Development
- Need to decide: Should personas be exposed via gateway or accessed directly?

## Decision
1. Use strict TDD approach to enable personas in the chat service
2. Initially expose personas directly on chat service at `/personas/*`
3. Add gateway routes later if needed for unified API surface

### Architectural Choice: Direct vs Gateway Access

**Current State:**
- Web UI has NO persona functionality yet
- Gateway doesn't currently proxy persona endpoints  
- Chat service has persona router implementation (commented out)
- Chat endpoints don't use personas in message processing yet

**Decision: Personas Encapsulated in Chat Service**
- Personas will be available at `http://chat-service:8000/personas/*`
- Only for API clients (mobile apps, external integrations)  
- Web UI will NOT manipulate persona endpoints directly
- Chat service internally manages persona selection and prompt injection
- Gateway proxy not needed - personas are chat service implementation detail

## Test-Driven Development Approach

### 1. Define Expected Behavior FIRST
Before touching any code, we write tests for what we WANT to happen:

```python
# Test 1: Service should have persona endpoints
def test_personas_endpoint_exists():
    response = client.get("/personas/")
    assert response.status_code == 200  # This will FAIL

# Test 2: Default user gets Mu persona
def test_new_user_gets_default_persona():
    response = client.get("/personas/current", headers=auth)
    assert response.json()["persona"]["name"] == "Mu"  # This will FAIL

# Test 3: Chat uses persona system prompt
def test_chat_uses_persona_prompt():
    # Set user to Mu persona
    # Send chat message
    # Verify response has Mu personality
    # This will FAIL
```

### 2. Run Tests - They Should All Fail
```bash
pytest tests/integration/test_personas.py
# Expected: All tests fail because personas router is commented out
```

### 3. Write Minimum Code to Make Tests Pass
Only NOW do we:
1. Uncomment the personas router
2. Fix any import errors
3. Implement missing methods
4. Run tests again

### 4. Refactor
Once tests pass, we can refactor for better design

## The TDD Cycle for Personas

1. **RED**: Write test for "GET /personas/ returns list"
2. **GREEN**: Uncomment router, fix imports until test passes
3. **REFACTOR**: Clean up code

4. **RED**: Write test for "new users get Mu persona"
5. **GREEN**: Implement default persona logic
6. **REFACTOR**: Optimize database queries

7. **RED**: Write test for "chat messages use persona prompt"
8. **GREEN**: Integrate personas with chat flow
9. **REFACTOR**: Extract prompt building logic

## Test Categories (Written Before Code)

### API Contract Tests
```python
- GET /personas/ returns PersonaListResponse
- GET /personas/current returns PersonaResponse  
- POST /personas/set accepts PersonaId, returns success
- GET /personas/{id} returns specific persona
```

### Integration Tests
```python
- Database has Mu persona
- User preferences persist
- Missing persona returns 404
- Invalid persona_id returns 400
```

### Behavioral Tests
```python
- Chat with Mu uses robotic expressions
- Different personas give different responses
- Persona switch changes behavior immediately
```

## Consequences

### Positive
- API design driven by tests
- No code written without failing test first
- Clear specification of expected behavior
- High confidence in implementation
- Built-in regression protection

### Negative
- Slower initial development
- Requires discipline to write tests first
- May need to refactor tests as understanding evolves

## Implementation Plan

### Phase 1: Enable Basic Persona API (Week 1)
1. **Write Test #1** (personas endpoint) → **Uncomment router** → Test passes
2. **Write Test #2** (auth required) → **Add auth middleware** → Test passes  
3. **Write Test #3** (default persona) → **Implement default logic** → Test passes
4. **Write Tests #4-6** (persona selection) → **Complete CRUD operations** → Tests pass

**Deliverable**: Full persona API working with authentication and validation

### Phase 2: Chat Integration & Directives (Week 2)
1. **Write Test #7** (PromptManager) → **Enhance PromptManager** → Test passes
2. **Write Test #8** (directives) → **Add directive injection** → Test passes
3. **Write Test #9** (chat integration) → **Integrate with chat service** → Test passes
4. **Write Test #10** (persona switching) → **Full chat personalization** → Test passes

**Deliverable**: Chat service uses persona-aware system prompts with directives

### Phase 3: Caching & Polish (Week 3)  
1. **Write Tests #11-12** (Redis caching) → **Implement caching layer** → Tests pass
2. **Write Test #13** (error handling) → **Add graceful fallbacks** → Test passes
3. **Performance testing** and **load validation**
4. **API documentation** for external consumers

**Deliverable**: Production-ready persona system with caching and error handling

## Redis Caching Strategy

### Cache Design
Since users change personas "infrequently", we'll implement caching:

```python
# Cache keys
user_persona_key = f"user_persona:{user_id}"    # User's current persona
persona_detail_key = f"persona:{persona_id}"     # Persona details  
personas_list_key = "personas:active"            # List of active personas

# TTLs (Time To Live)
USER_PERSONA_TTL = 3600   # 1 hour (changes are infrequent)
PERSONA_DETAIL_TTL = 1800 # 30 minutes
PERSONAS_LIST_TTL = 300   # 5 minutes
```

### Cache Tests (TDD)
```python
# Test 1: Cache miss returns None
def test_get_user_persona_cache_miss():
    # Clear cache
    # Get persona (should query DB)
    # Verify DB was called

# Test 2: Cache hit avoids DB
def test_get_user_persona_cache_hit():
    # Warm cache
    # Get persona again
    # Verify DB was NOT called

# Test 3: Setting persona invalidates cache
def test_set_persona_invalidates_cache():
    # Warm cache
    # Change persona
    # Verify old cache entry deleted
```

## Simplified Test Plan

### Phase 1: Basic Persona API (Week 1)

#### 1. API Endpoint Tests
```python
# Test 1: Router accessibility (FIRST TEST - WILL FAIL)
def test_personas_endpoint_exists():
    response = client.get("/personas/")
    assert response.status_code == 200  # FAILS until router uncommented

# Test 2: Authentication required
def test_personas_requires_auth():
    response = client.get("/personas/")  # No auth header
    assert response.status_code == 401  # FAILS until auth middleware active
```

#### 2. Default Persona Logic
```python
# Test 3: New users get Mu by default
def test_new_user_gets_default_persona():
    response = client.get("/personas/current", headers=new_user_auth)
    assert response.json()["persona"]["name"] == "Mu"  # FAILS until default logic

# Test 4: Mu exists in database (should PASS immediately)
def test_mu_persona_in_database():
    personas = await PersonaService().list_personas()
    assert any(p.name == "Mu" for p in personas)  # PASSES (already created)
```

#### 3. Persona Selection
```python
# Test 5: Setting active persona
def test_user_can_set_persona():
    # Get Mu's ID from /personas/
    # POST to /personas/set with persona_id
    # GET /personas/current should return Mu
    # FAILS until set endpoint implemented

# Test 6: Invalid persona handling
def test_setting_invalid_persona_fails():
    response = client.post("/personas/set", json={"persona_id": "invalid-uuid"})
    assert response.status_code == 404  # FAILS until validation added
```

### Phase 2: Chat Integration & Directives (Week 2)

#### 4. Prompt Manager Integration
```python
# Test 7: Enhanced PromptManager works
def test_prompt_manager_with_persona():
    prompt = await PromptManager.get_system_prompt_with_persona("test-user")
    assert "Mu" in prompt and "directives" in prompt.lower()
    # FAILS until PromptManager enhanced

# Test 8: AeoniaMCP directive injection
def test_directives_injected_into_persona_prompt():
    prompt = await PromptManager.get_system_prompt_with_persona("mu-user")
    assert '"m": "method_name"' in prompt  # JSON-RPC format documented
    assert 'AeoniaMCP Directive System' in prompt
    assert 'category (voice, game, time)' in prompt
    # FAILS until AeoniaMCP directive section implemented
```

#### 5. Chat Service Integration
```python
# Test 9: Chat uses persona-aware system prompt
def test_chat_uses_persona_system_prompt():
    # Set user to Mu persona
    # Send chat message
    # Mock LLM call should receive system prompt with "Beep boop!"
    # FAILS until chat service integration

# Test 10: Different personas = different prompts
def test_persona_switching_changes_system_prompt():
    # Switch from Mu to another persona
    # Verify system prompt changes in next chat call
    # FAILS until multiple personas and switching works
```

### Phase 3: Caching & Polish (Week 3)

#### 6. Redis Caching
```python
# Test 11: Persona lookup caching
def test_persona_lookup_uses_cache():
    # First call hits database
    # Second call hits Redis cache
    # Verify cache key exists and DB not called twice
    # FAILS until Redis caching implemented

# Test 12: Cache invalidation on persona change
def test_cache_invalidated_on_persona_switch():
    # User switches personas
    # Cache entry should be deleted
    # Next lookup hits database
    # FAILS until cache invalidation logic
```

#### 7. Performance & Error Handling  
```python
# Test 13: Graceful fallback
def test_fallback_when_persona_service_down():
    # Mock PersonaService to raise exception
    # PromptManager should return basic fallback prompt
    # Chat should still work
    # FAILS until error handling implemented
```

### TDD Implementation Order
1. **Write failing test #1** → Uncomment personas router → Test passes
2. **Write failing test #2** → Add auth middleware → Test passes  
3. **Write failing test #3** → Implement default persona logic → Test passes
4. **Continue pattern...** Each test drives exactly the code needed

### Success Criteria
- ✅ All 13 tests passing
- ✅ Mu persona responds with "Beep boop!" personality  
- ✅ Persona switching works via API
- ✅ Chat service uses persona-aware system prompts
- ✅ Redis caching improves persona lookup performance
- ✅ Directives properly injected into all persona prompts
- ✅ **Zero web UI complexity** - pure API functionality

## Conversation History Handling

Each chat message should store the persona_id used at message time:
```sql
ALTER TABLE messages ADD COLUMN persona_id UUID REFERENCES personas(id);
```

This ensures historical accuracy when viewing past conversations.

## Analytics Considerations

Track in Redis counters:
- Persona usage frequency: `persona:usage:{persona_id}`
- Persona switch events: `user:persona:switches:{user_id}`
- Popular persona pairs: `persona:switches:{from_id}:{to_id}`

## Simplified Prompt Composition 

### KISS Approach: Complete Prompts + Directive Injection
Keep personas simple - store complete system prompts with minimal templating:

```sql
-- Simple schema:
CREATE TABLE personas (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    system_prompt TEXT NOT NULL,        -- Complete persona prompt
    personality_traits JSONB DEFAULT '{}',
    capabilities JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true
);

-- Example Mu persona:
INSERT INTO personas (name, description, system_prompt) VALUES (
    'Mu',
    'A cheerful robot companion',
    'You are Mu, a cheerful robot companion with a helpful, upbeat personality.

Use robotic expressions like "Beep boop!" and "Bleep bloop!" for charm.
Stay enthusiastic and helpful in all interactions.

{directives_section}'
);
```

### Enhanced Prompt Manager with AeoniaMCP Directives
Centralize AeoniaMCP's sophisticated directive system in PromptManager:

```python
# app/shared/prompt_manager.py (enhanced)
class PromptManager:
    @staticmethod
    def get_directives_section() -> str:
        """AeoniaMCP JSON-RPC directive system documentation"""
        return '''## AeoniaMCP Directive System

You can enhance responses with interactive directives using Joseph's abridged JSON-RPC v2.0 format:

### Format
```json
{
  "m": "method_name",      // Required: command name
  "p": {"param": "value"}, // Optional: parameters
  "c": "category",         // Optional: category (voice, game, time)
  "s": "subcategory"       // Optional: subcategory
}
```

### Core Directives

**Timing Control:**
`{"m":"pause","p":{"sec":2}}` - Creates natural pauses in dialogue

**Visual Effects:**
`{"m":"effect","p":{"name":"sparkle","intensity":0.8}}` - Triggers visual effects
`{"m":"effect","p":{"name":"soft_glow"}}` - Atmospheric lighting

**Character Animation:**
`{"m":"animation","p":{"name":"wave","duration":3}}` - Character gestures
`{"m":"animation","p":{"name":"nod_head"}}` - Non-verbal communication

**Game World Integration:**
`{"m":"quest","p":{"action":"start","name":"rescueNPC","priority":"high"}}` - Game events
`{"m":"custom","p":{"event":"SaveProgress"}}` - Custom game functionality

### Usage Guidelines
- Embed directives naturally within conversational text
- System parses JSON from natural language automatically
- Text before/after directives remains as clean dialogue
- Use directives to match your persona's personality
- Categories help organize directive types (voice, game, time)

Example: "Let me help you relax. {"m":"pause","p":{"sec":2}} Take a deep breath."'''

    @staticmethod
    async def get_system_prompt_with_persona(user_id: str) -> str:
        """Get complete system prompt: persona + AeoniaMCP directives"""
        persona = await PersonaService().get_user_persona(user_id)
        
        if persona and persona.system_prompt:
            return persona.system_prompt.format(
                directives_section=cls.get_directives_section()
            )
        
        return f"You are a helpful AI assistant.\n\n{cls.get_directives_section()}"
```

### Key Insight: AeoniaMCP Directives vs Tools
- **Tools** (KB search, MCP-agent) = Server-side capabilities, same for all personas
- **AeoniaMCP Directives** = Client-side JSON-RPC commands embedded in LLM responses
  - Mixed text parsing extracts JSON from natural language
  - Categories: voice, game, time with optional subcategories
  - Game world integration (quests, effects, animations)
  - Advanced error handling and validation
- **Personas affect directive USAGE PATTERNS**:
  - Mu might use: `{"m":"effect","p":{"name":"robotic_sparkle"},"c":"game"}`
  - Serene might use: `{"m":"pause","p":{"sec":3},"c":"time"}` for meditation
  - Same directive catalog available, different personality-driven choices

## References
- [Test-Driven Development by Example - Kent Beck](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530)
- [TDD Cycle: Red, Green, Refactor](https://www.codecademy.com/article/tdd-red-green-refactor)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)