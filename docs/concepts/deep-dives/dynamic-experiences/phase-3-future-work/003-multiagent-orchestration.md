# Multiagent Orchestration in Gaia

## Overview

Gaia implements sophisticated multiagent orchestration using the mcp-agent framework to enable complex AI coordination patterns for MMOIRL (Massively Multiplayer Online In Real Life) gaming experiences. This system goes beyond single-agent chat to create rich, coordinated interactions between multiple specialized AI agents.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    MULTIAGENT ORCHESTRATOR                     │
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────────────────────┐   │
│  │   USER INPUT    │───▶│    SCENARIO DETECTOR             │   │
│  │                 │    │ - Analyzes message content       │   │
│  │ "A hooded       │    │ - Routes to appropriate team     │   │
│  │  figure enters  │    │ - gamemaster/worldbuilding/etc   │   │
│  │  tavern..."     │    └──────────────────────────────────┘   │
│  └─────────────────┘                    │                      │
│                                         ▼                      │
│  ┌─────────────────────────────────────────────────────────────┤
│  │               ORCHESTRATOR PATTERN                          │
│  │                                                             │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  │   PLANNER    │  │   EXECUTOR   │  │  SYNTHESIZER │      │
│  │  │              │  │              │  │              │      │
│  │  │ - Breaks     │  │ - Runs       │  │ - Combines   │      │
│  │  │   down task  │  │   agents in  │  │   all agent  │      │
│  │  │ - Assigns    │  │   parallel   │  │   outputs    │      │
│  │  │   to agents  │  │ - Manages    │  │ - Creates    │      │
│  │  │              │  │   execution  │  │   final      │      │
│  │  └──────────────┘  └──────────────┘  │   response   │      │
│  │         │                    │       └──────────────┘      │
│  │         ▼                    ▼                │            │
│  │  ┌──────────────────────────────────────────┐ │            │
│  │  │           AGENT TEAMS                    │ │            │
│  │  └──────────────────────────────────────────┘ │            │
│  └─────────────────────────────────────────────────┼────────────┘
│                                                    ▼
├─────────────────────────────────────────────────────────────────┤
│                     AGENT TEAMS                                 │
│                                                                 │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐     │
│ │  GAMEMASTER     │ │ WORLDBUILDING   │ │  STORYTELLING   │     │
│ │                 │ │                 │ │                 │     │
│ │ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │     │
│ │ │ Bartender   │ │ │ │ Geography   │ │ │ │ Hero        │ │     │
│ │ │ Agent       │ │ │ │ Specialist  │ │ │ │ Narrator    │ │     │
│ │ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │     │
│ │ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │     │
│ │ │ Musician    │ │ │ │ Culture     │ │ │ │ Villain     │ │     │
│ │ │ Agent       │ │ │ │ Specialist  │ │ │ │ Narrator    │ │     │
│ │ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │     │
│ │ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │     │
│ │ │ Merchant    │ │ │ │ History     │ │ │ │ Commoner    │ │     │
│ │ │ Agent       │ │ │ │ Specialist  │ │ │ │ Narrator    │ │     │
│ │ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │     │
│ │ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │     │
│ │ │ Guard       │ │ │ │ Economics   │ │ │ │ Scholar     │ │     │
│ │ │ Agent       │ │ │ │ Specialist  │ │ │ │ Narrator    │ │     │
│ │ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │     │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘     │
│                                                                 │
│ ┌─────────────────┐                                             │
│ │ PROBLEMSOLVING  │                                             │
│ │                 │                                             │
│ │ ┌─────────────┐ │                                             │
│ │ │ Game Design │ │                                             │
│ │ │ Expert      │ │                                             │
│ │ └─────────────┘ │                                             │
│ │ ┌─────────────┐ │                                             │
│ │ │ Technical   │ │                                             │
│ │ │ Expert      │ │                                             │
│ │ └─────────────┘ │                                             │
│ │ ┌─────────────┐ │                                             │
│ │ │ Narrative   │ │                                             │
│ │ │ Expert      │ │                                             │
│ │ └─────────────┘ │                                             │
│ │ ┌─────────────┐ │                                             │
│ │ │ Psychology  │ │                                             │
│ │ │ Expert      │ │                                             │
│ │ └─────────────┘ │                                             │
│ └─────────────────┘                                             │
└─────────────────────────────────────────────────────────────────┘
```

### Technical Implementation

**Core Service**: `app/services/chat/multiagent_orchestrator.py`

```python
class MMOIRLMultiagentOrchestrator:
    """Advanced multiagent orchestration service for MMOIRL scenarios"""
    
    def __init__(self):
        self.app = MCPApp(name="gaia_mmoirl_multiagent")
        self.session_orchestrators: Dict[str, Any] = {}
    
    async def process_multiagent_request(
        self,
        request: ChatRequest,
        auth_principal: Dict[str, Any],
        scenario_type: str = "auto"
    ) -> Dict[str, Any]:
        # 1. Detect scenario type from message content
        # 2. Create appropriate specialist agent team
        # 3. Use Orchestrator pattern for coordination
        # 4. Return synthesized response
