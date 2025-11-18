# NPC LLM Dialogue System Design

**Status**: Design Phase
**Date**: 2025-11-13
**Purpose**: Enable authentic NPC conversations using LLM for response generation

---

## Overview

NPCs in Wylding Woods should have authentic, context-aware conversations using LLM generation. This document outlines how to implement the `talk` command using the existing chat service infrastructure.

**Key Insight**: We already have a multi-provider LLM service (`MultiProviderChatService`) used by the chat service. We can reuse it for NPC dialogue!

---

## Architecture Pattern (from Chat Service)

### 1. Chat Service LLM Usage

**File**: `app/services/chat/unified_chat.py` and `app/services/llm/chat_service.py`

```python
from app.services.llm.chat_service import chat_service

# Generate completion
response = await chat_service.chat_completion(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": player_message}
    ],
    model="claude-3-5-sonnet-latest",  # or auto-select
    temperature=0.8,  # More creative for NPC personality
    max_tokens=500,
    user_id=user_id
)

npc_reply = response["content"]
```

**Key Features**:
- Multi-provider support (Claude, OpenAI, etc.)
- Automatic model selection based on complexity
- Fallback to other providers if primary fails
- Request tracking and instrumentation
- Streaming support (for real-time responses)

---

## NPC Dialogue Implementation

### Pattern: Fast Path Handler with LLM

**File**: `app/services/kb/handlers/talk.py` (NEW)

