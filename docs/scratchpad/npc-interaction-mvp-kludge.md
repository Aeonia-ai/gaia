# NPC Interaction System - MVP Kludge Documentation

**Status:** ✅ Implemented (2025-11-14)
**Branch:** `feature/unified-experience-system`
**Commit:** `b32e3ec`
**Timeline:** Refactor after Phase 1 demo (estimated 1-2 days)

---

## Overview

The NPC interaction system allows players to have natural language conversations with NPCs (like Louisa) via WebSocket. The current implementation is a **temporary MVP kludge** for the Phase 1 demo, creating a circular dependency between KB and Chat services.

## Current Architecture (MVP Kludge)

```
┌─────────┐                    ┌──────────────┐
│  Unity  │◄───WebSocket───────┤ KB Service   │
│ Client  │                    │              │
└─────────┘                    │ talk handler │
                               └──────┬───────┘
                                      │
                               HTTP POST /chat/message
                                      │
                                      ▼
                               ┌──────────────┐
                               │ Chat Service │
                               │              │
                               │ Louisa       │
                               │ Persona      │
                               └──────┬───────┘
                                      │
                     ┌────────────────┼────────────────┐
                     │                │                │
                     ▼                ▼                ▼
              check_quest_state  accept_bottle  grant_reward
                     │                │                │
              HTTP calls back to KB endpoints
                     │                │                │
                     ▼                ▼                ▼
                               ┌──────────────┐
                               │ KB Service   │
                               │              │
                               │ MVP Endpoints│
                               └──────────────┘
```

### Flow Breakdown

1. **Unity sends talk action via WebSocket:**
   ```json
   {
     "type": "action",
     "action": "talk",
     "npc_id": "louisa",
     "message": "Hello Louisa, can you help me?"
   }
   ```

2. **KB talk handler routes to Chat Service:**
   - File: `app/services/kb/handlers/talk.py:56`
   - Makes HTTP POST to `http://chat-service:8000/chat/message`
   - Passes: `persona_id="louisa"`, player message, context

3. **Chat Service processes with Louisa persona:**
   - Loads Louisa's system prompt from database
   - LLM has access to 4 NPC-specific KB tools
   - Persona-based filtering ensures Louisa only gets NPC tools

4. **If Louisa needs game state, calls KB tools:**
   - `check_quest_state` → `POST /experience/{exp}/quest/state`
   - `accept_bottle_from_player` → `POST /experience/{exp}/npc/accept_item`
   - `grant_quest_reward` → `POST /experience/{exp}/quest/reward`
   - `get_player_inventory` → `GET /experience/{exp}/player/inventory`

5. **KB executes tools and returns results to Chat:**
   - Tools access UnifiedStateManager directly
   - Return quest state, inventory, quest updates, etc.

6. **Chat Service generates final NPC dialogue:**
   - LLM synthesizes tool results into natural response
   - Returns dialogue to KB talk handler

7. **KB returns response to Unity via WebSocket:**
   ```json
   {
     "type": "action_response",
     "success": true,
     "message": "Oh, hello dear! Yes, I desperately need help...",
     "metadata": {"npc_id": "louisa", "dialogue_source": "chat_service_louisa_persona"}
   }
   ```

## Why This Is A Kludge

### 1. Circular Dependency
```
KB Service → Chat Service → KB Service
```
Creates tight coupling and potential for circular errors.

### 2. HTTP Overhead
- **3 HTTP calls per NPC interaction:**
  1. KB → Chat (send player message)
  2. Chat → KB (call quest/inventory tools, 1-4 calls)
  3. Chat → KB (final response, implicit)
- **Latency:** ~1-3 seconds (mostly LLM, but extra network hops add overhead)

### 3. Chat Service Knows Game Mechanics
The Louisa persona system prompt includes:
- Knowledge of specific quests (find_dream_bottles)
- Knowledge of specific items (bottle_mystery, bottle_joy, etc.)
- Game state structure assumptions
- Trust level mechanics

**Location:** Database `personas` table, row `7b197909-8837-4ed5-a67a-a05c90e817f0`

### 4. Duplicated Context
- Chat Service maintains conversation history
- KB Service maintains player state
- These aren't synchronized - potential for divergence

### 5. Tool Endpoint Coupling
Four MVP kludge endpoints exist ONLY for Chat Service to call back:
- `POST /experience/{exp}/quest/state`
- `POST /experience/{exp}/npc/accept_item`
- `POST /experience/{exp}/quest/reward`
- `GET /experience/{exp}/player/inventory`

