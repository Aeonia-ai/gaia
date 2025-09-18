# KB Endpoints and Chat Integration Guide

## Overview

This document provides a comprehensive guide to how the Knowledge Base (KB) service works and how the chat service integrates with it. The KB system is a sophisticated multi-layered architecture that provides intelligent knowledge management capabilities for the GAIA platform.

**★ Insight ─────────────────────────────────────**
The KB system uses a three-tier architecture: **Chat Service Tools** → **KB Service HTTP Endpoints** → **KB MCP Server**. This creates a clean separation where the chat service doesn't need to know about file systems or search implementations, while the KB service handles all knowledge management logic.
**─────────────────────────────────────────────────**

## Architecture Overview

```
┌─────────────────┐    HTTP/JSON    ┌─────────────────┐    Direct FS    ┌─────────────────┐
│   Chat Service  │ ──────────────► │   KB Service    │ ──────────────► │   KB MCP Server │
│                 │                 │                 │                 │                 │
│ - KB Tools      │                 │ - HTTP Endpoints│                 │ - File System   │
│ - Tool Executor │                 │ - Auth Handling │                 │ - Search (rg)   │
│ - LLM Interface │                 │ - Response Format│                 │ - Cache Layer   │
└─────────────────┘                 └─────────────────┘                 └─────────────────┘
```

### Core Components

1. **KB Tools (`kb_tools.py`)**: Tool definitions and HTTP client for chat service
2. **KB Service (`kb_service.py`)**: HTTP endpoints that process requests
3. **KB MCP Server (`kb_mcp_server.py`)**: Core knowledge management logic
4. **KB Agent (`kb_agent.py`)**: Intelligent interpretation and decision making

## Chat Service Integration

### 1. Tool Definition and Registration

The chat service integrates with KB through tool definitions in `app/services/chat/kb_tools.py`:

```python
KB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "FIRST CHOICE for KB queries: Real-time search of user's personal knowledge base...",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "limit": {"type": "integer", "description": "Max results", "default": 10}
                },
                "required": ["query"]
            }
        }
    },
    # ... 8 other KB tools
]
```

#### Available KB Tools

| Tool Name | Purpose | Key Parameters |
|-----------|---------|----------------|
| `search_knowledge_base` | Primary search functionality | `query`, `limit` |
| `read_kb_file` | Read specific file content | `path` |
| `list_kb_directory` | Browse directory structure | `path` |
| `load_kos_context` | Load operational contexts | `context_type`, `project` |
| `load_kb_context` | Load topic-related context | `topic`, `depth` |
| `synthesize_kb_information` | Cross-domain synthesis | `sources`, `focus` |
| `interpret_knowledge` | **AI-powered analysis** | `query`, `context_path`, `mode` |
| `execute_knowledge_workflow` | Run KB-defined workflows | `workflow_path`, `parameters` |
| `validate_against_rules` | Rule validation | `action`, `rules_path`, `context` |

### 2. Integration in Unified Chat

In `app/services/chat/unified_chat.py`, KB tools are integrated into the LLM tool selection:

```python
# Line 222: Combine routing tools with KB tools
all_tools = self.routing_tools + KB_TOOLS

# Line 250: Execute KB tools when selected
tool_results = await self._execute_kb_tools(kb_calls, auth, request_id, conversation_id)
```

#### Tool Execution Flow

1. **LLM Tool Selection**: LLM chooses appropriate KB tool based on user query
2. **Tool Classification**: System identifies KB tools vs routing tools
3. **Authentication**: Auth principal passed to KB service
4. **HTTP Request**: Tool executor makes HTTP call to KB service
5. **Response Processing**: Results formatted for LLM context
6. **Final Response**: LLM generates response using tool results

### 3. KBToolExecutor Implementation

The `KBToolExecutor` class handles HTTP communication with the KB service:

```python
class KBToolExecutor:
    def __init__(self, auth_principal: Dict[str, Any], progressive_mode: bool = False):
        # Handle both JWT and API key authentication
        api_key = auth_principal.get("key", "")
        if not api_key and auth_principal.get("auth_type") == "jwt":
            api_key = settings.API_KEY  # Use system API key for inter-service calls

        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
```

#### Progressive Response Support

The KB system supports progressive responses for enhanced UX:

```python
# Special handling for interpret_knowledge tool
if tool_name == "interpret_knowledge" and self.progressive_mode:
    # Yield progressive events for real-time feedback
    async for event in progressive_interpret_knowledge(...):
        yield event
```

## KB Service HTTP Endpoints

The KB service (`app/services/kb/kb_service.py`) exposes these HTTP endpoints:

### Core Search Endpoints

