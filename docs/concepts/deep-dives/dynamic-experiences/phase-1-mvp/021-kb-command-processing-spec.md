# KB-Driven Command Processing Tool Specification

> **Status**: SPECIFICATION
> **Version**: 0.5
> **Purpose**: Define general-purpose game command processing tool that leverages KB content for any game system
> **Created**: 2025-10-22
> **Updated**: 2025-10-22 (Added gameplay-first TDD strategy with security envelope pattern)
> **Implementation Status**: Infrastructure complete, core processor pending (see below)
> **Related**:
> - **[Game Command Developer Guide](./game-command-developer-guide.md)** - Practical guide with examples and current status
> - [KB Architecture Guide](../kb/developer/kb-architecture-guide.md) - Knowledge Base infrastructure
> - [RBAC System Guide](../kb/reference/rbac-system-guide.md) - Role-based access control
> - [Chat API Documentation](./chat/) - LLM processing infrastructure  

## Executive Summary

This specification defines a general-purpose `execute_game_command` tool that processes natural language commands for any game system by leveraging Knowledge Base content as interpretable game logic. The tool uses code-enforced RBAC with LLM interpretation of filtered content, supporting diverse game types through content-driven flexibility rather than code complexity.

## Current Implementation Status

**As of October 27, 2025:**

### ✅ Infrastructure Complete
- **Chat Service Integration** (`app/services/chat/kb_tools.py`)
  - `execute_game_command` added to KB_TOOLS array
  - KBToolExecutor routes commands to KB service via HTTP
  - LLM can detect game commands via tool calling
  - Tested end-to-end via GAIA CLI

- **KB Service API** (`app/services/kb/game_commands_api.py`)
  - `/game/command` endpoint created
  - Request/response models defined
  - Router integrated into main KB service
  - Authentication context merging

- **Detection & Routing**
  - Zero string parsing - pure LLM tool calling
  - Automatic integration with unified_chat.py
  - Works for any experience defined in KB

### 🟡 Core Processor Partially Implemented
- **File:** `app/services/kb/kb_agent.py` (lines 109-277)
- **Implemented:**
  1. ✅ Natural language parsing with LLM (Claude Haiku 4.5)
  2. ✅ Location extraction from commands (waypoint + sublocation)
  3. ✅ Action type detection (look, collect, return, inventory)
  4. ✅ Instance management integration
  5. ✅ Structured response formatting
  6. ✅ Narrative generation from results

- **Not Yet Implemented (from spec):**
  1. ❌ KB content loading from markdown files (spec lines 182-198)
  2. ❌ RBAC filtering (`GameRBAC.filter_content_for_role()`)
  3. ❌ Code-enforced permission checking (spec lines 221-294)
  4. ❌ Audit logging (spec lines 609-635)
  5. ❌ Content-level access control

**Current Behavior:**
- Processes natural language → structured actions → instance operations
- Uses file-based instance management (JSON files in KB)
- Returns structured GameCommandResponse with narrative + state changes
- **Performance:** 1.5-2s average response time (including LLM parsing)

**What Works Now:**
```python
# Via chat: "pick up the dream bottle from shelf_1 at waypoint_28a"
# Via API: POST /game/command with natural language command
# Result: Haiku 4.5 extracts location + action → updates instance JSON → returns narrative
```

**Current Limitations:**
- No RBAC content filtering (all content visible to all users)
- No audit trail (commands not logged for security review)
- Location must be extractable from command text (no persistent session context)
- Limited to file-based instance operations (no dynamic KB content loading)

See **[Instance Management Implementation](./100-instance-management-implementation.md)** for file-based system details.

## Design Principles

### **Content-Driven Generality**
- Support any game system through KB content, not predetermined code paths
- Let experiences define their own complexity levels and rule interpretations
- Leverage existing proven LLM-to-structured-response patterns

### **Security Envelope Pattern**
- Implement minimal security boundaries early with placeholder tests
- Focus on gameplay validation first, expand security as features solidify
- Enforce RBAC in code before LLM processing, not through LLM interpretation
- Progressive security hardening without sacrificing development velocity