**Location:** `app/services/kb/experience_endpoints.py:276-506`

These endpoints are marked with prominent warnings and should be removed in the refactor.

## Code Locations

### KB Service Files

**Talk Handler:**
```python
# app/services/kb/handlers/talk.py
async def handle_talk(user_id: str, experience_id: str, command_data: Dict[str, Any]) -> CommandResult:
    """Routes talk actions to Chat Service (MVP KLUDGE)"""
    # Makes HTTP call to chat service
    response = await client.post(
        f"{CHAT_SERVICE_URL}/chat/message",
        json={"message": player_message, "persona_id": "louisa", ...}
    )
```

**Registration:**
```python
# app/services/kb/main.py:173
from .handlers.talk import handle_talk
command_processor.register("talk", handle_talk)  # ⚠️ MVP KLUDGE
```

**MVP Kludge Endpoints:**
```python
# app/services/kb/experience_endpoints.py:276-506
# ═══════════════════════════════════════════════════════════════════════════
# ⚠️  MVP KLUDGE WARNING - NPC INTERACTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/{experience}/quest/state")
async def check_quest_state(...): ...

@router.post("/{experience}/npc/accept_item")
async def accept_item_from_player(...): ...

@router.post("/{experience}/quest/reward")
async def grant_quest_reward(...): ...

@router.get("/{experience}/player/inventory")
async def get_player_inventory(...): ...
```

### Chat Service Files

**NPC Tools Definition:**
```python
# app/services/chat/kb_tools.py:202-290
# 4 NPC-specific tools with full documentation

KB_TOOLS = [
    # ... (existing tools)
    {
        "type": "function",
        "function": {
            "name": "check_quest_state",
            "description": "Check the player's current quest state and progress...",
            ...
        }
    },
    # ... (3 more NPC tools)
]

# Organized tool lists for filtering
NPC_TOOLS = [KB_TOOLS[7], KB_TOOLS[8], KB_TOOLS[9], KB_TOOLS[10]]
```

**Tool Executors:**
```python
# app/services/chat/kb_tools.py:714-855
class KBToolExecutor:
    async def _execute_check_quest_state(self, args: dict) -> dict:
        """Makes HTTP call to KB /experience/{exp}/quest/state"""
        ...

    async def _execute_accept_bottle_from_player(self, args: dict) -> dict:
        """Makes HTTP call to KB /experience/{exp}/npc/accept_item"""
        ...

    # ... (2 more executors)
```

**Persona-Based Tool Filtering:**
```python
# app/services/chat/unified_chat.py:221-266
def _get_routing_tools_for_persona(self, persona_name: str) -> List[Dict]:
    """Filter routing tools by persona type"""
    if persona_name.lower() == "louisa":
        return []  # NPCs get NO routing tools
    elif persona_name.lower() in ["game master", "gamemaster"]:
        return [use_asset_service only]
    else:
        return self.routing_tools  # All routing tools

def _get_kb_tools_for_persona(self, persona_name: str) -> List[Dict]:
    """Filter KB tools by persona type"""
    if persona_name.lower() == "louisa":
        return NPC_TOOLS  # Only NPC-specific tools
    elif persona_name.lower() in ["game master", "gamemaster"]:
        return EXPERIENCE_TOOLS + KB_SEARCH_TOOLS
    else:
        return GENERAL_KB_TOOLS
```

**Persona Name Retrieval:**
```python
# app/shared/prompt_manager.py:17-43
@staticmethod
async def get_system_prompt_and_persona(user_id: str = None) -> tuple[str, str]:
    """Get system prompt and persona name for tool filtering"""
    persona = await persona_service.get_user_persona(user_id)
    if persona and persona.system_prompt:
        return (persona.system_prompt, persona.name)
    return ("You are a helpful AI assistant.", "default")
```

## Persona-Based Tool Distribution

| Persona | Routing Tools | KB Tools | Use Case |
|---------|---------------|----------|----------|
| **Louisa** (NPC) | None | NPC tools only (4 tools) | In-game NPC conversations |
| **Game Master** | `use_asset_service` only | Experience + search tools | Game coordination |
| **Default** | All routing tools | All general KB tools | General assistant |

### Current User Assignments

```sql
SELECT u.user_id, p.name as persona_name
FROM user_persona_preferences u
JOIN personas p ON u.persona_id = p.id;
```

