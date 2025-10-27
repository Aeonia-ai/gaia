# AI Character Integration Architecture

> **Purpose**: Integration between static KB content and dynamic AI character systems
> **Status**: DESIGN PHASE
> **Created**: 2025-10-24
> **Related**:
> - [Experience Platform Overview](./+experiences.md) - Platform architecture
> - [Player Progress Storage](./player-progress-storage.md) - Relationship tracking database
> - [Experience Tools API](./experience-tools-api.md) - Content creation tools
> - Symphony room: `designer` - Multi-agent collaboration discussions

## Executive Summary

This document describes how the GAIA Experience Platform's **static content infrastructure** (KB markdown, PostgreSQL, Redis) integrates with **dynamic AI character systems** (multi-agent AI, emotional modeling, procedural dialogue) to create believable, persistent NPCs that remember players and evolve relationships over time.

**Key Insight**: KB markdown files serve as "character sheets" that constrain and guide AI generation, while our database stores relationship memory that AI agents read to generate contextually appropriate, personalized responses.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DESIGNER CREATES CONTENT                  │
│                  (Experience Tools - Our System)             │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
         ┌─────────────────────────────┐
         │   KB Markdown Files         │
         │   (Character Templates)     │
         │   - Personality traits      │
         │   - Backstory               │
         │   - Spatial location        │
         │   - Communication style     │
         └─────────────┬───────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    ↓                  ↓                  ↓
┌───────────┐  ┌──────────────┐  ┌─────────────────┐
│  Spatial  │  │ Game Master  │  │ SimYou Agent    │
│  Context  │  │    Agent     │  │ (Emotional      │
│  Agent    │  │              │  │  Modeling)      │
└─────┬─────┘  └──────┬───────┘  └────────┬────────┘
      │               │                    │
      └───────────────┼────────────────────┘
                      ↓
         ┌────────────────────────┐
         │   PLAYER INTERACTS     │
         │  (Game Command)        │
         └────────┬───────────────┘
                  ↓
    ┌─────────────────────────────────┐
    │  Game Command Processor         │
    │  (Our System)                   │
    │  - Loads KB character template  │
    │  - Loads relationship from DB   │
    │  - Calls AI agents              │
    │  - Returns structured response  │
    └─────────────┬───────────────────┘
                  ↓
    ┌─────────────────────────────────┐
    │  Player Progress Service        │
    │  (Our System)                   │
    │  - Log interaction event        │
    │  - Update relationship data     │
    │  - Track emotional context      │
    └─────────────┬───────────────────┘
                  ↓
         ┌────────────────────┐
         │   PostgreSQL       │
         │   - player_profiles│
         │   - experience_    │
         │     progress       │
         │   - progress_events│
         └────────────────────┘
```

## Integration Layers

### Layer 1: KB Content as Character Templates

**Character Definition Files**: `/kb/experiences/{experience}/npcs/{character}.md`

```yaml
---
id: luna_fairy_guide
character_type: npc
experience: wylding-woods
---

# Luna - Fairy Guide

> **Character ID**: luna_fairy_guide
> **Role**: Guide
> **Species**: Fairy
> **Age**: 300+ years
> **Location**: Waypoint #1 (Woander Storefront)

## Personality Profile

### Core Traits
- **Playful**: Enjoys wordplay and gentle teasing
- **Wise**: Deep knowledge of forest history and magic
- **Protective**: Fierce defender of the Wylding Woods

### Communication Style
Poetic but practical - speaks in metaphors but gives clear guidance when needed.

### Emotional Baseline
Gentle curiosity with underlying concern for the forest's wellbeing.

## Backstory

Luna has watched over the Wylding Woods for over 300 years. She remembers when humans and magical creatures lived in harmony, before the Great Forgetting. Now she guides those rare individuals who can still perceive the magical realm.

## Appearance

- **Height**: 6 inches
- **Wings**: Translucent with rainbow shimmer
- **Clothing**: Woven flower petals and spider silk
- **Distinctive Feature**: Eyes that shift color based on mood

## Spatial Context

### Primary Location
- **Waypoint**: 1_inter_woander_storefront
- **Appearance Radius**: 50 meters
- **Time of Day**: Most active dawn and dusk

