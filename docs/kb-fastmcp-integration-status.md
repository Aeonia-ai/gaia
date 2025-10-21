# FastMCP Integration Status

## Current State: ✅ COMPLETE - Production Ready with pgvector

**Last Updated**: 2025-10-20 (pgvector migration complete)

### ✅ Completed
1. **FastMCP dependency added** - Version 0.2.0+ in requirements.txt
2. **MCP protocol adapter created** - `app/services/kb/kb_fastmcp_server.py` with 9 tools
3. **FastAPI integration implemented** - Proper mounting at `/mcp` endpoint with lifespan coordination
4. **Tools defined** - All 9 KB tools wrapped with MCP protocol:
   - `search_kb` - Full-text search with ripgrep (keyword-based)
   - `search_semantic` - **NEW** AI-powered semantic search with pgvector
   - `read_file` - File reading with frontmatter parsing
   - `load_context` - KOS context loading
   - `list_directory` - Directory listings
   - `navigate_index` - Hierarchical navigation
   - `synthesize_contexts` - Cross-domain insights
   - `delegate_tasks` - Parallel task execution
   - `get_active_threads` - Active work threads
5. **pgvector migration completed** - Replaced ChromaDB with PostgreSQL native vector search
6. **Persistent indexing** - Indexes survive container restarts, incremental updates only
7. **FastMCP lifespan properly initialized** - Nested async context managers pattern
8. **Service running successfully** - MCP endpoint responding with JSON-RPC protocol
9. **Full testing completed** - 55,681 chunks indexed from 1,825 files, semantic search operational

### ✅ Resolved Issues (pgvector Migration)

#### Issue 1: ChromaDB Ephemeral Storage (SOLVED)
**Problem**: ChromaDB used in-memory storage, requiring full re-indexing on every restart
- 55,681 chunks took ~53 minutes to index
- Lost all indexes on container restart
- No incremental indexing capability

**Solution**: Migrated to pgvector with PostgreSQL persistence
- Created migrations 006 (metadata tables) and 007 (vector columns)
- Switched from ChromaDB to sentence-transformers + pgvector
- Indexes persist in database, survive restarts
- Incremental indexing with mtime comparison (60s tolerance for Docker volumes)

#### Issue 2: FastMCP Lifespan Not Initialized (FIXED)
**Problem**: StreamableHTTPSessionManager task group was not initialized
- Both SSE and streamable-http transports require lifespan initialization
- Mounting as sub-app doesn't automatically start lifespans