Results:
- `jason@aeonia.ai` → **Game Master**
- `admin@aeonia.ai` → **Louisa** (for testing NPC tools directly through chat)

## Proper Future Architecture

Based on design in `docs/scratchpad/npc-llm-dialogue-system.md`:

```
┌─────────┐                    ┌──────────────────────────┐
│  Unity  │◄───WebSocket───────┤ KB Service               │
│ Client  │                    │                          │
└─────────┘                    │ ┌──────────────────────┐ │
                               │ │ talk handler         │ │
                               │ │                      │ │
                               │ │ 1. Load NPC template │ │
                               │ │    from markdown     │ │
                               │ │                      │ │
                               │ │ 2. Build system      │ │
                               │ │    prompt with:      │ │
                               │ │    - Personality     │ │
                               │ │    - Current quest   │ │
                               │ │    - Trust level     │ │
                               │ │    - Conversation    │ │
                               │ │      history         │ │
                               │ │                      │ │
                               │ │ 3. Call LLM directly │ │
                               │ │    (import singleton)│ │
                               │ │                      │ │
                               │ │ 4. Update state      │ │
                               │ │    internally        │ │
                               │ └──────────────────────┘ │
                               │                          │
                               │ Uses:                    │
                               │ - MultiProviderChatSvc   │
                               │ - UnifiedStateManager    │
                               │ - NPC templates (KB)     │
                               └──────────────────────────┘
```

### Benefits of Refactor

1. **No HTTP overhead** - Single service handles entire flow
2. **Direct state access** - No tool endpoints needed
3. **Unified context** - Conversation history stored with player state
4. **NPC templates in KB** - Personality/quests defined in markdown
5. **Trust system integrated** - Dialogue depth based on relationship
6. **Faster response** - ~1-2s (LLM only, no extra network hops)

### Refactor Implementation Plan

**Estimated Time:** 1-2 days

**Step 1: Move LLM Call to KB** (2 hours)
```python
# app/services/kb/handlers/talk.py (refactored)
from app.services.llm.chat_service import chat_service  # Import singleton

async def handle_talk(user_id: str, experience_id: str, command_data: Dict[str, Any]) -> CommandResult:
    # Load NPC template from KB markdown
    npc_template = await load_npc_template(experience_id, command_data["npc_id"])

    # Build system prompt with context
    system_prompt = build_npc_system_prompt(
        npc_template,
        player_state=await state_manager.get_player_view(experience_id, user_id),
        conversation_history=await get_npc_conversation_history(user_id, npc_id)
    )

    # Call LLM directly (no HTTP)
    response = await chat_service.chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command_data["message"]}
        ],
        model="claude-3-5-sonnet-latest",
        temperature=0.8
    )

    # Update conversation history
    await save_npc_conversation_turn(user_id, npc_id, command_data["message"], response["content"])

    return CommandResult(success=True, message_to_player=response["content"])
```

**Step 2: Create NPC Template System** (4 hours)
```markdown
<!-- /kb/experiences/wylding-woods/npcs/louisa.md -->
---
npc_id: louisa
name: Louisa
role: Dream Weaver
personality:
  - earnest
  - hopeful
  - formal and whimsical
current_situation: >
  Friends' dreams have been stolen by mischievous elf Neebling.
  Desperately needs help recovering dream bottles.
trust_levels:
  0-20: Polite but distant, vague about quest details
  21-50: Warming up, shares more about dream bottles
  51-80: Trusts player, reveals Neebling's location
  81-100: Close friend, offers special rewards
initial_greeting: >
  Oh, hello dear traveler! I am Louisa, guardian of these woods.
  I'm afraid I'm in quite a distressing situation...
---
```

**Step 3: Remove MVP Kludge** (1 hour)
- Delete 4 MVP endpoints from `experience_endpoints.py`
- Delete NPC tools from `kb_tools.py`
- Delete talk handler HTTP call logic
- Update Louisa persona to remove game-specific knowledge

**Step 4: Testing** (2 hours)
- Test NPC conversation flow via WebSocket
- Verify trust level affects dialogue
- Verify conversation history persists
- Performance testing (should be faster than MVP)

### Migration Path

1. **Keep MVP running** - Don't break the demo
2. **Implement refactor in parallel** - New handlers alongside old
3. **Feature flag** - `settings.USE_INTERNAL_NPC_LLM` to toggle
4. **Test thoroughly** - Ensure parity with MVP behavior
5. **Remove MVP code** - Clean up after successful transition