### Movement Patterns
- Stays near Woander storefront during player's first visit
- Can be summoned at other waypoints after trust level > 0.5
- Appears at sacred groves during full moon

## Dialogue Patterns

### First Encounter
"Well hello there! I'm Luna, and I've been watching over this place for quite some time. You seem different from the others who pass through. Are you ready for an adventure?"

### High Trust (> 0.7)
"My dear friend! After everything we've been through together, I knew you'd understand the importance of what I'm about to share..."

### Low Trust (< 0.3)
"You'll have to prove yourself before I share the forest's secrets, traveler. Actions speak louder than words here."

## Quest Hooks

### Initial Quest
**The Disturbance**: Luna senses something wrong in the forest and needs the player's help to investigate.

### Trust-Gated Quest (0.5+)
**Midnight Ritual**: Invitation to sacred ceremony revealing deeper forest mysteries.

### High Trust Quest (0.8+)
**The Guardian's Legacy**: Luna reveals her true purpose and offers to teach ancient magic.
```

**How AI Agents Use This:**

```python
# Game Master Agent reads character template
character_data = await kb_service.load_npc("luna_fairy_guide")

# AI generation constrained by template
ai_prompt = f"""
You are roleplaying {character_data.name}.

Personality: {character_data.personality_traits}
Communication Style: {character_data.communication_style}
Current Context: Player at {current_waypoint}
Relationship: Trust level {trust_level}

Generate dialogue that:
- Matches the personality traits
- Uses the communication style
- Reflects the current trust level
- References the backstory when appropriate
"""
```

`★ Insight ─────────────────────────────────────`
**The KB template is a contract between designer and AI.** Designers define "who" the character is, AI determines "how" they express it in the moment. This prevents AI hallucination while allowing dynamic, contextual responses.
`─────────────────────────────────────────────────`

### Layer 2: Database Stores Relationship Memory

**Three-Table Architecture**: See [Player Progress Storage](./player-progress-storage.md) for complete schema.

#### player_profiles Table
```python
{
  "user_id": "uuid",
  "display_name": "Player Name",
  "stats": {
    "total_npcs_met": 15,
    "total_interactions": 234,
    "reputation": {
      "fairy_faction": 0.73,     # Faction-wide reputation
      "merchant_guild": 0.45,
      "shadow_creatures": -0.32  # Can be negative
    },
    "personality_profile": {
      # SimYou emotional modeling data
      "compassion_score": 0.82,
      "risk_tolerance": 0.65,
      "dialogue_preference": "detailed"  # vs "concise"
    }
  }
}
```

#### experience_progress Table
```python
{
  "user_id": "uuid",
  "experience_id": "wylding-woods",
  "progress_data": {
    "npc_relationships": {
      "luna_fairy_guide": {
        "first_met": "2025-01-15T10:30:00Z",
        "last_interaction": "2025-10-24T15:45:00Z",
        "interaction_count": 47,
        "trust_level": 0.73,  # Range: -1.0 to 1.0

        "shared_experiences": [
          {
            "event": "rescued_lost_sprite",
            "timestamp": "2025-01-20T14:20:00Z",
            "impact": "major",
            "trust_delta": +0.15
          },
          {
            "event": "midnight_ritual",
            "timestamp": "2025-02-14T00:00:00Z",
            "impact": "major",
            "trust_delta": +0.10
          },
          {
            "event": "fought_shadow_creature",
            "timestamp": "2025-03-01T16:30:00Z",
            "impact": "critical",
            "trust_delta": +0.20
          }
        ],

        "emotional_context": {
          "luna_views_player_as": "trusted_friend",
          "player_emotional_pattern": "compassionate_adventurer",
          "recent_topics": [
            "forest_disturbance",
            "ancient_magic",
            "guardian_legacy"
          ],
          "avoided_topics": [],  # Topics player declined to discuss
          "preferred_interaction_style": "collaborative"  # vs "directive" or "passive"
        },

        "dialogue_history": {
          "total_exchanges": 47,
          "avg_response_length": "detailed",
          "player_initiative_ratio": 0.62,  # Player starts 62% of conversations
          "quest_completion_rate": 0.85
        },

        "current_state": {
          "active_quests": ["the_guardian_legacy"],
          "completed_quests": ["the_disturbance", "midnight_ritual"],
          "failed_quests": [],
          "pending_revelations": ["lunas_true_form", "forest_origin_story"]
        }
      },

      "merchant_guild_leader": {
        "first_met": "2025-01-16T11:00:00Z",
        "interaction_count": 12,
        "trust_level": 0.35,
        "relationship_type": "transactional"  # vs "friendship", "romance", "rivalry"
      }
    },

    "faction_standings": {
      "fairy_faction": {
        "reputation": 0.73,
        "rank": "honored_friend",
        "perks_unlocked": ["fairy_sight", "forest_passage"]
      }
    }
  }
}
```

#### player_progress_events Table (Append-Only Log)
```python
{
  "event_id": "uuid",
  "user_id": "uuid",
  "experience_id": "wylding-woods",
  "event_type": "npc_interaction",
  "timestamp": "2025-10-24T15:45:00Z",

  "event_data": {
    "npc_id": "luna_fairy_guide",
    "interaction_type": "dialogue",
    "
_choice": "helped_with_quest",
    "dialogue_exchange": {
      "player_input": "I'll help you investigate the disturbance",
      "npc_response": "Your courage honors the forest. Together we'll find the truth.",
      "emotional_tone": "grateful"
    },
    "trust_delta": +0.05,
    "emotional_tags": ["compassionate", "brave", "committed"],
    "context": {
      "waypoint": "1_inter_woander_storefront",
      "time_of_day": "dusk",
      "player_level": 5,
      "weather": "clear"
    }
  }
}
```

**How AI Agents Read This:**

```python
# Multi-agent collaboration flow
async def generate_npc_response(
    npc_id: str,
    player_command: str,
    user_id: str
):
    # 1. Load static template
    character_template = await kb_service.load_npc(npc_id)

    # 2. Load relationship context
    relationship = await progress_service.get_npc_relationship(
        user_id=user_id,
        npc_id=npc_id
    )

    # 3. Load recent interaction history
    recent_events = await progress_service.get_recent_events(
        user_id=user_id,
        npc_id=npc_id,
        limit=10
    )

    # 4. Hierarchical Memory System (kb-byrne-2's design)
    memory_context = {
        "session_memory": {
            "current_waypoint": current_waypoint,
            "recent_exchanges": recent_events[-3:],  # Last 3 interactions
            "active_quests": relationship.current_state.active_quests
        },
        "working_memory": {
            "relationship_summary": {
                "trust_level": relationship.trust_level,
                "relationship_type": relationship.emotional_context.luna_views_player_as,
                "shared_experiences": relationship.shared_experiences[-5:]  # Last 5
            },
            "player_personality": {
                "emotional_pattern": relationship.emotional_context.player_emotional_pattern,
                "interaction_style": relationship.emotional_context.preferred_interaction_style
            }
        },
        "long_term_memory": {
            "first_encounter": relationship.first_met,
            "total_interactions": relationship.interaction_count,
            "major_events": [e for e in relationship.shared_experiences if e.impact == "critical"]
        }
    }

    # 5. Call AI agents with full context
    ai_response = await ai_character_service.generate_dialogue(
        character_template=character_template,  # KB content
        memory_context=memory_context,          # Our database
        player_command=player_command,
        spatial_context=current_waypoint
    )

    return ai_response