```

## Multiagent Scenarios

### 1. Game Master Orchestration (`/api/v1/chat/gamemaster`)

**Purpose**: Coordinate multiple NPCs for immersive interactive scenes

**Agent Team**:
- **Tavern Bartender** (Grimjaw): Gruff, knows local gossip and rumors
- **Elvish Musician** (Lyralei): Poetic, ancient lore and legends
- **Merchant Patron** (Marcus): Well-traveled, political insider knowledge
- **City Guard** (Captain Elena): Authority figure, law enforcement knowledge

**Example Input**: "A hooded figure enters the tavern and asks about missing merchants"

**Agent Outputs**:
```
BARTENDER (Grimjaw):
"*wipes down mug with dirty rag* 
Missing merchants, eh? Aye, heard whispers about that. Northern road's been 
dangerous lately - bandits or worse. But information like that... *taps bar* 
...comes with a price. What's it worth to ya?"

MUSICIAN (Lyralei):
"*pauses mid-song, elvish eyes gleaming*
🎵 'Three wagons rolled at dawn's first light,
   But none returned by fall of night...' 🎵
I sing of what the wind whispers, stranger. The old songs speak of cursed 
paths where gold turns to dust..."

MERCHANT (Marcus):
"*leans in conspiratorially*
Your brother, you say? Marcus knows every guard on every route. If he was 
with Aldric's caravan... *shakes head grimly* That route's been hit three 
times this month. Someone's got inside information."

GUARD (Captain Elena):
"*straightens in chair, official tone*
You're asking about an active investigation. I can't share details, but... 
*glances around* Meet me by the old mill at midnight if you truly seek 
justice, not just revenge."
```

**Orchestrator Result**: Unified tavern scene where all NPCs respond naturally to create a living world experience.

### 2. Collaborative World Building (`/api/v1/chat/worldbuilding`)

**Purpose**: Create rich, detailed game world content through expert collaboration

**Agent Team**:
- **Geography Specialist**: Landscapes, climate, terrain, natural resources
- **Culture Specialist**: Civilizations, customs, social structures, religions  
- **History Specialist**: Timelines, events, conflicts, legends, current tensions
- **Economics Specialist**: Trade networks, resources, markets, economic systems

**Example Input**: "Create a new fantasy region called The Crimson Reaches"

**Agent Outputs**:
```
GEOGRAPHY SPECIALIST:
"The Crimson Reaches span 200 miles of red sandstone canyons and mesas, 
where ancient magical storms left crystalline formations. Three major rivers 
converge here: the Ironflow (rich in minerals), the Whisperbrook (pure 
mountain water), and the Bloodtide (tainted by old magic).

Climate: Arid days, cold nights. Seasonal magical storms. Rich iron and 
crystal deposits make it valuable but dangerous..."

CULTURE SPECIALIST:
"Three main peoples inhabit the Reaches:
- The Stoneshapers: Dwarven-descended miners adapted to desert life
- The Windwalkers: Nomadic tribes following magical storm patterns  
- The Frontier Towns: Mixed settlements of prospectors and traders