## Testing the Current MVP

### Via Unity WebSocket

```json
// Connect to WebSocket
ws://localhost:8001/ws/experience?experience=wylding-woods&user_id=admin@aeonia.ai

// Send talk action
{
  "type": "action",
  "action": "talk",
  "npc_id": "louisa",
  "message": "Hello Louisa, I heard you need help?"
}

// Expected response
{
  "type": "action_response",
  "success": true,
  "message": "Oh, hello dear! Yes, I desperately need help finding the dream bottles that were stolen by that mischievous elf Neebling...",
  "metadata": {
    "npc_id": "louisa",
    "dialogue_source": "chat_service_louisa_persona"
  }
}
```

### Via Chat Service Directly (as admin@aeonia.ai)

Since `admin@aeonia.ai` is assigned to Louisa persona, you can test NPC tools directly:

```bash
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "message": "Check if the player has completed the find_dream_bottles quest",
    "user_id": "admin@aeonia.ai"
  }'
```

Louisa should use the `check_quest_state` tool automatically.

## Performance Characteristics

### Current MVP (Measured)
- **Total latency:** 1-3 seconds
  - KB → Chat HTTP: ~50ms
  - LLM processing: 1-2s
  - Chat → KB tool calls: 10-50ms each
  - Response back to Unity: ~50ms

### Expected After Refactor
- **Total latency:** 1-2 seconds
  - LLM processing: 1-2s (unchanged)
  - No HTTP overhead
  - Direct state access: <10ms

**Improvement:** ~20-30% faster, more reliable

## Security Considerations

### Current MVP Issues
1. **Inter-service auth** - Uses `X-API-Key` header for KB ↔ Chat
2. **Persona hijacking** - User could potentially set persona_id to "louisa" in direct chat calls
3. **Tool endpoint exposure** - MVP endpoints are publicly accessible

### After Refactor
1. **No inter-service calls** - Single service, no auth needed
2. **NPC identity server-controlled** - npc_id from WebSocket action, not user input
3. **No tool endpoints** - Internal state access only

## Known Issues

### 1. Conversation History Divergence
- Chat Service stores conversation in its database
- KB Service has no access to this history
- If KB needs to understand context, it can't see past conversation

**Workaround:** Keep conversations short for demo

### 2. Persona Prompt Coupling
- Louisa's system prompt hardcodes game knowledge
- Changing quest design requires database update
- Not version-controlled with game content

**Workaround:** Keep quest design stable for demo

### 3. No Trust Level Implementation
- Code references trust system
- `grant_quest_reward(reward_type="trust")` exists
- But trust isn't actually stored or used yet

**Workaround:** Trust system is future enhancement

## Documentation References

- **Design:** `docs/scratchpad/npc-llm-dialogue-system.md`
- **Demo Guide:** `docs/scratchpad/aoi-phase1-demo-guide.md`
- **WebSocket Protocol:** `docs/scratchpad/websocket-aoi-client-guide.md`
- **Persona System:** `docs/reference/services/persona-system-guide.md`

## Questions & Decisions

### Q: Why not refactor immediately?
**A:** Demo is in 2-3 days. The MVP works and is low-risk. Refactor can wait until after demo when we have more time to test thoroughly.

### Q: Why create tool endpoints if they'll be removed?
**A:** Fastest path to working demo using existing chat infrastructure. The endpoints are clearly marked as temporary and isolated for easy removal.

### Q: Why does admin@aeonia.ai use Louisa persona?
**A:** Testing convenience. Allows testing NPC tool behavior directly through chat UI without needing Unity client.

### Q: Can we use this pattern for other NPCs?
**A:** Yes, but each NPC needs:
1. Persona in database with system prompt
2. Tool filtering logic (or reuse Louisa's NPC_TOOLS)
3. Understanding that this is temporary architecture

For the refactor, NPCs will be defined in markdown templates, not database personas.

---

## Summary

The NPC interaction MVP is a **functional kludge** that achieves the demo goal of natural language NPC dialogue. It's explicitly temporary, well-documented, and has a clear refactor path. The circular dependency and HTTP overhead are acceptable trade-offs for rapid development, but should not ship to production.

**Timeline:**
- **Now:** MVP works, demo-ready
- **After demo:** 1-2 day refactor to proper architecture
- **Future:** Template-based NPCs, trust system, conversation memory