```

### Layer 3: Three-Layer AI Response System

Based on kb-byrne-2's architecture design from Symphony discussion.

#### Immediate Response Layer (0-500ms)
**Purpose**: Acknowledge player action instantly to maintain immersion.

```python
# Quick acknowledgment while AI processes
async def immediate_acknowledgment(player_command: str, npc_id: str):
    # Simple pattern matching for instant feedback
    if "help" in player_command.lower():
        return "Luna's wings flutter with interest..."
    elif "fight" in player_command.lower():
        return "Luna's expression turns serious..."
    else:
        return "Luna considers your words..."
```

**Unity Integration:**
- Display acknowledgment text immediately
- Show NPC "thinking" animation
- Play ambient response sound

#### Narrative Generation Layer (500ms-2s)
**Purpose**: Generate personalized, context-aware dialogue.

```python
# Multi-agent coordination
async def generate_narrative_response(
    character_template: NPCTemplate,
    memory_context: dict,
    player_command: str,
    spatial_context: WaypointContext
):
    # Spatial Context Agent
    spatial_analysis = await spatial_agent.analyze_context(
        waypoint=spatial_context.waypoint_id,
        time_of_day=spatial_context.time,
        ar_environment=spatial_context.detected_objects
    )
    # → "Player at sacred grove, dusk, near ancient tree"

    # SimYou Emotional Modeling Agent
    emotional_state = await simyou_agent.assess_player_state(
        player_command=player_command,
        interaction_history=memory_context.working_memory,
        personality_profile=memory_context.player_personality
    )
    # → "Player showing curiosity and compassion"

    # Game Master Agent
    narrative_response = await game_master_agent.generate_dialogue(
        character=character_template,
        player_emotional_state=emotional_state,
        spatial_context=spatial_analysis,
        relationship_context=memory_context.working_memory,
        player_input=player_command
    )
    # → Generates contextual dialogue matching all constraints

    return narrative_response