```python
"""
Fast command handler for NPC conversations with LLM-generated dialogue.

Response time: ~1-3s (LLM latency)
"""

import logging
from typing import Any, Dict
from datetime import datetime

from app.shared.models.command_result import CommandResult
from app.services.kb.kb_agent import kb_agent

logger = logging.getLogger(__name__)


async def handle_talk(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> CommandResult:
    """
    Handle NPC conversation with LLM-generated dialogue.

    Flow:
    1. Validate NPC exists and is nearby
    2. Load NPC template (personality, situation, quests)
    3. Load player-NPC relationship state (trust, history)
    4. Build LLM prompt with full context
    5. Generate authentic NPC response
    6. Update conversation history and trust
    7. Return dialogue + state updates

    Args:
        user_id: Player talking to NPC
        experience_id: Experience ID (e.g., "wylding-woods")
        command_data: {"npc_id": "louisa", "message": "hello"}

    Returns:
        CommandResult with NPC dialogue and state updates
    """

    npc_id = command_data.get("npc_id")
    player_message = command_data.get("message", "")  # Default to greeting

    if not npc_id:
        return CommandResult(
            success=False,
            message_to_player="Who do you want to talk to? Try: talk to <npc_name>"
        )

    try:
        state_manager = kb_agent.state_manager
        llm_service = kb_agent.llm_service

        if not state_manager or not llm_service:
            raise Exception("KB Agent not initialized")

        # 1. Validate NPC proximity
        player_view = await state_manager.get_player_view(experience_id, user_id)
        world_state = await state_manager.get_world_state(experience_id)

        current_location = player_view.get("player", {}).get("current_location")
        current_area = player_view.get("player", {}).get("current_area")

        npc_location, npc_area = _find_npc_location(world_state, npc_id)

        if not npc_location:
            return CommandResult(
                success=False,
                message_to_player=f"There's no one named '{npc_id}' here."
            )

        if npc_location != current_location or npc_area != current_area:
            return CommandResult(
                success=False,
                message_to_player=f"You need to be near {npc_id} to talk to them."
            )

        # 2. Load NPC template
        npc_template = await _load_npc_template(experience_id, npc_id)

        # 3. Load player-NPC relationship state
        npc_state = player_view.get("player", {}).get("npcs", {}).get(npc_id, {})

        # Initialize if first meeting
        if not npc_state:
            npc_state = {
                "first_met": datetime.utcnow().isoformat(),
                "trust_level": 50,  # Neutral starting trust
                "total_conversations": 0,
                "conversation_history": []
            }

        # 4. Build LLM prompt
        system_prompt = _build_npc_system_prompt(npc_template, npc_state, player_view)

        # 5. Generate NPC response using LLM
        response = await llm_service.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": player_message or "Hello!"}
            ],
            model="claude-3-5-sonnet-latest",  # Good for creative dialogue
            temperature=0.8,  # More personality variation
            max_tokens=500,
            user_id=user_id
        )

        npc_dialogue = response["content"]

        # 6. Update conversation history and trust
        trust_change = _calculate_trust_change(player_message, npc_state)
        new_trust = min(100, max(0, npc_state.get("trust_level", 50) + trust_change))

        conversation_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "player": player_message,
            "npc": npc_dialogue,
            "trust_change": trust_change
        }

        # Keep last 20 conversation turns
        history = npc_state.get("conversation_history", [])[-19:]
        history.append(conversation_entry)

        # 7. Build state updates
        state_updates = {
            "player": {
                "npcs": {
                    npc_id: {
                        "last_interaction": datetime.utcnow().isoformat(),
                        "total_conversations": npc_state.get("total_conversations", 0) + 1,
                        "trust_level": new_trust,
                        "conversation_history": history
                    }
                }
            }
        }

        # Apply updates
        await state_manager.update_player_view(
            experience=experience_id,
            user_id=user_id,
            updates=state_updates
        )

        # Format response with trust indicator
        if trust_change != 0:
            trust_indicator = f"\n\n[Trust: {npc_state.get('trust_level', 50)} → {new_trust}]"
        else:
            trust_indicator = ""

        return CommandResult(
            success=True,
            message_to_player=npc_dialogue + trust_indicator,
            state_changes=state_updates,
            metadata={
                "npc_id": npc_id,
                "trust_level": new_trust,
                "trust_change": trust_change,
                "conversation_turn": npc_state.get("total_conversations", 0) + 1
            }
        )

    except Exception as e:
        logger.error(f"Error in handle_talk: {e}", exc_info=True)
        return CommandResult(
            success=False,
            message_to_player=f"Could not talk to {npc_id}. {str(e)}"
        )


def _find_npc_location(world_state: Dict, npc_id: str) -> tuple:
    """Find NPC's location and area in world state."""
    locations = world_state.get("locations", {})

    for location_id, location_data in locations.items():
        # Check location-level NPC
        if location_data.get("npc") == npc_id:
            return (location_id, None)

        # Check area-level NPCs
        areas = location_data.get("areas", {})
        for area_id, area_data in areas.items():
            if area_data.get("npc") == npc_id:
                return (location_id, area_id)

    return (None, None)


async def _load_npc_template(experience_id: str, npc_id: str) -> Dict:
    """Load NPC template from KB markdown file."""
    # Path: /kb/experiences/{exp}/templates/npcs/{npc_id}.md

    from app.services.kb.kb_agent import kb_agent

    template_path = f"{experience_id}/templates/npcs/{npc_id}.md"

    try:
        content = await kb_agent.kb_storage.read_file(template_path)
        # Parse markdown into structured data
        # For MVP, just extract description and personality sections
        return _parse_npc_markdown(content)
    except Exception as e:
        logger.warning(f"Could not load NPC template for {npc_id}: {e}")
        return {
            "name": npc_id.replace("_", " ").title(),
            "personality": "Friendly and helpful",
            "current_situation": "Going about their day"
        }


def _parse_npc_markdown(content: str) -> Dict:
    """Parse NPC markdown template into structured data."""
    # Simple parser for MVP - extract key sections
    # TODO: Use proper markdown parser or YAML frontmatter

    import re

    data = {
        "name": "",
        "description": "",
        "personality": "",
        "current_situation": "",
        "relationships": {},
        "quests": []
    }

    # Extract ## Personality section
    personality_match = re.search(r'## Personality\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if personality_match:
        data["personality"] = personality_match.group(1).strip()

    # Extract ## Current Situation section
    situation_match = re.search(r'## Current Situation\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if situation_match:
        data["current_situation"] = situation_match.group(1).strip()

    # Extract ## Description section
    desc_match = re.search(r'## Description\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if desc_match:
        data["description"] = desc_match.group(1).strip()

    return data


def _build_npc_system_prompt(
    npc_template: Dict,
    npc_state: Dict,
    player_view: Dict
) -> str:
    """Build comprehensive system prompt for NPC LLM generation."""

    npc_name = npc_template.get("name", "Unknown")
    personality = npc_template.get("personality", "")
    situation = npc_template.get("current_situation", "")
    trust_level = npc_state.get("trust_level", 50)
    total_convos = npc_state.get("total_conversations", 0)

    # Get recent conversation history for context
    history = npc_state.get("conversation_history", [])[-5:]
    history_text = ""
    if history:
        history_text = "\n\nRecent conversation:\n"
        for entry in history:
            history_text += f"Player: {entry['player']}\nYou: {entry['npc']}\n\n"

    prompt = f"""You are {npc_name}, an NPC in the Wylding Woods fantasy game.

## Your Personality
{personality}

## Your Current Situation
{situation}

## Your Relationship with This Player
- Trust level: {trust_level}/100
  (0-30: wary/distant, 31-60: neutral/polite, 61-85: friendly/open, 86-100: close friend/confidant)
- Total conversations: {total_convos}
- First met: {npc_state.get('first_met', 'Just now')}
{history_text}

## Guidelines for Responses
1. **Stay in character**: Respond as {npc_name} would, given your personality and situation
2. **Be authentic**: Use natural language, emotions, body language (in italics)
3. **Trust matters**: Share more personal information and quest details with higher trust
4. **Remember context**: Reference previous conversations and player actions
5. **Be concise**: Keep responses to 2-4 paragraphs unless the player asks for details
6. **Show emotion**: Use body language cues like *fidgets*, *brightens*, *wings flutter*
7. **Offer paths forward**: Suggest what the player might do next (subtly, in character)

## What NOT to do
- Don't break character or mention game mechanics directly
- Don't give quest rewards (system handles that)
- Don't narrate player actions (only your own actions and reactions)
- Don't be overly formal unless that's your personality
- Don't repeat information the player already knows (check conversation history)

Respond to the player's message naturally and authentically."""

    return prompt


def _calculate_trust_change(player_message: str, npc_state: Dict) -> int:
    """Calculate trust change based on player message."""
    # Simple heuristic for MVP
    # TODO: Use LLM to analyze sentiment and appropriateness

    message_lower = player_message.lower()

    # Positive keywords
    if any(word in message_lower for word in ["help", "yes", "agree", "thank", "please"]):
        return 2

    # Negative keywords
    if any(word in message_lower for word in ["no", "refuse", "rude", "insult"]):
        return -3

    # Neutral conversation
    return 1  # Small positive for engaging in conversation


# Helper function
async def _load_npc_template(experience_id: str, npc_id: str) -> Dict:
    """Load and parse NPC template markdown file."""
    # Implementation above
    pass
```