### **Service Integration Flexibility**
- Any service (Chat, Web, KB) can invoke game command processing
- Tool-based approach leverages existing `ToolProvider` infrastructure
- Clear separation: services handle UI/conversation, tool handles game logic

## Development Strategy

### **TDD Approach: Gameplay-First with Security Envelope**

Based on expert analysis, this system follows a **gameplay-first TDD strategy** with early security placeholders:

**Phase 1: Core Gameplay Mechanics**
- Focus on command execution, state management, and LLM interpretation
- Write failing tests for actual gameplay scenarios
- Implement basic session isolation and user scoping stubs
- Validate KB content loading and rule interpretation

**Phase 2: Rich Gameplay Features**
- Multi-turn narratives and complex state changes
- Advanced command parsing and natural language variations
- Cross-experience compatibility and content switching
- Performance optimization for command processing

**Phase 3: Security Envelope Expansion**
- Convert security stubs to full RBAC implementation
- Add comprehensive access control and content filtering
- Implement audit logging and security monitoring
- Penetration testing and security validation

**Rationale**: Early gameplay validation prevents building secure but unusable systems, while placeholder security tests ensure retrofit-friendly architecture.

### **Test Priority Framework**

1. **Start**: Core command execution (`"look"`, `"take lamp"`, `"go north"`)
2. **Next**: KB content interpretation and state persistence
3. **Then**: Multi-turn gameplay and session management
4. **Later**: Service integration and advanced features
5. **Last**: Full RBAC implementation and security hardening

## Tool Interface

### **Core Tool Definition**

```python
@tool_registry.register("execute_game_command")
async def execute_game_command(
    command: str,                    # Any natural language command
    experience: str,                 # Experience identifier from KB
    user_context: Dict[str, Any],    # {role, permissions, user_id, session_context}
    session_state: Optional[Dict] = None  # Current game state
) -> Dict[str, Any]:
    """
    General-purpose game command processor for any game system.
    
    Processes natural language commands by:
    1. Applying code-enforced RBAC filtering
    2. Loading and filtering KB content by role
    3. Using LLM to interpret content rules
    4. Returning structured responses with actions and state changes
    
    Args:
        command: Natural language command ("examine crystal", "go north", "cast fireball")
        experience: Experience ID from KB ("west-of-house", "sanctuary", "rock-paper-scissors")
        user_context: Role and permission information
        session_state: Current game state (optional, managed by caller)
    
    Returns:
        {
            "success": True,
            "narrative": "Generated narrative description",
            "actions": [{"type": "award_xp", "amount": 50}],
            "state_changes": {"crystal_discovered": True},
            "next_suggestions": ["attune to crystal", "examine garden"],
            "metadata": {"processing_info": "..."}
        }
    """
```

### **Response Format Specification**

```typescript
interface GameCommandResponse {
  success: boolean;
  
  // Core response (on success)
  narrative?: string;                    // Human-readable description
  actions?: Array<{                      // Structured actions for services
    type: string;                        // "award_xp", "play_sound", "add_item", etc.
    params: Record<string, any>;
  }>;
  state_changes?: Record<string, any>;   // Game state updates
  next_suggestions?: string[];           // Valid follow-up commands
  
  // Error response (on failure)
  error?: {
    code: string;                        // "invalid_command", "insufficient_permissions"
    message: string;                     // Human-readable error
    details?: Record<string, any>;       // Additional error context
  };
  
  // Metadata (always present)
  metadata: {
    processing_time_ms: number;
    kb_files_accessed: string[];
    persona_used: string;
    user_role: string;
    experience: string;
  };
}
```

## Processing Architecture

### **General Processing Pipeline**