The Stoneshapers worship the Deep Forge, believing crystals are gods' tears. 
Windwalkers see storms as ancestral spirits. Constant tension over mining 
rights vs sacred sites..."

HISTORY SPECIALIST:
"500 years ago, the Great Sundering cracked the earth here, releasing wild 
magic that turned the stone red. The last Arcanum wars ended with the 
Crimson Compact - a treaty limiting magical exploitation.

Recent events: Discovery of 'singing crystals' has broken old treaties. 
The mining rush brought new conflicts. Ancient guardians awakening..."

ECONOMICS SPECIALIST:
"Primary exports: Iron ore, magical crystals, rare desert herbs
Trade routes: Three major caravan paths converge at Redrock Crossing
Currency: Iron tokens backed by the Miners' Guild

Economic tensions: Crystal mining vs traditional iron work, outside 
corporations vs local guilds, water rights disputes..."
```

**Orchestrator Result**: Comprehensive region design that integrates all specialist perspectives into a cohesive, playable world area.

### 3. Multi-Perspective Storytelling (`/api/v1/chat/storytelling`)

**Purpose**: Generate rich, layered narratives from multiple viewpoints

**Agent Team**:
- **Hero Narrator**: Courage, justice, moral choices, sacrifice
- **Villain Narrator**: Complex motivations, tragic backstory, twisted logic
- **Commoner Narrator**: Survival-focused, practical concerns, daily impact
- **Scholar Narrator**: Academic analysis, historical patterns, long-term view

**Example Input**: "Tell the story of a powerful artifact discovery from multiple perspectives"

**Agent Outputs**:
```
HERO NARRATOR:
"Sir Aldric knew the moment he saw the Sunward Crown that innocent lives 
hung in the balance. The artifact's power could save the plague-stricken 
villages, but only if he could resist its whispered promises of personal 
glory. With trembling hands, he chose duty over desire..."

VILLAIN NARRATOR:
"They called me villain, but who among them understood true loss? When the 
Crown spoke to me in my daughter's voice - the daughter their 'noble' war 
had taken - how could I not listen? If using its power makes me monster, 
then I embrace monstrosity for love..."

COMMONER NARRATOR:
"All we wanted was to work our fields in peace. Then the lords came with 
their magical crown and their grand quests. But while they fought over 
ancient power, our children still went hungry. Magic don't put bread on 
the table..."

SCHOLAR NARRATOR:
"The Sunward Crown represents the classic pattern of concentrated power 
corrupting those who wield it. Historical precedent suggests artifacts of 
this magnitude inevitably lead to societal upheaval - the Crown Wars of 
the Third Age being the most relevant example..."
```

**Orchestrator Result**: Multi-layered narrative showing how the same events are perceived differently based on perspective and experience.

### 4. Expert Problem Solving (`/api/v1/chat/problemsolving`)

**Purpose**: Collaborative analysis of complex challenges requiring multiple expertise areas

**Agent Team**:
- **Game Design Expert**: Player engagement, balance, progression, fun factor
- **Technical Expert**: Performance, scalability, networking, implementation
- **Narrative Expert**: Story integration, character development, meaningful choices
- **Psychology Expert**: Player behavior, social dynamics, psychological engagement

**Example Input**: "Design a complex multiplayer puzzle for 6-8 players called The Resonance Chamber"

**Agent Outputs**:
```
GAME DESIGN EXPERT:
"The Resonance Chamber should require 6-8 players with asymmetric roles:
- 2 Frequency Controllers (set crystal resonance)
- 2 Amplitude Modulators (control power levels)
- 2 Timing Coordinators (synchronize pulses)
- 1-2 Directors (coordinate overall strategy)

Success requires precise teamwork - no single player can solve it alone. 
Include backup mechanics for when teams get stuck..."

TECHNICAL EXPERT:
"Real-time synchronization requirements:
- Sub-100ms latency for frequency adjustments
- State validation every 50ms to prevent desync
- Graceful degradation if players disconnect mid-puzzle
- Visual feedback systems to show resonance states

Implementation: WebSocket connections with heartbeat monitoring, 
client-side prediction with server authority..."