---

## Integration with Existing Systems

### 1. Register Handler in KB Service

**File**: `app/services/kb/main.py`

```python
from .handlers.talk import handle_talk

# Add to command router
FAST_PATH_HANDLERS = {
    "collect_item": handle_collect_item,
    "drop_item": handle_drop_item,
    "use_item": handle_use_item,
    "examine": handle_examine,
    "inventory": handle_inventory,
    "give_item": handle_give_item,
    "go": handle_go,
    "talk": handle_talk,  # NEW
}
```

### 2. Command Recognition (Already in game-logic/talk.md)

The LLM in KB Agent will recognize patterns like:
- "talk to Louisa"
- "ask Louisa about dreams"
- "hello Louisa"
- "speak with Woander"

And route to the `talk` command handler.

---

## Data Flow

```
1. PLAYER COMMAND
   Player: "talk to Louisa about the dreams"
   → KB Agent parses intent → routes to talk handler

2. CONTEXT LOADING
   → Load NPC template (louisa.md)
   → Load player-NPC state (trust, history)
   → Load player state (quests, inventory, location)

3. LLM PROMPT CONSTRUCTION
   System Prompt:
     - NPC personality, situation, relationships
     - Player trust level and conversation history
     - Guidelines for authentic responses

   User Message:
     - Player's actual words: "talk to Louisa about the dreams"

4. LLM GENERATION
   → MultiProviderChatService.chat_completion()
   → Claude Sonnet generates authentic Louisa dialogue
   → Response time: ~1-3s

5. STATE UPDATES
   → Add conversation to history
   → Update trust level (+2 for showing interest)
   → Update last_interaction timestamp
   → Increment total_conversations

6. RESPONSE TO PLAYER
   Louisa: *fidgets with her dress, wings drooping*

   The dreams... yes. Neebling has stolen them all and hidden
   them in the shop. Without them, my fairy friends are so listless.
   Would you help me find them?

   [Trust: 52 → 56]
```

---

## Example: Louisa Conversation

### First Meeting (Trust: 50)

```python
# Player: "Hello"
#
# System Prompt includes:
# - Personality: Earnest, anxious, hopeful
# - Situation: Dreams have been stolen, community is sad
# - Trust: 50/100 (neutral)
#
# LLM generates:

"*looks up with wide, hopeful eyes*

Oh! You... you can see me? I wasn't expecting a human to notice
a small fairy like me.

*smooths her teal dress nervously*

I'm Louisa. I've been watching humans come and go through this
shop for quite some time, but I've never had the courage to speak
to one before. You seem kind, though..."
```

### After Accepting Quest (Trust: 68)

```python
# Player: "I'll help you find the dream bottles"
#
# System Prompt includes:
# - Previous conversation context
# - Trust: 68/100 (friendly)
# - Player has active quest
#
# LLM generates:

"*wings flutter with excitement, green glow brightening*

Oh, thank you! Thank you so much!

*clasps tiny hands together*

There are four bottles hidden throughout the shop. Each one
glows with a different color - you'll know them when you see them.
Mystery shimmers turquoise, Energy crackles amber, Joy glows
golden, and Nature flows emerald.

*looks up hopefully*

Just bring them back to me when you find them, and I'll return
the dreams to my community. You're truly kind to help us."
```