```python
async def execute_game_command(command, experience, user_context, session_state):
    start_time = time.time()
    
    # 1. CODE-ENFORCED RBAC (security boundary)
    user_role = user_context.get("role", "player")
    
    if not GameRBAC.is_command_allowed(user_role, command, experience):
        return create_permission_denied_response(user_role, command)
    
    # 2. LOAD EXPERIENCE CONTENT (any game type)
    game_content = await kb_service.load_game_content(
        experience=experience,
        content_types=["GAME.md", "rules", "world", "mechanics", "waypoints"]
    )
    
    # 3. FILTER CONTENT BY ROLE (remove restricted sections)
    filtered_content = GameRBAC.filter_content_for_role(game_content, user_role)
    
    # 4. LLM INTERPRETATION (using existing KB-to-code pattern)
    interpretation = await llm_service.interpret_game_command(
        command=command,
        game_rules=filtered_content,
        current_state=session_state,
        user_context=user_context,
        persona="game_interpreter",
        response_format="structured"
    )
    
    # 5. VALIDATE AND FORMAT RESPONSE
    response = await format_response(
        interpretation, user_role, time.time() - start_time
    )
    
    # 6. AUDIT LOGGING
    audit_logger.log_command_execution(user_context, command, response)
    
    return response
```

### **Role-Based Access Control**

```python
class GameRBAC:
    """Code-enforced permissions - not LLM-interpreted"""
    
    ROLE_PERMISSIONS = {
        "player": {
            "content_access": ["public", "player"],
            "state_modification": ["player_inventory", "player_location", "player_stats"],
            "command_categories": ["movement", "interaction", "social", "basic"],
            "admin_commands": []
        },
        "storyteller": {
            "content_access": ["public", "player", "storyteller"],
            "state_modification": ["narratives", "dialogues", "descriptions"],
            "command_categories": ["movement", "interaction", "social", "narrative"],
            "admin_commands": ["narrate", "describe", "create_scene"]
        },
        "gamemaster": {
            "content_access": ["public", "player", "storyteller", "gamemaster", "admin"],
            "state_modification": ["world_state", "items", "npcs", "weather", "time"],
            "command_categories": ["*"],
            "admin_commands": ["set", "reset", "debug", "teleport", "give", "modify"]
        }
    }
    
    @classmethod
    def is_command_allowed(cls, role: str, command: str, experience: str) -> bool:
        """Check if role can execute command (code-enforced)"""
        role_perms = cls.ROLE_PERMISSIONS.get(role, cls.ROLE_PERMISSIONS["player"])
        
        # Extract command category
        command_category = cls.categorize_command(command)
        allowed_categories = role_perms.get("command_categories", [])
        
        if "*" in allowed_categories:
            return True
            
        return command_category in allowed_categories
    
    @classmethod
    def filter_content_for_role(cls, content: Dict, role: str) -> Dict:
        """Remove content sections user cannot access"""
        role_perms = cls.ROLE_PERMISSIONS.get(role, cls.ROLE_PERMISSIONS["player"])
        allowed_access = role_perms.get("content_access", ["public"])
        
        filtered = {}
        for key, value in content.items():
            # Check access level from content metadata
            access_level = getattr(value, 'access_level', 'public')
            if access_level in allowed_access:
                filtered[key] = value
        
        return filtered
    
    @classmethod
    def categorize_command(cls, command: str) -> str:
        """Categorize command for permission checking"""
        command_lower = command.lower()
        
        if any(word in command_lower for word in ["set", "debug", "teleport", "give", "modify"]):
            return "admin"
        elif any(word in command_lower for word in ["go", "move", "walk", "north", "south"]):
            return "movement"
        elif any(word in command_lower for word in ["examine", "take", "open", "use"]):
            return "interaction"
        elif any(word in command_lower for word in ["say", "tell", "whisper", "emote"]):
            return "social"
        elif any(word in command_lower for word in ["narrate", "describe", "create"]):
            return "narrative"
        else:
            return "basic"
```

## Service Integration Patterns

### **Chat Service Integration**