```

**Example Output:**
```python
{
  "dialogue": "Luna's eyes shimmer as she notices your genuine concern.
               'The forest speaks to those who truly listen,' she says
               softly, gesturing toward the ancient tree. 'Come, there's
               something I must show you - something only a true friend
               could understand.'",

  "emotional_tone": "warm_trust",
  "trust_delta": +0.03,

  "ar_directives": [
    {"type": "play_audio", "file": "luna_warm_voice.wav"},
    {"type": "facial_expression", "expression": "gentle_smile"},
    {"type": "gesture", "animation": "beckon_toward_tree"},
    {"type": "particle_effect", "effect": "trust_sparkles"}
  ]
}
```

#### World Evolution Layer (Async)
**Purpose**: Update persistent state, create ripple effects, plan future events.

```python
# Runs asynchronously after response delivered
async def evolve_world_state(
    interaction_result: InteractionResult,
    user_id: str,
    npc_id: str
):
    # 1. Log interaction event
    await progress_service.log_event(
        user_id=user_id,
        event_type="npc_interaction",
        event_data={
            "npc_id": npc_id,
            "dialogue_exchange": interaction_result.dialogue,
            "trust_delta": interaction_result.trust_delta,
            "emotional_tags": interaction_result.emotional_tags
        }
    )

    # 2. Update relationship state
    await progress_service.update_relationship(
        user_id=user_id,
        npc_id=npc_id,
        updates={
            "trust_level": f"trust_level + {interaction_result.trust_delta}",
            "interaction_count": "interaction_count + 1",
            "last_interaction": "NOW()"
        }
    )

    # 3. Check for threshold events
    new_trust = await progress_service.get_trust_level(user_id, npc_id)
    if new_trust > 0.7 and not quest_unlocked("guardian_legacy"):
        # Unlock high-trust quest
        await progress_service.unlock_quest(user_id, "guardian_legacy")
        await notification_service.queue_message(
            user_id=user_id,
            message="Luna seems ready to share something important..."
        )

    # 4. Update faction reputation
    if npc_id.startswith("fairy_"):
        await progress_service.update_faction_reputation(
            user_id=user_id,
            faction="fairy_faction",
            delta=interaction_result.trust_delta * 0.5  # Faction rep grows slower
        )

    # 5. Trigger world events
    if interaction_result.significant:
        await world_event_service.create_event(
            event_type="npc_relationship_milestone",
            affected_npcs=[npc_id],
            effect="Other fairies become more friendly toward player"
        )