| Endpoint | Method | Purpose | Request Format |
|----------|--------|---------|----------------|
| `/search` | POST | Knowledge base search | `{"message": "search query"}` |
| `/read` | POST | Read specific file | `{"message": "file/path.md"}` |
| `/list` | POST | List directory contents | `{"message": "/directory/path"}` |
| `/context` | POST | Load topic context | `{"message": "topic (depth: 2)"}` |
| `/synthesize` | POST | Cross-domain synthesis | `{"message": "Synthesize from: sources"}` |

### Advanced KB Agent Endpoints

| Endpoint | Method | Purpose | Request Format |
|----------|--------|---------|----------------|
| `/agent/interpret` | POST | AI-powered knowledge interpretation | `{"query": "...", "context_path": "/", "mode": "decision"}` |
| `/agent/workflow` | POST | Execute knowledge workflows | `{"workflow_path": "...", "parameters": {}}` |
| `/agent/validate` | POST | Validate against KB rules | `{"action": "...", "rules_path": "...", "context": {}}` |

### Specialized Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/threads` | POST | Get active KOS threads |
| `/navigate` | POST | Navigate KB index system |
| `/multitask` | POST | Execute multiple KB tasks in parallel |
| `/claude-code` | POST | Execute Claude Code commands |

### Response Format

All KB service endpoints return a standardized format:

```json
{
    "status": "success" | "error",
    "response": "Formatted response content",
    "metadata": {
        "total_results": 10,
        "query": "original query",
        // ... additional metadata
    }
}
```

## KB MCP Server Core Functionality

The KB MCP Server (`app/services/kb/kb_mcp_server.py`) provides the core knowledge management capabilities:

### File System Integration

```python
class KBMCPServer:
    def __init__(self, kb_path: str = "/kb"):
        self.kb_path = Path(kb_path)
        self.cache = kb_cache  # Redis cache
        self.cache_ttl = 300  # 5 minutes
```

#### Key Capabilities

1. **Direct File System Access**: Fast access to mounted KB volume
2. **Ripgrep Search**: High-performance text search across all files
3. **Frontmatter Parsing**: Extracts metadata from markdown files
4. **Redis Caching**: Performance optimization with 5-minute TTL
5. **Path Security**: Validates all paths are within KB boundaries

### Search Implementation

The KB uses `ripgrep` for fast, accurate search:

```bash
# Example ripgrep command executed by KB server
rg --json --context=2 --max-count=50 "search term" /kb/
```

#### Search Features

- **Full-text search** across all file types
- **Context extraction** with surrounding lines
- **Relevance scoring** based on match frequency
- **File type filtering** for specific document types
- **Case-insensitive search** with pattern matching

## KB Agent: Intelligent Knowledge Processing

The KB Agent (`app/services/kb/kb_agent.py`) provides AI-powered knowledge interpretation:

### Core Agent Capabilities

```python
class KBIntelligentAgent:
    async def interpret_knowledge(self, query: str, context_path: str, user_id: str,
                                mode: str = "decision") -> Dict[str, Any]:
        # 1. Load relevant knowledge from KB
        # 2. Build prompt based on mode (decision/synthesis/validation)
        # 3. Select appropriate LLM model
        # 4. Generate intelligent response
        # 5. Cache successful interpretations
```

#### Agent Modes

| Mode | Purpose | LLM Requirements | Temperature |
|------|---------|------------------|-------------|
| `decision` | Make choices based on KB content | `CHAT` capability | 0.7 |
| `synthesis` | Combine information across domains | `LONG_CONTEXT` capability | 0.7 |
| `validation` | Check against established rules | `CODE_GENERATION` capability | 0.3 |

### Workflow Execution

The agent can execute workflows defined in markdown:

```markdown
# Player Combat Workflow
1. Check player stats
2. Calculate damage based on weapon
3. Apply environmental modifiers
4. Update creature health
```

The agent interprets these steps and executes them using LLM reasoning.

## Authentication and Security

### Multi-User Support

When `KB_MULTI_USER_ENABLED` is true:

```python
# Email-based user identification
if getattr(settings, 'KB_MULTI_USER_ENABLED', False):
    user_email = auth_principal.get("email")
    if user_email:
        kwargs["user_id"] = user_email
    else:
        raise HTTPException(status_code=403,
                          detail="KB access requires email-based authentication")
```

### API Key Handling

The system supports dual authentication:

1. **Direct API Keys**: For API key-based authentication
2. **JWT Tokens**: Uses system API key for inter-service communication
3. **System Fallback**: Uses `settings.API_KEY` when JWT auth is detected

### RBAC Integration

When RBAC is enabled, the KB service integrates with role-based access control:

