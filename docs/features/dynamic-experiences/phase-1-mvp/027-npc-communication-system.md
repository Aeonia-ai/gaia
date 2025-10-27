# NPC Communication System

## Status: ✅ **COMPLETE**

The NPC communication system provides memory-aware dialogue with NPCs using a three-layer architecture that stores personality (templates), world state (instances), and personal relationships (per-player memory).

---

## Quick Start

### Talk to an NPC

```bash
# Simple greeting
curl -X POST http://localhost:8001/game/command \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "command": "Hello Louisa",
    "experience": "wylding-woods",
    "user_context": {
      "user_id": "jason@aeonia.ai",
      "waypoint": "waypoint_28a",
      "sublocation": "fairy_door_1",
      "role": "player"
    }
  }'

# Ask about quest
curl -X POST http://localhost:8001/game/command \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{
    "command": "Ask Louisa about the dream bottles",
    "experience": "wylding-woods",
    "user_context": {
      "user_id": "jason@aeonia.ai",
      "waypoint": "waypoint_28a",
      "sublocation": "fairy_door_1",
      "role": "player"
    }
  }'
```

### Response Format

```json
{
  "success": true,
  "narrative": "*with a soft, slightly nervous but warm tone* Oh! You... you can see me? I wasn't expecting a human to notice.",
  "actions": [{
    "type": "npc_dialogue",
    "npc": "louisa",
    "mood": "anxious"
  }],
  "state_changes": {
    "relationship": {
      "npc": "louisa",
      "trust": 52,
      "conversations": 1
    }
  }
}
```

---

## Architecture

### Three-Layer Memory System

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: NPC Templates (Personality & Knowledge)           │
│  File: /kb/experiences/{exp}/templates/npcs/{npc}.md        │
│  Contains: Personality traits, voice, knowledge, dialogue   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: NPC Instances (World State)                       │
│  File: /kb/experiences/{exp}/instances/npcs/{npc}_1.json    │
│  Contains: Location, mood, quest status, events witnessed   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Player-NPC Relationships (Personal Memory)        │
│  File: /kb/experiences/{exp}/players/{user}/npcs/{npc}.json │
│  Contains: Conversation history, trust, facts learned       │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1: NPC Templates

**File**: `/kb/experiences/wylding-woods/templates/npcs/louisa.md`

This is a **markdown file** that defines the NPC's personality and knowledge. The entire file is fed to the LLM as context.

### Template Structure

```markdown
# Louisa

> **NPC ID**: louisa
> **Type**: fairy
> **Role**: quest_giver

## Personality
- **Earnest & Hopeful**: Deep-seated belief in the good of others
- **Anxious Guardian**: Self-appointed caretaker of her community's dreams
- **Slightly Formal & Old-Fashioned**: Polite speech with archaic whimsy

## Current Situation
Neebling has stolen her community's dreams and bottled them up.
She needs help retrieving the dream bottles scattered around the clearing.

## Interaction Guidelines
- **Natural conversation**: Responds to what the player actually says
- **Emotional authenticity**: Anxiety shows when discussing stolen dreams
- **Story emerges organically**: Doesn't rush to explain entire quest

## Quest: Dream Bottle Recovery
**Objective**: Find 4 dream bottles and return them to matching fairy houses
- Spiral bottle → Spiral house (fairy_door_1)
- Star bottle → Star house (fairy_door_2)
- Moon bottle → Moon house (fairy_door_3)
- Sun bottle → Sun house (fairy_door_4)
```

**Benefits:**
- Rich personality definition
- Easy to author (just markdown)
- Version controlled with Git
- Can be edited by content creators without code changes

---

## Layer 2: NPC Instances

**File**: `/kb/experiences/wylding-woods/instances/npcs/louisa_1.json`

This is a **JSON file** that tracks the NPC's current state in the world.

```json
{
  "instance_id": 1,
  "template": "louisa",
  "semantic_name": "louisa",
  "location": "waypoint_28a",
  "sublocation": "fairy_door_1",
  "state": {
    "emotional_state": "anxious",
    "quest_given": false,
    "bottles_returned": 0,
    "player_relationship": "stranger"
  },
  "metadata": {
    "created_at": "2025-10-26T18:00:00Z",
    "last_modified": "2025-10-26T18:00:00Z",
    "_version": 1
  }
}
```

**What It Tracks:**
- Current location (can move NPCs by editing this)
- Emotional state (affects dialogue tone)
- Quest status (shared across all players)
- World events (what the NPC has witnessed)

**Note:** This is shared state - all players see the same NPC mood and quest progress.

---

## Layer 3: Player-NPC Relationships

**File**: `/kb/experiences/wylding-woods/players/jason@aeonia.ai/npcs/louisa.json`