```

### Layer 4: Game Command Processor Orchestration

**Complete flow when player interacts with NPC:**

```python
@router.post("/game/command")
async def execute_game_command(
    request: GameCommandRequest,
    user: AuthUser = Depends(get_current_user)
):
    # Parse command to detect NPC interaction
    if is_npc_interaction(request.command):
        npc_id = extract_npc_id(request.command, request.experience)

        # === IMMEDIATE RESPONSE (0-500ms) ===
        acknowledgment = generate_immediate_acknowledgment(
            command=request.command,
            npc_id=npc_id
        )

        # Send to client immediately
        await websocket.send_json({
            "type": "immediate_response",
            "text": acknowledgment
        })

        # === NARRATIVE GENERATION (500ms-2s) ===
        # Layer 1: Load KB character template
        character_template = await kb_service.load_npc(npc_id)

        # Layer 2: Load player relationship from database
        relationship = await progress_service.get_npc_relationship(
            user_id=user.id,
            npc_id=npc_id
        )

        recent_events = await progress_service.get_recent_events(
            user_id=user.id,
            npc_id=npc_id,
            limit=10
        )

        # Build memory context
        memory_context = build_memory_context(relationship, recent_events)

        # Get spatial context
        spatial_context = await kb_service.get_waypoint_context(
            waypoint_id=request.session_state.get("current_waypoint")
        )

        # Layer 3: Call multi-agent AI system
        ai_response = await ai_character_service.generate_dialogue(
            character_template=character_template,
            memory_context=memory_context,
            player_command=request.command,
            spatial_context=spatial_context
        )

        # Build structured response
        game_response = GameCommandResponse(
            success=True,
            narrative=ai_response.dialogue,
            actions=[
                {"type": "play_audio", "file": ai_response.voice_file},
                {"type": "facial_expression", "expression": ai_response.expression},
                {"type": "update_trust", "npc_id": npc_id, "delta": ai_response.trust_delta}
            ],
            state_changes={
                f"npc_{npc_id}_last_interaction": datetime.now().isoformat()
            },
            next_suggestions=ai_response.suggested_responses
        )

        # Send to client
        await websocket.send_json({
            "type": "narrative_response",
            "data": game_response.dict()
        })

        # === WORLD EVOLUTION (Async) ===
        # Layer 4: Background updates (don't block response)
        asyncio.create_task(
            evolve_world_state(
                interaction_result=ai_response,
                user_id=user.id,
                npc_id=npc_id
            )
        )

        return game_response
```

## Content Creation Integration

### Designer Creates NPC via Conversational Tools

**See:** [Experience Tools API](./experience-tools-api.md) for complete tool specifications.

```python
# Designer in web chat
"Create a new fairy NPC for Wylding Woods"

     ↓

# LLM detects tool call
KB_TOOLS.create_experience_npc(...)

     ↓

# Multi-turn conversation
LLM: "I'll help create a fairy NPC. What should we call them?"
Designer: "Luna"

LLM: "Great! What personality traits should Luna have?
     (playful, wise, serious, mischievous, protective, etc.)"
Designer: "Playful and wise"

LLM: "Where in Wylding Woods does Luna appear?"
Designer: "At the Woander storefront waypoint"

LLM: "What's Luna's role in the experience?"
Designer: "She's a guide who helps players navigate the magical forest"

LLM: "Should Luna have any special knowledge or backstory?"
Designer: "She's been guarding the forest for 300 years and remembers
          when humans and magical creatures lived together"

     ↓

# LLM calls tool with complete data
create_experience_npc(
    experience="wylding-woods",
    npc_data={
        "id": "luna_fairy_guide",
        "name": "Luna",
        "species": "fairy",
        "personality_traits": ["playful", "wise", "protective"],
        "communication_style": "poetic_but_practical",
        "location": {"waypoint_id": "1_inter_woander_storefront"},
        "role": "guide",
        "backstory": "Guardian of Wylding Woods for 300+ years...",
        "age": "300+",
        "appearance": {
            "height": "6 inches",
            "distinctive_features": "Rainbow shimmer wings"
        }
    }
)

     ↓

# KB Service generates markdown
content = generate_npc_markdown(npc_data)

# Write to KB
file_path = "/kb/experiences/wylding-woods/npcs/luna-fairy-guide.md"
await kb_storage.write_file(file_path, content)

# Git commit
await git_service.commit(
    message="Add Luna fairy guide NPC to Wylding Woods",
    files=[file_path]
)

     ↓

# Auto-sync to production (15 minutes)
# AI agents read new character template
# Luna becomes interactive immediately after sync
```

### Template Learning for Consistency

```python
# Before creating NPC, LLM learns from examples
get_content_template("npc", experience="wylding-woods")

# Returns existing NPC files for structure learning
→ [
    "/kb/experiences/wylding-woods/npcs/forest-sprite.md",
    "/kb/experiences/wylding-woods/npcs/shadow-guardian.md",
    "/kb/experiences/wylding-woods/npcs/ancient-tree-spirit.md"
  ]

# LLM reads examples to understand:
# - Required frontmatter fields
# - Section structure (Personality, Backstory, Appearance)
# - Metadata format
# - Naming conventions