**Solution**: Nested async context managers pattern (Perplexity-verified):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle - includes FastMCP lifespan if available"""
    if HAS_FASTMCP and mcp_app and hasattr(mcp_app, 'lifespan'):
        async with mcp_app.lifespan(app):
            async with kb_service_lifespan(app):
                yield
    else:
        async with kb_service_lifespan(app):
            yield
```

#### Issue 3: asyncpg Vector Type Registration (SOLVED)
**Problem**: Python lists not converting to PostgreSQL vectors
- Error: "invalid input for query argument $5: [...] (expected str, got list)"
- `::vector` cast alone wasn't sufficient

**Solution**: Added explicit pgvector type registration for asyncpg
```python
from pgvector.asyncpg import register_vector
async with db_pool.acquire() as conn:
    await register_vector(conn)  # Required for each connection
```

### 🔧 Integration Code (Verified Working)

**kb_fastmcp_server.py** (Helper function):
```python
def get_mcp_app_for_mount():
    """Get FastMCP app configured for mounting at /mcp."""
    return mcp.http_app(path="/")  # Root path internally
```

**main.py** (Mount configuration):
```python
from .kb_fastmcp_server import get_mcp_app_for_mount

mcp_app = get_mcp_app_for_mount()
app.mount("/mcp", mcp_app)  # Final endpoint: /mcp/
```

**Perplexity-verified approach**: Use `path="/"` in FastMCP, mount at `/mcp` in FastAPI to avoid double-nesting.

### 📊 Test Results

**Health Endpoint**: ✅ Working
```bash
curl http://localhost:8005/health
# {"service":"kb","status":"healthy","version":"1.0.0"}
```

**MCP Endpoint**: ✅ Working
```bash
curl http://localhost:8005/mcp/
# Returns MCP protocol handshake
```

**Semantic Search (REST)**: ✅ Working
```bash
curl http://localhost:8005/search -d '{"message":"chat service"}' -H "Content-Type: application/json"
# Returns 20 results with 0.81-0.70 relevance scores
```

**Semantic Search (MCP)**: ✅ Working
```bash
# Available via search_semantic tool in Claude Code MCP client
# Returns semantically relevant chunks with similarity scores
```

**OpenAPI Docs**: ✅ Working
```bash
curl http://localhost:8005/docs
# Returns FastAPI documentation
```

### 🎯 Next Steps (All Core Features Complete)

1. ✅ **Apply migrations to remote databases** (dev/staging/prod)
   - Migration 006: Metadata tables
   - Migration 007: pgvector columns and HNSW indexes

2. ✅ **Deploy to production**:
   - Rebuild kb-docs and kb-service containers
   - Verify pgvector indexing works remotely
   - Test MCP tools in production

3. **Optional Enhancements**:
   - Add caching for embedding generation (currently computed per search)
   - Implement hybrid search (combine keyword + semantic)
   - Add query result highlighting
   - Create performance benchmarks

### 📁 Modified Files (pgvector Migration)

- `requirements.txt` - Added fastmcp>=0.2.0, sentence-transformers, pgvector
- `migrations/006_create_semantic_search_metadata_tables.sql` - **NEW** - Metadata tables
- `migrations/007_add_pgvector_embeddings.sql` - **NEW** - Vector columns and HNSW indexes
- `app/services/kb/kb_fastmcp_server.py` - MCP adapter with **9 tools** (added search_semantic)
- `app/services/kb/kb_semantic_search.py` - Replaced ChromaDB with pgvector + sentence-transformers
- `app/services/kb/main.py` - Added FastMCP mounting logic
- `docker-compose.yml` - Updated PostgreSQL to pgvector/pgvector:pg15
- `docs/kb-fastmcp-claude-code-setup.md` - Configuration guide (updated for 9 tools)
- `docs/kb-fastmcp-integration-status.md` - This file (updated for pgvector)

### 🐛 Known Issues (Minor)

1. **Incremental indexing mtime tolerance** - Fixed at 60 seconds for Docker volume mounts
   - May need adjustment for different environments
   - Can be tuned in `kb_semantic_search.py` if needed

2. **Background indexing can temporarily block searches** - During initial indexing
   - Searches blocked while database writes are in progress
   - Resolves automatically once indexing completes
   - Only happens on first startup or when many files changed

3. **No embedding cache** - Embeddings generated on every search
   - Could add caching for frequently used queries
   - Trade-off: memory usage vs computation time

### 💡 Architectural Insights

**Why pgvector Migration Was Worth It**:
- **Persistent storage**: No re-indexing on restart (was ~53 min, now 0 min)
- **Incremental updates**: Only changed files re-indexed (60s mtime tolerance)
- **Transactional consistency**: Atomic updates without sync complexity
- **Simpler architecture**: One database instead of two (PostgreSQL + ChromaDB)
- **Better performance**: HNSW indexes for sub-second searches
- **No vendor lock-in**: Standard PostgreSQL extension

**Why FastMCP Integration Matters**:
- **Auto-discovery**: Claude Code discovers tools automatically via MCP protocol
- **Type safety**: Pydantic models ensure correct parameter types
- **Streaming**: MCP supports streaming responses for long-running operations
- **Standard protocol**: Works with any MCP-compatible client (not just Claude)

**Alternative Approaches Considered**:
1. **ChromaDB ephemeral** - Simple but re-indexes on every restart (rejected)
2. **ChromaDB persistent** - File-based storage, harder to query (not tested)
3. **Separate vector service** - More complexity, network overhead (rejected)

**Chosen: pgvector with PostgreSQL** - Best balance of simplicity, performance, and persistence

### 📚 References

- [FastMCP Documentation](https://gofastmcp.com/)
- [FastMCP + FastAPI Integration](https://gofastmcp.com/integrations/fastapi)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Claude Code MCP Configuration](https://docs.claude.ai/en/docs/claude-code)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [sentence-transformers](https://www.sbert.net/)
- [PostgreSQL HNSW Indexing](https://github.com/pgvector/pgvector#hnsw)

### 🕐 Migration Timeline

- **Oct 13, 2025**: Started FastMCP integration, discovered ChromaDB issues
- **Oct 16, 2025**: Created pgvector migration plan
- **Oct 20, 2025**: Completed pgvector migration
  - Applied migrations 006 and 007
  - Replaced ChromaDB with sentence-transformers + pgvector
  - Fixed asyncpg type registration
  - Indexed 55,681 chunks from 1,825 files
  - Added 9th MCP tool (search_semantic)
  - Fixed incremental indexing mtime tolerance
  - Updated documentation