This is a **JSON file** created automatically on first conversation. It stores personal memory between this specific player and this NPC.

```json
{
  "npc_template": "louisa",
  "player_id": "jason@aeonia.ai",
  "first_met": "2025-10-27T17:30:00Z",
  "last_interaction": "2025-10-27T17:35:00Z",
  "total_conversations": 5,
  "trust_level": 60,

  "conversation_history": [
    {
      "timestamp": "2025-10-27T17:30:00Z",
      "player": "Hello Louisa",
      "npc": "Oh! You can see me? I wasn't expecting a human to notice.",
      "mood": "anxious"
    },
    {
      "timestamp": "2025-10-27T17:32:00Z",
      "player": "What's wrong?",
      "npc": "My community's dreams have been stolen. I'm so worried about them.",
      "mood": "concerned"
    }
  ],

  "facts_learned": [],
  "promises": [],

  "metadata": {
    "created_at": "2025-10-27T17:30:00Z",
    "last_modified": "2025-10-27T17:35:00Z",
    "_version": 5
  }
}
```

**What It Tracks:**
- Last 20 conversations (older ones are removed)
- Trust level (0-100, starts at 50)
- When you first met
- Facts the NPC learned about you
- Promises made between you

**Privacy:** Each player has their own relationship file - NPCs remember each player differently.

---

## How It Works

### Conversation Flow

```
1. Player sends: "Hello Louisa, can you help me?"
                     ↓
2. System finds NPC at player's location
                     ↓
3. Load 3 layers:
   - Template (personality from louisa.md)
   - Instance (current mood: "anxious")
   - Relationship (trust: 52, last 3 conversations)
                     ↓
4. Build LLM prompt with all context:
   """
   You are Louisa, a fairy Dream Weaver.

   PERSONALITY: Earnest, hopeful, anxious, formal
   CURRENT MOOD: anxious
   SITUATION: Dreams have been stolen

   RELATIONSHIP WITH PLAYER:
   Trust: 52/100
   Total Conversations: 1
   History: (This is your first conversation)

   PLAYER SAYS: "Hello Louisa, can you help me?"

   Respond in character, naturally and authentically.
   """
                     ↓
5. LLM generates response in character
                     ↓
6. Update relationship:
   - Add conversation to history
   - Increment total_conversations
   - Increase trust by +2
                     ↓
7. Save relationship file atomically
                     ↓
8. Return response to player
```

### Memory Management

**Short-Term Memory (Conversation Window):**
- Keeps last 20 conversations
- Older conversations are dropped (can be summarized in future)
- Provides immediate context for natural dialogue

**Long-Term Memory (Facts & Trust):**
- Trust level persists forever
- Facts learned about player stored separately
- Can be expanded with semantic search in future

---

## Natural Language Commands

The system understands multiple ways to talk to NPCs:

```bash
# Direct greeting
"Hello Louisa"
"Hi Louisa"
"Hey Louisa"

# Formal address
"Talk to Louisa"
"Speak with Louisa"

# Questions
"Ask Louisa about the dream bottles"
"Ask Louisa what happened"
"Can you help me, Louisa?"

# Contextual
"Louisa, I found a dream bottle"
"Louisa, are you okay?"
```

All of these will be parsed as "talk" actions with Louisa as the target.

---

## Relationship Dynamics

### Trust System

**Trust Level:** 0-100 scale
- **0-30**: Wary, guarded responses
- **30-60**: Neutral, polite
- **60-80**: Friendly, helpful
- **80-100**: Close friend, shares secrets

**Trust Changes:**
- +2 for any meaningful conversation (>5 characters)
- +5 for helpful actions (completing quests)
- +10 for keeping promises
- -5 for rude responses
- -20 for breaking promises

**Current Implementation:** Simple +2 per conversation (MVP)

### Conversation Count

Tracks total number of interactions:
- Affects how NPC greets you
- "Oh, you're back!" vs "Hello stranger"
- Can unlock special dialogue after X conversations

---

## Testing NPC Communication

### Test Script

```python
#!/usr/bin/env python3
"""Test NPC conversation"""
import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "your-api-key"

def talk_to_npc(message):
    payload = {
        "command": message,
        "experience": "wylding-woods",
        "user_context": {
            "user_id": "test@example.com",
            "waypoint": "waypoint_28a",
            "sublocation": "fairy_door_1",
            "role": "player"
        }
    }

    response = requests.post(
        f"{BASE_URL}/game/command",
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
        json=payload
    )

    result = response.json()
    print(f"You: {message}")
    print(f"Louisa: {result['narrative']}")
    if 'state_changes' in result:
        rel = result['state_changes'].get('relationship', {})
        print(f"Trust: {rel.get('trust')}/100, Conversations: {rel.get('conversations')}")
    print()

# Test conversation
talk_to_npc("Hello Louisa")
talk_to_npc("What's troubling you?")
talk_to_npc("I can help find the dream bottles")
```