# Generated content matches existing patterns
```

## Cross-Platform Character Persistence

**Same character, different rendering:**

| Client | Character Representation | Data Source |
|--------|-------------------------|-------------|
| **Unity AR** | 3D fairy model with animations | KB template + AI responses |
| **VR (Sanctuary)** | Full-body avatar with gestures | KB template + AI responses |
| **Web UI** | Illustrated portrait + text | KB template + AI responses |
| **Text Client** | Pure dialogue (Zork-style) | KB template + AI responses |

**Shared state across all clients:**
```python
# Player talks to Luna in Unity AR
execute_game_command(
    command="ask Luna about the forest",
    experience="wylding-woods",
    client="unity_ar"
)

# Relationship updated in database
relationship.trust_level += 0.02

# Later, player uses web UI
execute_game_command(
    command="greet Luna",
    experience="wylding-woods",
    client="web_browser"
)

# Luna remembers previous AR interaction
response = "Ah, I was just thinking about our conversation earlier!
            Did you find the sacred grove I mentioned?"
```

## Performance Considerations

### Response Time Targets

| Layer | Target | Strategy |
|-------|--------|----------|
| **Immediate acknowledgment** | < 100ms | Pattern matching, cached responses |
| **Narrative generation** | < 2s | Parallel agent execution, prompt optimization |
| **World evolution** | Async | Background tasks, don't block response |
| **Memory retrieval** | < 50ms | Redis caching, indexed JSONB queries |

### Caching Strategy

```python
# Cache character templates (rarely change)
@cache(ttl=3600)  # 1 hour
async def load_npc_template(npc_id: str):
    return await kb_service.load_npc(npc_id)

# Cache relationship summaries (moderate change rate)
@cache(ttl=300)  # 5 minutes
async def get_relationship_summary(user_id: str, npc_id: str):
    return await progress_service.get_npc_relationship(user_id, npc_id)

# Don't cache immediate interactions (always fresh)
async def log_interaction_event(user_id: str, event_data: dict):
    # Direct write, no cache
    return await progress_service.log_event(user_id, event_data)
```

### Database Query Optimization

```sql
-- Indexed JSONB queries for fast relationship lookups
CREATE INDEX idx_experience_progress_npc_relationships
ON experience_progress USING GIN ((progress_data->'npc_relationships'));

-- Composite index for recent events
CREATE INDEX idx_progress_events_user_npc_time
ON player_progress_events (user_id, (event_data->>'npc_id'), timestamp DESC);

-- Partial index for active relationships
CREATE INDEX idx_active_relationships
ON experience_progress ((progress_data->'npc_relationships'))
WHERE (progress_data->'npc_relationships') IS NOT NULL;
```

## Implementation Roadmap

### Phase 1: Static Character Content (Week 1)
- [ ] Design NPC markdown schema
- [ ] Create `create_experience_npc` tool
- [ ] Implement template learning from existing NPCs
- [ ] Add NPC directory to KB structure
- [ ] Demo: Create Luna through conversation

### Phase 2: Relationship Tracking (Week 2)
- [ ] Add `npc_relationships` JSONB field to `experience_progress`
- [ ] Implement trust level calculations
- [ ] Add interaction event logging
- [ ] Build relationship query endpoints
- [ ] Demo: Track Luna interactions, show trust growth

### Phase 3: AI Agent Integration (Week 3-4)
- [ ] Define AI agent interface contracts
- [ ] Implement immediate acknowledgment layer
- [ ] Build memory context loading
- [ ] Integrate multi-agent orchestration
- [ ] Demo: Luna responds with personality + memory

### Phase 4: World Evolution (Week 5)
- [ ] Implement async state updates
- [ ] Add quest unlocking based on trust thresholds
- [ ] Build faction reputation system
- [ ] Create world event triggers
- [ ] Demo: Luna unlocks secret quest at high trust

### Phase 5: Cross-Platform Support (Week 6+)
- [ ] Define client-agnostic response format
- [ ] Build platform-specific renderers
- [ ] Test consistency across Unity/VR/Web
- [ ] Add voice synthesis integration
- [ ] Demo: Same Luna conversation across all clients

## Testing Strategy

### Unit Tests
```python
# Test character template loading
async def test_load_npc_template():
    template = await kb_service.load_npc("luna_fairy_guide")
    assert template.personality_traits == ["playful", "wise", "protective"]
    assert template.communication_style == "poetic_but_practical"

