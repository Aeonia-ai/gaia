# KB Integration Implementation Guide

**Version**: 2.0  
**Date**: 2025-07-26  
**Status**: HTTP-Based Implementation (Updated)  

## Overview

This document describes the HTTP-based Knowledge Base (KB) integration with Gaia Platform, enabling Knowledge Operating System (KOS) capabilities through direct HTTP calls to the KB service.

## Architecture

### Components Implemented

```
┌─────────────────────────────────────────────────────────────┐
│                    Gateway Service (8666)                   │
│                /api/v1/chat/* endpoints                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  Chat Service (8668)                        │
│                 unified_chat.py                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              KB Tools (kb_tools.py)                │    │
│  │                                                     │    │
│  │  • search_knowledge_base() - HTTP search call     │    │
│  │  • load_kos_context() - Context loading           │    │
│  │  • read_kb_file() - File reading                  │    │
│  │  • list_kb_directory() - Directory listing        │    │
│  │  • load_kb_context() - Topic context              │    │
│  │  • synthesize_kb_information() - Cross-domain     │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │ HTTP Calls                      │
└───────────────────────────┼─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    KB Service (8000)                        │
│                                                             │
│  HTTP Endpoints:                                            │
│  • POST /search - Fast search                              │
│  • POST /read - File reading                               │
│  • POST /list - Directory listing                          │
│  • POST /context - Context loading                         │
│  • POST /synthesize - Cross-domain synthesis              │
│  • POST /threads - Thread management                       │
│                           │                                 │
│                           ▼                                 │
│              Direct File System Access                      │
│              /kb (mounted volume)                          │
└─────────────────────────────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  KB Volume   │
                    │ (read-only) │
                    └─────────────┘
```

## Key Files Implemented

### 1. KB Tools (`app/services/chat/kb_tools.py`)

HTTP-based KB integration tools for LLM use:

- **search_knowledge_base()**: Searches KB via HTTP POST to `/search`
- **load_kos_context()**: Loads KOS context via HTTP POST to `/search` with specific patterns
- **read_kb_file()**: Reads files via HTTP POST to `/read`
- **list_kb_directory()**: Lists directory contents via HTTP POST to `/list`
- **load_kb_context()**: Loads topic context via HTTP POST to `/context`
- **synthesize_kb_information()**: Cross-domain synthesis via HTTP POST to `/synthesize`

**Key Features**:
- Direct HTTP calls to KB service
- Standard authentication via X-API-Key headers
- Standardized {success, content, error} response format
- Integration with LLM tool-calling system

### 2. Unified Chat Handler (`app/services/chat/unified_chat.py`)

Intelligent chat routing with KB tool integration:

- **KB Tool Detection**: Recognizes when KB tools are called by LLM
- **HTTP Execution**: Executes KB tools via KBToolExecutor class
- **Response Processing**: Formats KB results for final LLM response
- **Metadata Tracking**: Tracks which KB tools were used

**KB Tool Integration Flow**:
1. LLM receives message with KB tools available
2. LLM calls KB tools (e.g., `search_knowledge_base`)
3. `KBToolExecutor` makes HTTP calls to KB service
4. KB service returns structured response
5. Results fed back to LLM for final response generation

### 3. KB Service (`app/services/kb/main.py` & `kb_service.py`)

Standalone HTTP service providing KB functionality:

```python
@app.post("/search")        # KB search endpoint
@app.post("/read")          # File reading endpoint  
@app.post("/list")          # Directory listing endpoint
@app.post("/context")       # Context loading endpoint
@app.post("/synthesize")    # Cross-domain synthesis endpoint
@app.post("/threads")       # Thread management endpoint
```

### 4. Gateway Integration (`app/gateway/main.py`)

No direct KB endpoints - KB access happens through unified chat:

```python
@app.post("/api/v1/chat/")  # Unified chat with KB tool support
```

## Authentication & Request Flow

### KB Tool Execution Flow

1. **User Message**: "Search my knowledge base for X"
2. **Unified Chat**: Processes message with KB tools available
3. **LLM Tool Call**: LLM calls `search_knowledge_base` tool
4. **HTTP Request**: KBToolExecutor makes HTTP call:
   ```
   POST http://kb-service:8000/search
   Headers: X-API-Key: <user-api-key>
   Body: {"message": "X"}
   ```
5. **KB Response**: 
   ```json
   {
     "status": "success",
     "response": "Search results...",
     "metadata": {"total_results": 5, "query": "X"}
   }
   ```
6. **Final Response**: LLM generates response using KB results

### Authentication Pattern

```python
class KBToolExecutor:
    def __init__(self, auth_principal: Dict[str, Any]):
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": auth_principal.get("key", "")
        }
```

## Configuration

### Docker Compose Setup

KB service runs independently with volume mount:

```yaml
kb-service:
  build:
    context: .
    dockerfile: Dockerfile.kb
  volumes:
    - ${KB_PATH:-/path/to/kb}:/kb:ro
  environment:
    - KB_PATH=/kb
    - SERVICE_PORT=8000
  ports:
    - "8000:8000"

chat-service:
  environment:
    - KB_SERVICE_URL=http://kb-service:8000
```

### Environment Variables

```env
# KB Service Configuration  
KB_SERVICE_URL=http://kb-service:8000    # KB service endpoint
KB_PATH=/kb                              # Path to mounted KB
KB_STORAGE_MODE=git                      # Storage backend mode

# Chat Service Configuration
KB_TOOLS_ENABLED=true                    # Enable KB tools in chat
```

## Usage Examples

### 1. KB Search via Chat

```bash
./scripts/test.sh --local unified "Search my knowledge base for consciousness"
```

