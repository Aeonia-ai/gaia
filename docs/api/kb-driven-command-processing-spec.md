# KB-Driven Command Processing Tool Specification

> **Status**: SPECIFICATION  
> **Version**: 0.4  
> **Purpose**: Define general-purpose game command processing tool that leverages KB content for any game system  
> **Created**: 2025-10-22  
> **Updated**: 2025-10-22 (Simplified architecture, incorporated expert feedback)  
> **Related**: 
> - [KB Architecture Guide](../kb/developer/kb-architecture-guide.md) - Knowledge Base infrastructure  
> - [RBAC System Guide](../kb/reference/rbac-system-guide.md) - Role-based access control  
> - [Chat API Documentation](./chat/) - LLM processing infrastructure  

## Executive Summary

This specification defines a general-purpose `execute_game_command` tool that processes natural language commands for any game system by leveraging Knowledge Base content as interpretable game logic. The tool uses code-enforced RBAC with LLM interpretation of filtered content, supporting diverse game types through content-driven flexibility rather than code complexity.

## Design Principles

### **Content-Driven Generality**
- Support any game system through KB content, not predetermined code paths
- Let experiences define their own complexity levels and rule interpretations
- Leverage existing proven LLM-to-structured-response patterns

### **Security Through Code**
- Enforce RBAC in code before LLM processing, not through LLM interpretation
- Filter content by role before sending to LLM to prevent prompt injection
- Multi-layer validation with audit logging

### **Service Integration Flexibility**
- Any service (Chat, Web, KB) can invoke game command processing
- Tool-based approach leverages existing `ToolProvider` infrastructure
- Clear separation: services handle UI/conversation, tool handles game logic

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

### **Test Categories**

#### **1. RBAC Enforcement Tests**
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

#### **2. Game System Variety Tests**
```python
async def test_text_adventure_commands():
    """Test text adventure game system"""
    result = await execute_game_command(
        command="examine mailbox",
        experience="west-of-house",
        user_context={"role": "player"},
        session_state={"current_room": "west_of_house"}
    )
    
    assert result["success"] == True
    assert "mailbox" in result["narrative"]

async def test_turn_based_commands():
    """Test turn-based game system"""
    result = await execute_game_command(
        command="play rock",
        experience="rock-paper-scissors",
        user_context={"role": "player"},
        session_state={"round": 1}
    )
    
    assert result["success"] == True
    assert "rock" in result["narrative"]
    assert any(action["type"] == "update_score" for action in result["actions"])

async def test_ar_location_commands():
    """Test AR location-based system"""
    result = await execute_game_command(
        command="scan marker",
        experience="wylding-woods",
        user_context={"role": "player"},
        session_state={"current_waypoint": "woander_storefront"}
    )
    
    assert result["success"] == True
    assert any(action["type"] == "play_sound" for action in result["actions"])
```

#### **3. Content Integration Tests**
```python
async def test_content_filtering_by_role():
    """Verify RBAC content filtering"""
    # Test that players don't see gamemaster content
    player_content = GameRBAC.filter_content_for_role(sample_content, "player")
    assert "admin_commands" not in player_content
    
    # Test that gamemasters see all content
    gm_content = GameRBAC.filter_content_for_role(sample_content, "gamemaster")
    assert "admin_commands" in gm_content
```

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