# Test relationship updates
async def test_update_trust_level():
    await progress_service.update_trust(
        user_id="test-user",
        npc_id="luna_fairy_guide",
        delta=0.05
    )
    relationship = await progress_service.get_npc_relationship(
        "test-user", "luna_fairy_guide"
    )
    assert relationship.trust_level == 0.05

# Test memory context building
async def test_memory_context_structure():
    context = await build_memory_context(relationship, recent_events)
    assert "session_memory" in context
    assert "working_memory" in context
    assert "long_term_memory" in context
```

### Integration Tests
```python
# Test complete interaction flow
async def test_npc_interaction_flow():
    response = await execute_game_command(
        command="greet Luna",
        experience="wylding-woods",
        user_id="test-user"
    )

    # Check immediate response
    assert response.success is True
    assert "Luna" in response.narrative

    # Check relationship updated
    relationship = await progress_service.get_npc_relationship(
        "test-user", "luna_fairy_guide"
    )
    assert relationship.interaction_count == 1

    # Check event logged
    events = await progress_service.get_recent_events(
        "test-user", "luna_fairy_guide"
    )
    assert len(events) == 1
    assert events[0].event_type == "npc_interaction"
```

### Load Tests
```python
# Test concurrent NPC interactions
async def test_concurrent_interactions():
    # Simulate 100 players talking to Luna simultaneously
    tasks = [
        execute_game_command(
            command="greet Luna",
            experience="wylding-woods",
            user_id=f"user-{i}"
        )
        for i in range(100)
    ]

    responses = await asyncio.gather(*tasks)

    # All responses should succeed
    assert all(r.success for r in responses)

    # All responses should be personalized
    assert len(set(r.narrative for r in responses)) > 1  # Not all identical

    # Response times under target
    assert all(r.processing_time_ms < 2000 for r in responses)
```

## Security & Privacy Considerations

### Data Privacy
- **Player emotional profiles**: Stored locally on-device (SimYou agent)
- **Interaction history**: User owns data, can request deletion
- **Cross-player isolation**: No player can see another's NPC relationships

### Content Moderation
- **AI response filtering**: Inappropriate content detection
- **Designer review**: High-trust content requires approval
- **Player reporting**: Flag problematic NPC behavior

### RBAC Integration
```python
# Only designers can create NPCs
@require_role("designer")
async def create_experience_npc(...):
    pass

# Players can view NPC templates (read-only)
@require_role("player")
async def get_npc_info(npc_id: str):
    # Return sanitized template (no internal metadata)
    return await kb_service.load_npc(npc_id, sanitized=True)

# Admins can modify existing NPCs
@require_role("admin")
async def update_npc_template(npc_id: str, updates: dict):
    pass
```

## Related Documentation

### Experience Platform
- [Experience Platform Overview](./+experiences.md) - Architecture overview
- [Player Progress Storage](./player-progress-storage.md) - Database design
- [Experience Tools API](./experience-tools-api.md) - Content creation tools
- [Experience Data Models](./experience-data-models.md) - SQLAlchemy schemas

### Game Systems
- [Game Command Developer Guide](../../api/game-command-developer-guide.md) - Runtime execution
- [KB-Driven Command Processing Spec](../../api/kb-driven-command-processing-spec.md) - Complete spec

### Infrastructure
- [Database Architecture](../database/database-architecture.md) - Hybrid PostgreSQL + Redis
- [KB Architecture Guide](../../kb/developer/kb-architecture-guide.md) - KB infrastructure

---

## Summary

The AI Character Integration Architecture creates **believable, persistent NPCs** by combining:

1. **Static KB Templates** - Designers define personality, backstory, appearance
2. **Dynamic AI Generation** - Multi-agent system generates contextual responses
3. **Relationship Memory** - PostgreSQL stores trust, history, emotional context
4. **Cross-Platform Consistency** - Same character across Unity/VR/Web/Text

**Key Innovation**: NPCs that truly remember you, evolve relationships over time, and respond authentically to your emotional state while maintaining designer-defined personality boundaries.

**Status**: Design phase complete, ready for Phase 1 implementation (static character content).