```python
# Conditional import based on multi-user settings
if getattr(settings, 'KB_MULTI_USER_ENABLED', False):
    from .kb_rbac_integration import kb_server_with_rbac as kb_server
else:
    from .kb_mcp_server import kb_server
```

## Performance Optimization

### Caching Strategy

1. **Redis Cache**: 5-minute TTL for search results and file contents
2. **Rule Cache**: In-memory cache for frequently accessed rules
3. **Context Cache**: Cached context loading for repeated queries

### Search Optimization

1. **Ripgrep**: Fastest text search tool available
2. **Parallel Execution**: Multi-task endpoint for concurrent operations
3. **Result Limiting**: Configurable result limits to prevent overload
4. **Content Truncation**: Large files truncated in responses

## Progressive Response Integration

### V0.3 Progressive Format

The KB system supports the v0.3 progressive response format:

```python
# Immediate acknowledgment
yield {
    "type": "content",
    "content": "📊 Analyzing specialized knowledge base content..."
}

# Detailed analysis follows
yield {
    "type": "content",
    "content": "## 🧠 KB Agent Analysis\n\nBased on comprehensive knowledge..."
}
```

### Use Cases for Progressive Responses

1. **Complex Searches**: Large KB searches with immediate feedback
2. **Cross-Domain Synthesis**: Multi-step analysis across contexts
3. **Workflow Execution**: Step-by-step workflow progress
4. **Agent Interpretation**: Real-time AI analysis updates

## Error Handling and Resilience

### Common Error Scenarios

1. **File Not Found**: Graceful handling with helpful error messages
2. **Search Timeout**: Configurable timeouts with partial results
3. **Authentication Failures**: Clear error messages for auth issues
4. **Service Unavailability**: Fallback responses when KB service is down

### Logging and Monitoring

```python
# Comprehensive logging throughout the system
logger.info(f"🔍 KB search: {query}")
logger.warning(f"KB search for user: {user_email}")
logger.error(f"KB search failed: {e}", exc_info=True)
```

## Configuration and Deployment

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `KB_SERVICE_URL` | KB service endpoint | `http://kb-service:8000` |
| `KB_PATH` | KB file system path | `/kb` |
| `KB_MULTI_USER_ENABLED` | Enable multi-user support | `False` |
| `API_KEY` | System API key | Required |

### Docker Integration

The KB service is designed for containerized deployment:

```yaml
volumes:
  - /path/to/knowledge/base:/kb:ro
environment:
  - KB_PATH=/kb
  - KB_MULTI_USER_ENABLED=false
```

## Testing and Validation

### Test Coverage

The KB system includes comprehensive tests:

- `test_kb_response_processing.py`: Response format validation
- `test_kb_tool_classification.py`: Tool selection logic
- `test_kb_http_builder.py`: HTTP request construction
- `test_kb_tool_parsing.py`: Tool argument parsing
- `test_kb_progressive_response.py`: Progressive response format

### Manual Testing Commands

```bash
# Test KB search via chat service
python3 gaia_client.py --env local --batch "search my knowledge for project status"

# Test KB agent interpretation
python3 gaia_client.py --env local --batch "KB Agent analyze my knowledge base"

# Test file reading
python3 gaia_client.py --env local --batch "read my notes on deployment"
```

## Troubleshooting Common Issues

### Authentication Problems

**Symptom**: 403 Forbidden errors from KB service
**Solution**: Verify `X-API-Key` header and multi-user settings

### Search Returns No Results

**Symptom**: Empty search results for known content
**Solution**: Check KB path mounting and file permissions

### Progressive Responses Not Working

**Symptom**: No immediate acknowledgment in chat
**Solution**: Verify `progressive_mode=True` in KBToolExecutor

### Performance Issues

**Symptom**: Slow KB responses
**Solution**: Check Redis cache connectivity and KB volume size

## Best Practices

### For Developers

1. **Always use KB tools** for knowledge base operations, never direct file access
2. **Handle authentication properly** with both API key and JWT support
3. **Implement progressive responses** for long-running operations
4. **Cache results appropriately** to avoid repeated expensive operations
5. **Validate inputs** to prevent security issues

### For Users

1. **Use specific search terms** for better results
2. **Leverage KB Agent** for complex analysis and decision making
3. **Organize KB content** with clear file structure and frontmatter
4. **Test workflows** before relying on them for automation

## Future Enhancements

### Planned Features

1. **Vector Search Integration**: Semantic search capabilities
2. **Real-time Collaboration**: Multi-user editing and sharing
3. **Advanced Analytics**: Usage patterns and knowledge insights
4. **AI-Powered Organization**: Automatic content categorization
5. **Version Control Integration**: Git-based change tracking

This comprehensive guide provides everything needed to understand and work with the KB endpoints and chat integration system.