NARRATIVE EXPERT:
"The Chamber houses an ancient AI that speaks in musical patterns. 
Players must 'sing' to it in harmony to unlock deeper chambers. 
Each player discovers fragments of the AI's tragic history - 
it was once the conductor of a great orchestra, now seeking 
to recreate its lost symphony..."

PSYCHOLOGY EXPERT:
"Team dynamics considerations:
- Natural leaders will emerge - design roles that support this
- Include 'follower' roles that are engaging, not just passive
- Communication is key - require voice coordination
- Failure states should encourage regrouping, not blame
- Victory should feel earned by the entire team..."
```

**Orchestrator Result**: Comprehensive design solution that incorporates insights from all expert domains.

## API Endpoints

### Enhanced MCP-Agent Endpoint

**`POST /api/v1/chat/mcp-agent`**
- **Description**: Enhanced with automatic multiagent orchestration
- **Behavior**: Analyzes incoming messages and routes to appropriate agent teams
- **Scenarios**: Auto-detects gamemaster, worldbuilding, storytelling, or problemsolving needs

### Specific Scenario Endpoints

**`POST /api/v1/chat/gamemaster`**
- **Description**: Game Master orchestrating multiple NPCs
- **Use Case**: Interactive scenes, character dialogues, immersive world interactions

**`POST /api/v1/chat/worldbuilding`** 
- **Description**: Collaborative world building with specialist agents
- **Use Case**: Creating regions, cities, cultures, histories for game worlds

**`POST /api/v1/chat/storytelling`**
- **Description**: Multi-perspective storytelling 
- **Use Case**: Rich narratives, character backstories, event descriptions

**`POST /api/v1/chat/problemsolving`**
- **Description**: Expert team collaboration for complex challenges
- **Use Case**: Game design problems, technical challenges, complex puzzles

### Request Format

```json
{
  "message": "Your request or scenario description",
  "model": "claude-sonnet-4-5",
  "persona": "optional_persona_context"
}
```

### Response Format

```json
{
  "id": "multiagent-{user_id}-{timestamp}",
  "object": "chat.completion", 
  "created": 1234567890,
  "model": "claude-sonnet-4-5",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Orchestrated response from multiple agents..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 800,
    "total_tokens": 950
  },
  "_multiagent": {
    "scenario_type": "gamemaster",
    "orchestrator": "tavern_game_master", 
    "agent_count": 4,
    "coordination_time_ms": 12500,
    "agent_names": ["tavern_bartender", "tavern_musician", "merchant_patron", "city_guard"]
  }
}
```

## Testing

### Using Test Script

```bash
# Test all multiagent scenarios
./scripts/test.sh --local chat-all

# Test specific scenarios
./scripts/test.sh --local gamemaster
./scripts/test.sh --local worldbuilding  
./scripts/test.sh --local storytelling
./scripts/test.sh --local problemsolving

# Test enhanced mcp-agent with auto-detection
./scripts/test.sh --local mcp-agent "Create a tavern scene with multiple characters"
```

### Example Test Commands

```bash
# Game Master scenario
./scripts/test.sh --local gamemaster "A mysterious stranger enters asking about ancient ruins"

# World building scenario  
./scripts/test.sh --local worldbuilding "Design the floating city of Aerion"

# Storytelling scenario
./scripts/test.sh --local storytelling "The discovery of time magic from different perspectives"

# Problem solving scenario
./scripts/test.sh --local problemsolving "Design a social deduction game for 12 players"
```

## Technical Architecture

### Agent Structure

Each agent is implemented as:

```python
Agent(
    name="specific_role_name",
    instruction="Detailed personality and expertise description", 
    server_names=[]  # No MCP servers for performance
)
```

### Orchestrator Pattern

```python
Orchestrator(
    llm_factory=llm_factory,
    available_agents=[agent1, agent2, agent3, agent4],
    plan_type="iterative",  # Dynamic, responsive planning
    name="scenario_coordinator"
)
```

### Scenario Detection

The system automatically detects appropriate scenarios based on message content:

```python
def _detect_scenario_type(self, message: str) -> str:
    """Detect appropriate multiagent scenario based on message content"""
    message_lower = message.lower()
    
    # Game master scenarios
    if any(word in message_lower for word in ['tavern', 'npc', 'character', 'dialogue']):
        return "gamemaster"
    
    # World building scenarios  
    elif any(word in message_lower for word in ['world', 'region', 'geography', 'culture']):
        return "worldbuilding"
    
    # And so on...