---

## Performance Considerations

### Response Time

- **LLM Latency**: ~1-3 seconds (Claude Sonnet)
- **State Loading**: <50ms (local file reads)
- **Total**: ~1-3 seconds end-to-end

**Optimization**: Pre-load NPC templates at startup to reduce file I/O.

### Caching Strategy

```python
# Cache NPC templates (they rarely change)
NPC_TEMPLATE_CACHE = {}

async def _load_npc_template_cached(experience_id: str, npc_id: str) -> Dict:
    """Load NPC template with caching."""
    cache_key = f"{experience_id}:{npc_id}"

    if cache_key not in NPC_TEMPLATE_CACHE:
        NPC_TEMPLATE_CACHE[cache_key] = await _load_npc_template(experience_id, npc_id)

    return NPC_TEMPLATE_CACHE[cache_key]
```

### Streaming Support (Future Enhancement)

```python
async def handle_talk_streaming(
    user_id: str,
    experience_id: str,
    command_data: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """Stream NPC dialogue in real-time (like typing)."""

    # Same setup as handle_talk...

    # Stream from LLM
    async for chunk in llm_service.chat_completion_stream(
        messages=messages,
        model="claude-3-5-sonnet-latest",
        temperature=0.8
    ):
        yield chunk["content"]
```

---

## Testing

### Unit Test Example

```python
async def test_talk_to_louisa():
    """Test basic Louisa conversation."""

    result = await handle_talk(
        user_id="test_user",
        experience_id="wylding-woods",
        command_data={
            "npc_id": "louisa",
            "message": "Hello"
        }
    )

    assert result.success
    assert "louisa" in result.message_to_player.lower()
    assert result.metadata["trust_level"] > 0

    # Verify state updates
    state = result.state_changes["player"]["npcs"]["louisa"]
    assert state["total_conversations"] == 1
    assert len(state["conversation_history"]) == 1
```

### Integration Test with Unity

```bash
# 1. Connect Unity client
# 2. Send talk command via WebSocket
{
  "type": "command",
  "action": "talk",
  "npc_id": "louisa",
  "message": "Hello"
}

# 3. Expect response within 3 seconds
{
  "type": "command_result",
  "success": true,
  "narrative": "*looks up with wide eyes* Oh! You can see me?...",
  "metadata": {
    "trust_level": 52,
    "trust_change": 2
  }
}
```

---

## Future Enhancements

### Phase 2: Quest Integration

- NPCs offer quests based on trust level
- Quest progress affects NPC dialogue
- Completion triggers special dialogue and rewards

### Phase 3: Voice Integration

- Text-to-speech for NPC dialogue
- Voice-to-text for player input
- Regional accents for different NPCs

### Phase 4: Multi-NPC Conversations

- NPCs talk to each other
- Player can facilitate conversations
- Group dynamics and relationships

---

## Summary

✅ **Reuses Existing Infrastructure**: Multi-provider chat service
✅ **Authentic Dialogue**: LLM generates in-character responses
✅ **Context-Aware**: Trust system and conversation history
✅ **Fast Implementation**: ~1 day for MVP
✅ **Scalable**: Same pattern works for any NPC

**Next Steps**:
1. Implement `handle_talk()` handler
2. Add NPC template parsing logic
3. Test with Louisa and Woander
4. Tune prompts for personality consistency
5. Add streaming support for real-time typing effect

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

This document proposes a design for an NPC dialogue system. The verification confirms that this design has **NOT** been implemented.

-   **`talk` Command Handler (`app/services/kb/handlers/talk.py`):** **NOT IMPLEMENTED AS DESIGNED**.
    -   **Evidence:** The existing `handle_talk` function in `app/services/kb/handlers/talk.py` is explicitly labeled as an "MVP KLUDGE". It does not contain any of the proposed logic (NPC proximity validation, template loading, prompt construction, LLM calls, state updates). Instead, it makes an HTTP call to the Chat Service, delegating the entire dialogue generation process.

-   **Helper Functions:** **NOT IMPLEMENTED**.
    -   **Evidence:** The proposed helper functions (`_find_npc_location`, `_load_npc_template`, `_parse_npc_markdown`, `_build_npc_system_prompt`, `_calculate_trust_change`) do not exist in the codebase in the context of the `talk` handler.

**Conclusion:** This document is a design proposal that has not been implemented. The current implementation of the `talk` command is a temporary workaround and does not reflect the architecture described here.