```python
# In chat service - detect and route game commands
async def process_user_message(message: str, user_context: Dict):
    # Check if user is in a game experience
    current_experience = user_context.get("current_experience")
    
    if current_experience and await is_potential_game_command(message):
        # Invoke game command tool
        tools = await ToolProvider.get_tools_for_activity("game_command")
        result = await tools["execute_game_command"](
            command=message,
            experience=current_experience,
            user_context=user_context,
            session_state=user_context.get("game_state")
        )
        
        if result["success"]:
            # Update user's game state
            user_context["game_state"] = result.get("updated_session", user_context.get("game_state"))
            
            # Convert to chat response
            return ChatResponse(
                message=result["narrative"],
                directives=convert_actions_to_directives(result.get("actions", [])),
                metadata={"type": "game_command", "next_suggestions": result.get("next_suggestions")}
            )
        else:
            # Handle error gracefully
            return ChatResponse(
                message=f"I don't understand that command. {result['error']['message']}",
                metadata={"type": "game_error"}
            )
    
    # Regular chat processing
    return await standard_chat_processing(message, user_context)

async def is_potential_game_command(message: str) -> bool:
    """Simple pattern-based detection"""
    game_command_patterns = [
        r"^(go|move|walk)\s+",
        r"^(examine|look|inspect)\s+",
        r"^(take|get|pick)\s+",
        r"^(inventory|inv|i)$",
        r"^(help|commands)$",
        r"^(use|cast|activate)\s+",
        r"^(say|tell|whisper)\s+"
    ]
    
    return any(re.match(pattern, message.lower()) for pattern in game_command_patterns)
```

### **Web Service Integration**

```python
# In web service - direct game command processing
@app.post("/game/command")
async def web_game_command(
    request: GameCommandRequest,
    user_session = Depends(get_current_session)
):
    tools = await ToolProvider.get_tools_for_activity("game_command")
    result = await tools["execute_game_command"](
        command=request.command,
        experience=request.experience,
        user_context={
            "role": user_session.role,
            "user_id": user_session.user_id,
            "permissions": user_session.permissions
        },
        session_state=user_session.game_state
    )
    
    if result["success"]:
        # Update session with new game state
        user_session.game_state.update(result.get("state_changes", {}))
        
        # Return web-friendly response
        return {
            "narrative": result["narrative"],
            "actions": result.get("actions", []),
            "suggestions": result.get("next_suggestions", []),
            "success": True
        }
    else:
        return {
            "error": result["error"]["message"],
            "success": False
        }
```

## KB Content Requirements

### **Universal Content Structure**

Any experience can use this structure - the tool adapts to whatever is present:

```markdown
---
# Universal metadata (YAML frontmatter)
experience_id: "any-game-name"
content_type: "room" | "item" | "rule" | "mechanic" | "waypoint"
access_level: "public" | "player" | "storyteller" | "gamemaster" | "admin"
tool_processing:
  response_format: "structured"
  complexity_level: "simple" | "moderate" | "complex"
---

# Content Title

## Description
Natural language description that LLM can use for context.

## Valid Actions (for any game type)

### [command pattern]
**Conditions**: [optional game state conditions]
**Response**: "[narrative text]" 
**Actions**: [optional structured actions]
```yaml
state_changes:
  key: value
actions:
  - type: "action_type"
    params: {}
```
```

### **Experience-Specific Examples**

#### **Text Adventure** (`west-of-house/world/rooms/west-of-house.md`)
```markdown
---
experience_id: "west-of-house"
content_type: "room"
access_level: "public"
---

# West of House

## Description
You are standing in an open field west of a white house.

## Valid Actions

### examine mailbox
**Response**: "A fairly ordinary mailbox, painted red."

### open mailbox
**Conditions**: mailbox_opened == false
**Response**: "You open the small mailbox. A leaflet is inside."
**Actions**:
```yaml
state_changes:
  mailbox_opened: true
actions:
  - type: "add_to_inventory"
    item: "leaflet"
  - type: "award_points"
    amount: 5
```
```