```

## Performance Considerations

### Response Times
- **Single Agent**: ~2-5 seconds
- **Multiagent Orchestration**: ~10-30 seconds (due to coordination overhead)
- **Parallel Agent Processing**: Agents run simultaneously, not sequentially

### When to Use Multiagent vs Single Agent

**Use Multiagent For**:
- Complex interactive scenes requiring multiple characters
- Rich content creation needing multiple expertise areas
- Sophisticated storytelling with multiple perspectives
- Complex problem solving requiring diverse skills

**Use Single Agent For**:
- Simple questions and direct responses
- Real-time gaming interactions requiring <500ms responses
- Basic chat and conversational interactions
- Performance-critical scenarios

### Optimization Strategies

1. **Scenario Pre-detection**: Route simple queries to single-agent endpoints
2. **Agent Caching**: Keep frequently-used agent teams warm
3. **Parallel Processing**: All agents in a team run simultaneously
4. **Response Streaming**: Stream individual agent outputs as they complete

## MMOIRL Applications

### Dynamic NPCs
- Multiple characters responding simultaneously to player actions
- Coordinated NPC behavior that feels like a living world
- Rich interactive dialogues with multiple personality types

### Procedural Content Generation
- Collaborative creation of game regions, cities, and cultures
- Multi-expert analysis for complex game design challenges
- Rich, multi-layered storytelling for dynamic narratives

### Adaptive Gameplay
- Intelligent routing based on interaction complexity
- Scalable from simple responses to sophisticated coordination
- Foundation for consciousness-like AI behavior patterns

### Educational Applications
- Multiple expert perspectives on complex topics
- Collaborative problem-solving demonstrations
- Rich, nuanced explanations from different viewpoints

## Integration with Existing Systems

### Chat Infrastructure
- Built on top of existing Gaia chat architecture
- Maintains authentication and response format compatibility
- Integrates with Redis caching and database conversation storage

### Gateway Routing
- New endpoints automatically routed through Gaia gateway
- Maintains backward compatibility with existing clients
- Consistent API patterns with other chat endpoints

### MCP-Agent Framework
- Uses LastMile AI's mcp-agent library for orchestration
- Leverages proven patterns for multiagent coordination
- Extensible architecture for adding new agent types and scenarios

## Future Enhancements

### Advanced Coordination Patterns
- **Swarm Intelligence**: Large numbers of simple agents working together
- **Hierarchical Orchestration**: Multi-level agent management
- **Dynamic Team Formation**: Agents chosen based on real-time needs

### Performance Optimizations
- **Hot-loaded Agent Teams**: Pre-initialized specialist groups
- **Intelligent Caching**: Cache common agent combinations
- **Streaming Coordination**: Real-time agent output as it's generated

### Extended Scenarios
- **Combat Coordination**: Multiple AI characters in tactical scenarios
- **Economic Simulation**: Agents representing different market forces
- **Social Dynamics**: Complex interpersonal relationship modeling

### Consciousness Integration
- **Memory Systems**: Agents that remember past interactions
- **Emotional States**: Agents with persistent moods and relationships
- **Learning Behaviors**: Agents that adapt based on player feedback

## Conclusion

Gaia's multiagent orchestration system provides the foundation for sophisticated AI coordination required for MMOIRL experiences. By combining multiple specialized agents through intelligent orchestration, we can create rich, dynamic, and immersive interactions that go far beyond simple single-agent chat responses.

This system enables:
- **Living World Experiences**: Multiple AI characters working together
- **Rich Content Creation**: Expert collaboration for complex game design
- **Sophisticated Storytelling**: Multi-perspective narrative generation  
- **Complex Problem Solving**: Diverse expertise applied to challenging scenarios

The architecture is designed to scale from simple single-agent responses to complex multiagent coordination, providing the flexibility needed for diverse MMOIRL gaming and educational applications.