# FastMCP Integration: Claude Code Setup Guide

## Overview

The GAIA KB service now exposes MCP tools via HTTP using FastMCP, enabling Claude Code to directly access the Knowledge Base with automatic tool discovery.

## Architecture

```
┌──────────────┐     HTTP/MCP      ┌─────────────────┐
│ Claude Code  │ ◄──────────────► │ kb-docs:8005/mcp│
│    (CLI)     │                   │ (Documentation) │
└──────────────┘                   └─────────────────┘
       │
       │         HTTP/MCP      ┌─────────────────┐
       └────────────────────► │ kb-service:8001/mcp│
                               │ (Game Content)   │
                               └─────────────────┘
```

## Available MCP Tools

Both KB instances provide the same 9 tools:

1. **search_kb** - Fast full-text search using ripgrep (keyword-based)
2. **search_semantic** - AI-powered semantic search using pgvector (conceptual queries)
3. **read_file** - Read specific KB files with frontmatter parsing
4. **load_context** - Load KOS contexts with dependencies
5. **list_directory** - List files in KB directories
6. **navigate_index** - Navigate hierarchical index system
7. **synthesize_contexts** - Cross-domain insight generation
8. **delegate_tasks** - Parallel multi-task execution
9. **get_active_threads** - Get active KOS work threads

## Claude Code MCP Configuration

### Method 1: Add to Claude Code Settings

Add these MCP servers to your Claude Code configuration file (`~/.claude/config.json`):

```json
{
  "mcpServers": {
    "gaia-kb-docs": {
      "transport": "http",
      "url": "http://localhost:8005/mcp",
      "name": "GAIA KB Documentation",
      "description": "Access Obsidian Vault documentation (3,319 files)"
    },
    "gaia-kb-game": {
      "transport": "http",
      "url": "http://localhost:8001/mcp",
      "name": "GAIA KB Game Content",
      "description": "Access game content (experiences, waypoints, lore)"
    }
  }
}
```

### Method 2: Using Claude Code CLI

```bash
# Add kb-docs server
claude code mcp add gaia-kb-docs \
  --transport http \
  --url http://localhost:8005/mcp \
  --description "GAIA Documentation KB"

# Add kb-service server
claude code mcp add gaia-kb-game \
  --transport http \
  --url http://localhost:8001/mcp \
  --description "GAIA Game Content KB"

# Verify servers are added
claude code mcp list
```

## Testing MCP Endpoints

### Health Check

```bash
# Check kb-docs MCP endpoint
curl http://localhost:8005/mcp/health

# Check kb-service MCP endpoint
curl http://localhost:8001/mcp/health
```

### Tool Discovery

```bash
# List available tools (kb-docs)
curl http://localhost:8005/mcp/tools | jq

# List available tools (kb-service)
curl http://localhost:8001/mcp/tools | jq
```

### Test a Tool

```bash
# Search documentation
curl -X POST http://localhost:8005/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "search_kb",
    "arguments": {
      "query": "authentication",
      "limit": 5
    }
  }' | jq

# Search game content
curl -X POST http://localhost:8001/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "search_kb",
    "arguments": {
      "query": "waypoint",
      "contexts": ["experiences/wylding-woods"],
      "limit": 10
    }
  }' | jq
```

## Using MCP Tools in Claude Code

Once configured, Claude Code automatically discovers and uses KB tools:

### Example 1: Search Documentation

```
User: "Search the docs for how authentication works"

Claude Code: Uses search_kb tool on kb-docs
→ Finds authentication guide
→ Returns relevant excerpts
```

### Example 2: Semantic Search

```
User: "Find information about chat service architecture"

Claude Code: Uses search_semantic tool on kb-docs
→ Finds semantically related content
→ Returns results with relevance scores
→ No exact "chat service architecture" keyword needed
```

### Example 3: Read Game Content

```
User: "Read the Wylding Woods story file"

Claude Code: Uses read_file tool on kb-game
→ Returns markdown content with frontmatter
→ Parses game lore and mission data
```

### Example 4: Multi-Task Workflow

```
User: "Find all waypoints in Wylding Woods and check their mission requirements"

Claude Code: Uses delegate_tasks tool
→ Task 1: search_kb for waypoints
→ Task 2: read_file for each waypoint
→ Task 3: synthesize_contexts for mission overview
→ Returns comprehensive report
```

## Differences Between kb-docs and kb-service