#### **Turn-Based Game** (`rock-paper-scissors/rules/core/basic-play.md`)
```markdown
---
experience_id: "rock-paper-scissors"
content_type: "rule"
access_level: "public"
---

# Basic Play Rules

## Game Flow
Players simultaneously choose rock, paper, or scissors.

## Valid Actions

### play [choice]
**Conditions**: choice in ["rock", "paper", "scissors"]
**Response**: "You play [choice]. AI plays [ai_choice]. [result]"
**Actions**:
```yaml
state_changes:
  player_choice: "[choice]"
  ai_choice: "[generated]"
  round_result: "[win/lose/tie]"
actions:
  - type: "update_score"
    winner: "[player/ai/tie]"
```
```

#### **AR Location** (`wylding-woods/waypoints/1_inter_woander_storefront.md`)
```markdown
---
experience_id: "wylding-woods"
content_type: "waypoint"
access_level: "public"
waypoint_data:
  lat: 37.906233
  lng: -122.547721
---

# Woander Storefront

## Description
A magical shop with glowing markers and mystical atmosphere.

## Valid Actions

### scan marker
**Conditions**: player_location near waypoint
**Response**: "The marker glows as you scan it with your device."
**Actions**:
```yaml
state_changes:
  marker_scanned: true
actions:
  - type: "play_sound"
    file: "magical_chime.wav"
  - type: "trigger_ar_effect"
    effect: "golden_sparkles"
  - type: "award_xp"
    amount: 10
```
```

### **Tool Configuration** (per experience)

```markdown
# experiences/[any-game]/tool-config.md
---
tool_integration:
  supported_command_types: ["movement", "interaction", "combat", "social"]
  response_format: "structured"
  session_management: "external"
  multiplayer_support: true
  complexity_level: "moderate"
---

## Processing Guidelines

### LLM Instructions
You are processing commands for [experience_name]. Use the content files to understand game rules and generate appropriate responses in the structured format.

### Error Handling
- Unknown commands: Suggest similar valid commands
- Invalid conditions: Explain what's required
- Permission denied: Explain role requirements
```

## Supported Game Systems

The tool architecture supports any game system through content definition:

### **Proven Game Types** (from existing KB content)
1. **Text Adventures**: Room-based navigation, item interaction, narrative
2. **Turn-Based Games**: Rule-based mechanics, scoring, AI opponents  
3. **AR Location Games**: GPS waypoints, real-world integration, media effects

### **Extensible to Any System**
- **Real-Time Strategy**: Unit commands, resource management, combat
- **Social Deduction**: Voting, role abilities, information sharing
- **Puzzle Games**: Logic challenges, hint systems, solution validation
- **Simulation Games**: World management, complex systems, progression

## Performance Considerations

### **Caching Strategy**

```python
class GameContentCache:
    """Cache KB content to minimize file system access"""
    
    def __init__(self):
        self.content_cache = {}  # Per-experience content
        self.metadata_cache = {}  # Content metadata
        self.ttl = 300  # 5-minute cache TTL
    
    async def get_game_content(self, experience: str) -> Dict:
        """Load and cache experience content"""
        if experience not in self.content_cache:
            content = await kb_service.load_game_content(experience)
            self.content_cache[experience] = content
            self.metadata_cache[experience] = {
                "loaded_at": time.time(),
                "file_count": len(content),
                "access_levels": self.extract_access_levels(content)
            }
        
        return self.content_cache[experience]
```

### **Optimization Guidelines**
- Cache frequently accessed content per experience
- Pre-filter content by role to reduce LLM token usage
- Use structured responses to minimize interpretation overhead
- Let experiences define their own complexity levels

## Security Model

### **Defense in Depth**

1. **Service Layer**: Authentication and basic input validation
2. **Tool Layer**: RBAC enforcement and content filtering
3. **Content Layer**: Access level metadata in frontmatter
4. **LLM Layer**: Processes only pre-filtered, authorized content
5. **Response Layer**: Role-based response filtering

### **Audit and Monitoring**

