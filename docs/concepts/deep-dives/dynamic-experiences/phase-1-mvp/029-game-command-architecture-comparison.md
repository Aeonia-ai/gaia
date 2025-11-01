# Markdown Command Execution Flow in GAIA

## Two Separate Systems for Command Processing

### System 1: Markdown-Based Agent System ✅ (Content-Driven)

**Endpoint**: `POST /agent/interpret`
**Purpose**: LLM interprets markdown rules and content
**Status**: ✅ Fully implemented

#### Flow Diagram
```
User Request → /agent/interpret → interpret_knowledge()
                                        ↓
                                  _load_context()
                                        ↓
                                  KB MCP Server
                                        ↓
                     List .md files in context_path (recursive)
                                        ↓
                      Read all markdown file contents
                                        ↓
                      Build prompt with markdown content
                                        ↓
                            LLM (Claude/OpenAI)
                                        ↓
                  Return interpretation/decision/synthesis
```

#### Code Path
```
app/services/kb/agent_endpoints.py:34-72
  → kb_agent.interpret_knowledge()  (kb_agent.py:44-111)
      → _load_context()  (kb_agent.py:427-459)
          → kb_server.list_kb_directory(pattern="*.md")
          → kb_server.read_kb_file() for each file
          → Returns Dict[file_path: content]
      → Build prompt with markdown content
      → llm_service.chat_completion()
      → Return interpretation
```

#### Example Request
```json
POST /agent/interpret
{
  "query": "Can I play rock?",
  "context_path": "experiences/rock-paper-scissors",
  "mode": "decision"
}
```

#### What It Does
1. **Loads markdown files** from `experiences/rock-paper-scissors/`
   - `rules/core/basic-play.md`
   - `rules/core/win-conditions.md`
   - `rules/meta/ai-behavior.md`
2. **Builds prompt** with markdown content as context
3. **Asks LLM** to interpret the query against the rules
4. **Returns narrative response** based on markdown content

#### Supported Modes
- `decision` - Make decisions based on KB knowledge
- `synthesis` - Synthesize information across sources
- `validation` - Validate actions against rules

---

### System 2: Hardcoded Game Command System ⚠️ (Code-Driven)

**Endpoint**: `POST /game/command`
**Purpose**: Execute predefined game actions with JSON state
**Status**: ⚠️ Does NOT load markdown (design intent unimplemented)

#### Flow Diagram
```
User Command → /game/command → execute_game_command()
                                        ↓
                          Haiku 4.5 parses command
                                        ↓
                        Extracts: action_type, target
                                        ↓
                 Hardcoded Python action routing:
                    if action_type == "look": ...
                    elif action_type == "collect": ...
                    elif action_type == "return": ...
                    elif action_type == "inventory": ...
                    elif action_type == "talk": ...
                                        ↓
            Read/write JSON instance files (manifest.json, item.json)
                                        ↓
            Return hardcoded narrative + structured state changes
```

#### Code Path
```
app/services/kb/game_commands_api.py:29-101
  → kb_agent.execute_game_command()  (kb_agent.py:113-321)
      → Haiku 4.5 parses natural language to action type
      → if action_type == "look":
            _find_instances_at_location()  (kb_agent.py:797-829)
      → elif action_type == "collect":
            _collect_item()  (kb_agent.py:830-924)
              - Reads manifest.json
              - Updates item.json (marks collected_by)
              - Hardcoded narrative: "You carefully lift the {item}..."
      → elif action_type == "return":
            _return_item()
      → elif action_type == "inventory":
            Load player_state.json
      → elif action_type == "talk":
            _talk_to_npc()
      → Returns structured JSON response
```

#### Example Request
```json
POST /game/command
{
  "command": "look around",
  "experience": "wylding-woods",
  "user_context": {
    "role": "player",
    "user_id": "player@test.com"
  }
}
```

#### What It Does
1. **Does NOT load markdown** templates or game-logic files
2. **Parses command** with Haiku 4.5: "look around" → action_type: "look"
3. **Routes to hardcoded method**: `_find_instances_at_location()`
4. **Reads JSON files**: `manifest.json` to find items/NPCs
5. **Returns hardcoded narrative**: "You carefully lift the dream bottle..."

#### Key Limitation
- Templates like `dream_bottle.md` exist but are **not loaded**
- Narratives are **hardcoded strings** in Python
- No markdown-driven interaction logic
- `game-logic/` directory is **empty**

---

## Comparison Table

| Feature | `/agent/interpret` | `/game/command` |
|---------|-------------------|-----------------|
| **Loads Markdown** | ✅ Yes (recursive) | ❌ No |
| **LLM Usage** | Full model (Claude/GPT) | Haiku 4.5 (parse only) |
| **Logic Source** | Markdown rules | Python code |
| **Narrative Source** | Markdown content | Hardcoded strings |
| **Response Format** | Free-form interpretation | Structured JSON |
| **State Management** | None | JSON files |
| **Use Case** | Rule interpretation | Game state operations |
| **Exposed to Chat LLM** | ❌ No | ✅ Yes (via `execute_game_command` tool) |

---

## Agent Endpoint Capabilities

### POST /agent/interpret
- Loads markdown files from KB
- LLM interprets natural language rules
- Returns narrative response
- **Example**: rock-paper-scissors rule interpretation

### POST /agent/workflow
- Executes step-by-step procedures from markdown
- Supports parameterized workflows
- Returns execution results

### POST /agent/validate
- Validates actions against markdown rules
- Returns validation result + reasons
- Useful for checking if action is allowed

### GET /agent/status
- Returns agent initialization status
- Shows cache size and capabilities
- Lists supported modes

### POST /agent/cache/clear
- Clears rule interpretation cache
- Forces fresh markdown loading

---

## Chat Tool Exposure

**7 KB Tools Available to Chat LLM:**

1. `search_knowledge_base` - Search user's KB
2. `load_kos_context` - Load KOS contexts (threads, plans)
3. `read_kb_file` - Read specific file
4. `list_kb_directory` - List files in directory
5. `load_kb_context` - Load topic context
6. `synthesize_kb_information` - Cross-domain synthesis
7. `execute_game_command` - **Only this uses `/game/command`**

**NOT exposed to Chat LLM:**
- `/agent/interpret` - Must call directly via REST API
- `/agent/workflow` - Must call directly via REST API
- `/agent/validate` - Must call directly via REST API

---

## Key Insights

### Why Two Systems?

**Agent endpoints** (`/agent/*`):
- Designed for markdown-driven rule interpretation
- Full LLM reasoning over content
- Content-first approach
- Works with rock-paper-scissors today

**Game command endpoint** (`/game/command`):
- Designed for structured state management
- Fast action execution (minimal LLM)
- Code-first approach (for now)
- Works with wylding-woods today

### Design Intent vs Reality

**Design Intent**: Both systems should load markdown
- rock-paper-scissors: ✅ Uses `/agent/interpret` with markdown
- wylding-woods: ❌ Uses `/game/command` WITHOUT markdown

**Why the Gap?**
- `/game/command` needs JSON state management (inventory, locations)
- Template markdown exists but loading not implemented yet
- Hardcoded approach was faster to ship MVP
- `game-logic/` directory empty (content not written yet)

### Future State

**Goal**: Merge benefits of both systems
- Load markdown for narrative/interaction logic
- Manage JSON for persistent state
- LLM interprets content-driven rules
- Fast execution for state operations

**Path Forward**:
1. Implement markdown loading in `execute_game_command()`
2. Populate `game-logic/` with command definitions
3. Replace hardcoded narratives with template content
4. Keep JSON for state, markdown for logic/narrative