### Expected Output

```
You: Hello Louisa
Louisa: *with a soft, slightly nervous but warm tone* Oh! You... you can see me?
Trust: 52/100, Conversations: 1

You: What's troubling you?
Louisa: My community's dreams have been stolen by Neebling. Without their dreams, my friends are listless and sad.
Trust: 54/100, Conversations: 2

You: I can help find the dream bottles
Louisa: *eyes brighten with hope* You would help us? That's... that's very kind of you. The bottles are scattered around the clearing.
Trust: 56/100, Conversations: 3
```

---

## Performance

**Response Times:**
- Template load: <10ms (markdown file read)
- Instance load: <10ms (small JSON file)
- Relationship load/create: <20ms (JSON file or new creation)
- LLM generation: 1-2 seconds
- Relationship save: <20ms (atomic write)

**Total: ~1-2 seconds** for complete conversation

**Scalability:**
- MVP (file-based): 1-10 concurrent players ✅
- Phase 2 (PostgreSQL): 100+ concurrent players
- Phase 3 (vector search): Semantic memory retrieval

---

## Advanced Features (Future)

### Semantic Memory Search
```python
# Player asks: "Do you remember when we talked about dreams?"
# System:
# 1. Generate embedding for question
# 2. Search past conversations by semantic similarity
# 3. Return most relevant memories
# 4. Include in LLM context
```

### Cross-NPC Knowledge
```python
# Louisa tells player about Neebling
# Later, player talks to Neebling
# Neebling already knows player has been helping Louisa (gossip system)
```

### Emotion Detection
```python
# Detect player emotion from message
# Adjust NPC response accordingly
# "I'm so frustrated!" → NPC shows sympathy
# "This is amazing!" → NPC shares excitement
```

### Dynamic Relationships
```python
# NPCs have relationships with each other
# Helping one NPC may affect relationship with their rival
# Complex social dynamics emerge
```

---

## File Locations

### Templates (Personality)
```
/kb/experiences/{experience}/templates/npcs/{npc_name}.md
```
**Created by**: Content creators/designers
**Contains**: Personality, knowledge, dialogue guidelines
**Format**: Markdown

### Instances (World State)
```
/kb/experiences/{experience}/instances/npcs/{npc_name}_1.json
```
**Created by**: Initial world setup
**Contains**: Location, mood, quest status
**Format**: JSON

### Relationships (Player Memory)
```
/kb/experiences/{experience}/players/{user_id}/npcs/{npc_name}.json
```
**Created by**: Automatically on first conversation
**Contains**: Conversation history, trust, facts
**Format**: JSON

---

## Troubleshooting

### NPC Not Found
```
Error: "You don't see louisa nearby"
```
**Cause**: NPC not at player's location
**Fix**: Check NPC instance location matches player's waypoint/sublocation

### No Response
```
Error: "Something went wrong while talking to louisa"
```
**Cause**: Template file missing or LLM error
**Fix**: Check `/kb/experiences/wylding-woods/templates/npcs/louisa.md` exists

### Conversation Not Saved
**Cause**: Permissions issue on player directory
**Fix**: Ensure `/kb/experiences/wylding-woods/players/` is writable

---

## Best Practices

### Creating New NPCs

1. **Create template** (`templates/npcs/name.md`):
   - Define personality traits
   - Write interaction guidelines
   - Include current situation/motivations

2. **Create instance** (`instances/npcs/name_1.json`):
   - Set location
   - Set initial emotional state
   - Add to manifest

3. **Test conversation**:
   - Talk to NPC from different angles
   - Verify personality comes through
   - Check relationship tracking works

### Writing Good NPC Templates

✅ **Do:**
- Write rich personality descriptions
- Include specific voice/speech patterns
- Define what they know and don't know
- Give clear interaction guidelines
- Include current emotional state

❌ **Don't:**
- Write scripted dialogue trees
- Make them omniscient
- Give contradictory personality traits
- Forget to define their role in the world

### Managing Memory

- Keep last 20 conversations (enough for context)
- Store important facts separately
- Trust level is the key long-term metric
- Conversation count adds flavor

---

## Summary

The NPC communication system provides:

✅ **Memory-Aware Dialogue** - NPCs remember conversations
✅ **Personality Consistency** - LLM follows template personality
✅ **Relationship Tracking** - Trust builds over time
✅ **Natural Language** - Flexible conversation commands
✅ **File-Based Storage** - Easy to author, version controlled
✅ **Atomic Operations** - No corruption risk
✅ **Per-Player Memory** - Each player's relationship is unique

**Ready for production at MVP scale (1-10 players)!** 🎮