```python
class GameAuditLogger:
    """Log all game command execution for security monitoring"""
    
    async def log_command_execution(
        self, 
        user_context: Dict, 
        command: str, 
        response: Dict
    ):
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_context.get("user_id"),
            "user_role": user_context.get("role"),
            "command": command,
            "experience": user_context.get("current_experience"),
            "success": response.get("success"),
            "processing_time_ms": response.get("metadata", {}).get("processing_time_ms"),
            "rbac_applied": True,
            "content_filtered": True
        }
        
        # Log to security monitoring system
        security_logger.info("game_command_executed", extra=audit_entry)
```

## Testing Strategy

### **Gameplay-First TDD Implementation**

Following expert recommendation for **gameplay-first development with security envelope**, tests are prioritized to validate core mechanics before hardening security.

### **Phase 1: Core Gameplay Tests** (Start Here)

#### **1. Basic Command Execution Tests**
```python
def test_basic_look_command():
    """User says 'look' and gets room description with items."""
    result = await execute_game_command(
        command="look",
        experience="west-of-house",
        user_context={"role": "player", "user_id": "test"},
        session_state={"current_room": "west_of_house"}
    )
    
    assert result["success"] == True
    assert "white house" in result["narrative"].lower()
    assert "mailbox" in result["narrative"].lower()
    assert "obvious exits" in result["narrative"].lower()

def test_take_item_updates_inventory():
    """User takes lamp, it appears in inventory and disappears from room."""
    result = await execute_game_command(
        command="take lamp",
        experience="west-of-house",
        user_context={"role": "player", "user_id": "test"},
        session_state={
            "current_room": "forest",
            "inventory": [],
            "room_states": {"forest": {"items": ["lamp"]}}
        }
    )
    
    assert result["success"] == True
    assert "lamp" in result["narrative"]
    assert result["state_changes"]["inventory"] == ["lamp"]
    assert "lamp" not in result["state_changes"]["room_states"]["forest"]["items"]

def test_movement_between_rooms():
    """User goes north, current room changes, new room description shown."""
    result = await execute_game_command(
        command="go north",
        experience="west-of-house",
        user_context={"role": "player", "user_id": "test"},
        session_state={"current_room": "west_of_house"}
    )
    
    assert result["success"] == True
    assert result["state_changes"]["current_room"] == "north_of_house"
    assert "north of house" in result["narrative"].lower()

def test_rock_paper_scissors_game():
    """User plays rock, AI plays scissors, user wins."""
    result = await execute_game_command(
        command="rock",
        experience="rock-paper-scissors",
        user_context={"role": "player", "user_id": "test"},
        session_state={"round": 1, "score": {"player": 0, "ai": 0}}
    )
    
    assert result["success"] == True
    assert "rock" in result["narrative"].lower()
    assert any(action["type"] == "update_score" for action in result["actions"])
```

#### **2. Session Isolation Stubs** (Security Envelope)
```python
def test_user_session_isolation_stub():
    """Different users get separate game sessions (placeholder test)."""
    # TODO: Expand to full RBAC in Phase 3
    user1_state = {"current_room": "west_of_house", "inventory": ["lamp"]}
    user2_state = {"current_room": "west_of_house", "inventory": []}
    
    # Verify sessions don't bleed (basic implementation)
    assert user1_state != user2_state  # Placeholder - expand later
```

### **Phase 2: Rich Gameplay Features**

#### **3. State Persistence Tests**
```python
async def test_player_cannot_execute_admin_commands():
    """Verify code-enforced RBAC works"""
    result = await execute_game_command(
        command="set weather stormy",
        experience="sanctuary",
        user_context={"role": "player", "user_id": "test"},
        session_state={}
    )
    
    assert result["success"] == False
    assert result["error"]["code"] == "insufficient_permissions"
    assert "gamemaster" in result["error"]["details"]["required_role"]
```