This triggers:
1. Unified chat receives message
2. LLM calls `search_knowledge_base` tool
3. HTTP call to KB service `/search` endpoint
4. Formatted results returned to user

### 2. File Reading

```bash
./scripts/test.sh --local unified "Read the file about project architecture"
```

Flow: `read_kb_file` tool → HTTP POST `/read` → File content

### 3. Context Loading

```bash
./scripts/test.sh --local unified "Load the gaia project context"
```

Flow: `load_kos_context` tool → HTTP POST `/search` with context patterns

## Testing

### Test Script Integration

Added KB endpoints to `scripts/test.sh`:

```bash
# Individual endpoint tests
./scripts/test.sh kb-enhanced "Query"
./scripts/test.sh kb-research "Topic"  
./scripts/test.sh kb-gamemaster "Scene"
./scripts/test.sh kb-development "Question"
./scripts/test.sh kb-search "Keywords"
./scripts/test.sh kb-context "ContextName"
./scripts/test.sh kb-multitask "Tasks"

# Batch testing (includes KB endpoints)
./scripts/test.sh chat-all
```

### Standalone Testing

```bash
# Test KB server independently
python test_kb_integration.py
```

## Performance Characteristics

### HTTP-Based Performance

- **KB Search**: ~100-300ms (HTTP overhead + search)
- **File Reading**: ~50-100ms (HTTP overhead + file I/O)  
- **Context Loading**: ~200-500ms (HTTP overhead + context processing)
- **Tool Execution**: ~150ms routing + KB operation time

## Integration Benefits

### Immediate Value

1. **Service Separation**: KB runs independently, can be scaled separately
2. **HTTP Standard**: Uses standard REST patterns, easy to test/debug
3. **Tool Integration**: Natural LLM tool-calling integration
4. **Unified Interface**: Single chat endpoint handles KB operations

### Strategic Value  

1. **Microservice Architecture**: KB service can be deployed independently
2. **Multi-User Ready**: KB service supports RBAC and user namespaces
3. **API Standard**: HTTP APIs can be used by any client
4. **Scalability**: KB service can be horizontally scaled

## Security Model

### Access Control

- **Read-only access**: KB mounted as read-only volume
- **Path validation**: All file operations validate paths within KB
- **Authentication**: All endpoints require valid authentication
- **No sandboxing**: Direct file access (same security model as Claude Code)

### File System Security

```python
def _validate_path(self, path: str) -> Path:
    """Validate path is within KB and exists"""
    resolved = full_path.resolve()
    if not str(resolved).startswith(str(self.kb_path.resolve())):
        raise ValueError(f"Path outside KB: {path}")
    return resolved
```

## Integration Benefits

### Immediate Value

1. **Knowledge Access**: Direct search and navigation of KB content
2. **Context Switching**: Seamless movement between knowledge domains
3. **Cross-Domain Synthesis**: Insights across multiple contexts
4. **Agent Enhancement**: KB-aware multiagent behaviors

### Strategic Value

1. **KOS Foundation**: Stepping stone to full Knowledge Operating System
2. **Unified Experience**: Same tools work in Claude Code and Gaia
3. **Scalable Architecture**: Can expand to multi-user, cloud storage
4. **No Vendor Lock-in**: Standard filesystem, portable approach

## Future Enhancements

### Phase 2: Database Caching

- PostgreSQL index for metadata and search optimization
- Hot path tracking for performance tuning
- Query result caching with TTL

### Phase 3: Multi-User Support

- Per-user KB directories
- Sharing mechanisms between users
- Workspace collaboration features

### Phase 4: Advanced Features

- Vector embeddings for semantic search
- Smart cache warming based on usage patterns  
- Write operations with Git integration
- Real-time collaboration features

## Troubleshooting

### Common Issues

1. **KB Service Not Available**
   ```
   Solution: Check KB service health at http://kb-service:8000/health
   ```

2. **Authentication Failures**
   ```
   Solution: Verify X-API-Key header is being sent correctly
   ```

3. **Tool Not Called**
   ```
   Solution: Check LLM prompt includes KB tool descriptions
   ```

4. **Empty Results**
   ```
   Solution: Verify KB volume is mounted and contains files
   ```

### Debugging

```bash
# Check KB service health
curl -H "X-API-Key: $API_KEY" http://kb-service:8000/health

# Test KB search directly  
curl -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"message": "test"}' http://kb-service:8000/search

# Check unified chat with KB tools
./scripts/test.sh --local unified "Search my KB for test"
```

## Comparison to Previous MCP Design

### What Changed ✅

- [x] HTTP-based architecture instead of embedded MCP server
- [x] Separate KB service instead of chat service integration  
- [x] Standard HTTP authentication instead of MCP auth
- [x] 6 focused KB tools instead of complex MCP tools
- [x] Unified chat integration with tool-calling
- [x] Standardized response format across all endpoints

### What Remains the Same ✅

- [x] Direct file system access to KB volume
- [x] Fast search using ripgrep
- [x] Context loading and navigation
- [x] Cross-domain synthesis capabilities
- [x] Same user experience through chat interface

## Conclusion

The HTTP-based KB integration successfully provides:

1. **Clean Architecture** - Separate KB service with standard HTTP APIs
2. **Tool Integration** - Natural LLM tool-calling for KB operations  
3. **Unified Experience** - Single chat endpoint handles all KB interactions
4. **Production Ready** - Standard HTTP patterns, easy deployment/scaling
5. **User-Friendly** - Same conversational interface for KB access

This provides a more maintainable and scalable foundation compared to the original MCP-embedded design while preserving all core functionality.