| Aspect | kb-docs (8005) | kb-service (8001) |
|--------|----------------|-------------------|
| **Content** | Developer documentation, API references | Game experiences, waypoints, lore |
| **Storage** | Direct filesystem mount (instant updates) | Git-synchronized repository |
| **Files** | 3,319 files (Obsidian Vault) | ~76 files (game content) |
| **Use Case** | Technical documentation, guides | Game design, content management |
| **Semantic Search** | Enabled (1,696 markdown files indexed) | Enabled (all markdown files) |
| **Write Access** | Read-write (direct filesystem) | Read-write (Git commits) |

## Semantic Search vs. Full-Text Search

### When to use `search_kb` (full-text):
- You know exact keywords or phrases
- Looking for specific code, commands, or identifiers
- Fast searches with regex patterns
- Searching for file names or paths

### When to use `search_semantic` (conceptual):
- Natural language queries: "how do users authenticate?"
- Conceptual searches without knowing exact terms
- Finding related content by meaning, not keywords
- Exploring topics you can't describe with exact words

### How `search_semantic` works:
- Uses **pgvector** extension in PostgreSQL for vector similarity search
- Embeddings generated with **sentence-transformers** (all-MiniLM-L6-v2 model)
- Returns relevance scores (0.0-1.0) showing how semantically similar results are
- Persistent indexing - no re-indexing needed after restarts
- Incremental updates - only changed files are re-indexed

## Troubleshooting

### MCP Endpoint Not Responding

**Common Causes:**
1. **FastMCP lifespan integration bug** - ✅ FIXED (Nov 2025)
   - Symptom: "Task group is not initialized" error
   - Cause: Different MCP app instances for lifespan vs mounting
   - Solution: Use same `http_mcp_app` instance everywhere (commit `0f6f69e`)

2. **Service startup issues**:
```bash
# Check if kb-docs container is running
docker compose ps kb-docs

# Check for errors in logs
docker compose logs kb-docs --tail 50

# Verify pgvector indexing status
curl http://localhost:8005/health

# Test MCP endpoint specifically
curl -X POST http://localhost:8005/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"ping","id":1}' \
  --max-time 5

# Restart kb-docs if needed
docker compose restart kb-docs
```

### Tools Not Appearing in Claude Code

```bash
# Verify MCP configuration
claude code mcp list

# Re-add servers if needed
claude code mcp remove gaia-kb-docs
claude code mcp add gaia-kb-docs --transport http --url http://localhost:8005/mcp

# Check Claude Code can reach endpoint
curl http://localhost:8005/mcp/health
```

### Slow Search Results

1. **Initial indexing**: First startup indexes all files (can take time for large KBs with 1000+ files)
2. **Incremental indexing**: Subsequent startups only index changed files (much faster)
3. **Database queries**: Check PostgreSQL performance with `docker stats gaia-db-1`
4. **Indexing in progress**: ✅ Service remains responsive during indexing (fixed Nov 2025)
   - MCP endpoints respond in ~200ms even during active indexing
   - Uses `asyncio.to_thread()` to prevent event loop blocking
   - See `docs/scratchpad/semantic-search-pgvector-debugging-2025-11-03.md` for details

## Production Deployment

For production environments (Fly.io, AWS, etc.):

1. **Update MCP URLs** to use public endpoints:
```json
{
  "url": "https://gaia-kb-docs-dev.fly.dev/mcp"
}
```

2. **Add Authentication** (if needed):
```json
{
  "transport": "http",
  "url": "https://gaia-kb-docs-dev.fly.dev/mcp",
  "headers": {
    "X-API-Key": "${GAIA_API_KEY}"
  }
}
```

3. **Enable HTTPS** for secure MCP communication

## Performance Considerations

- **Parallel execution**: Use `delegate_tasks` for batch operations (5x faster)
- **Result caching**: Search results cached in Redis (5-minute TTL)
- **Context loading**: Cached contexts persist across sessions
- **Semantic search**:
  - pgvector HNSW indexes for sub-second searches
  - Persistent storage in PostgreSQL (no re-indexing on restart)
  - Incremental indexing (only changed files are re-indexed)
  - 384-dimensional embeddings via sentence-transformers

## Next Steps

1. **Test MCP tools** from Claude Code CLI
2. **Create workflows** combining multiple tools
3. **Configure semantic search** for your content
4. **Add custom tools** by extending `kb_fastmcp_server.py`

## References

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol Spec](https://modelcontextprotocol.io/docs)
- [KB Semantic Search Implementation](./kb-semantic-search-implementation.md)
- [KB Git Sync Guide](./kb-git-sync-guide.md)