```python
def test_multi_turn_narrative_consistency():
    """Commands build coherent story across multiple turns."""
    # Turn 1: Look around
    result1 = await execute_game_command("look", "west-of-house", user_context, {})
    
    # Turn 2: Examine mailbox
    result2 = await execute_game_command(
        "examine mailbox", "west-of-house", user_context, 
        result1["state_changes"]
    )
    
    # Turn 3: Open mailbox
    result3 = await execute_game_command(
        "open mailbox", "west-of-house", user_context,
        result2["state_changes"]
    )
    
    assert "leaflet" in result3["narrative"]
    assert result3["state_changes"]["mailbox_opened"] == True

def test_inventory_capacity_limits():
    """Inventory has realistic capacity constraints."""
    full_inventory = ["lamp", "matches", "leaflet", "sword", "rope", "bread", "water"]
    
    result = await execute_game_command(
        "take heavy_rock",
        "west-of-house",
        user_context,
        {"inventory": full_inventory, "inventory_capacity": 7}
    )
    
    assert result["success"] == False
    assert "too heavy" in result["error"]["message"].lower()
```

#### **4. Content Loading and Interpretation**
```python
def test_kb_content_loading():
    """Load game rules from actual KB markdown files."""
    # Test loading west-of-house room content
    content = await load_experience_content("west-of-house")
    
    assert "west_of_house" in content["rooms"]
    assert "mailbox" in content["rooms"]["west_of_house"]["items"]
    assert "north" in content["rooms"]["west_of_house"]["exits"]

def test_natural_language_command_variations():
    """Handle command variations and synonyms."""
    commands = ["take lamp", "get lamp", "grab the lamp", "pick up lamp"]
    
    for command in commands:
        result = await execute_game_command(
            command, "west-of-house", user_context,
            {"current_room": "forest", "room_states": {"forest": {"items": ["lamp"]}}}
        )
        assert result["success"] == True
        assert "lamp" in result["state_changes"]["inventory"]
```

### **Phase 3: Security Envelope Expansion** (Final Phase)

#### **5. RBAC Enforcement Tests** (Convert stubs to full implementation)

#### **6. Content Filtering and Access Control**
```python
async def test_player_cannot_execute_admin_commands():
    """Verify code-enforced RBAC works (converted from stub)"""
    result = await execute_game_command(
        command="set weather stormy",
        experience="sanctuary",
        user_context={"role": "player", "user_id": "test"},
        session_state={}
    )
    
    assert result["success"] == False
    assert result["error"]["code"] == "insufficient_permissions"
    assert "gamemaster" in result["error"]["details"]["required_role"]

async def test_content_filtering_by_role():
    """Verify RBAC content filtering"""
    # Test that players don't see gamemaster content
    player_content = GameRBAC.filter_content_for_role(sample_content, "player")
    assert "admin_commands" not in player_content
    
    # Test that gamemasters see all content
    gm_content = GameRBAC.filter_content_for_role(sample_content, "gamemaster")
    assert "admin_commands" in gm_content

async def test_cross_user_session_isolation():
    """Full implementation of session isolation (expanded from stub)"""
    user1_context = {"role": "player", "user_id": "user1"}
    user2_context = {"role": "player", "user_id": "user2"}
    
    # User 1 takes lamp
    result1 = await execute_game_command(
        "take lamp", "west-of-house", user1_context,
        {"current_room": "forest", "inventory": []}
    )
    
    # User 2 tries to take same lamp - should fail
    result2 = await execute_game_command(
        "take lamp", "west-of-house", user2_context,
        {"current_room": "forest", "inventory": []}
    )
    
    assert result1["success"] == True
    assert "lamp" in result1["state_changes"]["inventory"]
    # Session isolation: User 2 sees lamp still available in their session
    assert result2["success"] == True or "don't see" in result2["error"]["message"]
```

### **TDD Development Benefits**

**Gameplay-First Advantages Realized**:
- **Rapid validation** of LLM interpretation and KB content loading
- **Early user experience feedback** on command parsing and narrative quality
- **Clear test scenarios** that demonstrate actual game functionality
- **Reduced complexity** by focusing on core mechanics before security

**Security Envelope Benefits**:
- **Retrofit-friendly architecture** with placeholder security hooks
- **Progressive hardening** without breaking existing gameplay tests
- **Clear security boundaries** identified through gameplay testing
- **Maintainable test suite** with logical progression from simple to complex

## Migration and Implementation

### **Phase 1: Core Tool Implementation**
1. Implement `execute_game_command` tool with basic RBAC
2. Add tool registration to existing `ToolProvider` system
3. Create content filtering and caching infrastructure
4. Test with one existing experience (`west-of-house`)

### **Phase 2: Service Integration**
1. Add game command detection to Chat service
2. Implement Web service integration endpoints
3. Add session state management for game contexts
4. Test across all three existing game types

### **Phase 3: Content Enhancement**
1. Add YAML frontmatter metadata to existing content
2. Create tool-config.md files for each experience
3. Implement audit logging and monitoring
4. Performance optimization and caching

### **Phase 4: Advanced Features**
1. Multiplayer session coordination
2. Real-time state synchronization
3. Community content creation tools
4. Advanced AI persona coordination

## Success Metrics

### **Functional Metrics**
- **Command Processing Success Rate**: >95% for well-formed commands
- **RBAC Enforcement**: 100% compliance with role permissions
- **Game System Support**: All existing game types work without modification

### **Performance Metrics**
- **Response Time**: <3 seconds for typical commands
- **Cache Hit Rate**: >80% for frequently accessed content
- **Concurrent Users**: Support 100+ simultaneous players per experience

### **Security Metrics**
- **Permission Bypass Attempts**: 0 successful bypasses
- **Audit Completeness**: 100% of commands logged
- **Content Filtering**: 100% of restricted content properly filtered

## Related Documentation

- **[KB Architecture Guide](../kb/developer/kb-architecture-guide.md)** - Knowledge Base infrastructure and content organization
- **[RBAC System Guide](../kb/reference/rbac-system-guide.md)** - Role-based access control implementation  
- **[Chat API Documentation](./chat/)** - LLM processing and persona management
- **[Authentication Guide](../authentication/authentication-guide.md)** - JWT and role-based authentication
- **[Testing Guide](../testing/TESTING_GUIDE.md)** - Testing patterns and best practices

## Conclusion

The KB-Driven Command Processing Tool provides a general-purpose foundation for natural language game commands across any game system. By enforcing security through code while enabling flexibility through content, the tool supports rapid game development and deployment without sacrificing reliability or security.

The tool-based architecture leverages existing GAIA infrastructure while providing clear boundaries between authorization, content loading, and game logic interpretation. This approach enables both simple and complex game systems to coexist within the same processing framework, determined by their content definitions rather than code complexity.

---

## Key Points Summary

### **General-Purpose Architecture**
- **Support**: Tool works with any game system through content definition, not code assumptions
- **Support**: Proven by existing variety: text adventure, turn-based, AR location-based
- **Support**: Content-driven complexity allows simple to complex games in same framework

### **Code-Enforced Security**  
- **Support**: RBAC validation before LLM processing prevents prompt injection
- **Support**: Multi-layer filtering with audit logging ensures security boundaries
- **Support**: Role-based content access prevents unauthorized information disclosure

### **Service Integration Flexibility**
- **Support**: Tool pattern leverages existing `ToolProvider` infrastructure
- **Support**: Any service can invoke game processing without architectural changes  
- **Support**: Clear separation between UI/conversation handling and game logic

### **Minimal Content Modifications**
- **Support**: Existing KB structure works with additive enhancements only
- **Support**: YAML frontmatter and structured responses maintain content readability
- **Support**: No fundamental restructuring required for current game content

### **Performance Through Caching**
- **Support**: Experience-level content caching reduces file system access
- **Support**: Role-based filtering reduces LLM token usage
- **Support**: Content-defined complexity levels optimize processing