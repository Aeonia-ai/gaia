# KB Service HTTP API Reference



**Service**: KB Service  
**Base URL**: `http://kb-service:8000`  
**Authentication**: X-API-Key header  
**Response Format**: `{status, response, metadata}`

## Endpoints

### POST /search
Search KB content using full-text search.

**Request:**
```json
{"message": "search query"}
```

**Response:**
```json
{
  "status": "success",
  "response": "Formatted search results...",
  "metadata": {
    "total_results": 5,
    "query": "search query"
  }
}
```

**Usage in KB Tools:**
- `search_knowledge_base()` - General knowledge base search
- `load_kos_context()` - KOS context loading with specific patterns

### POST /read  
Read a specific KB file.

**Request:**
```json
{"message": "/path/to/file.md"}
```

**Response:**
```json
{
  "status": "success", 
  "response": "File content with metadata...",
  "metadata": {
    "file_path": "/path/to/file.md"
  }
}
```

**Usage in KB Tools:**
- `read_kb_file()` - Direct file reading

### POST /list
List directory contents.

**Request:**
```json
{"message": "/directory/path"}
```

**Response:**
```json
{
  "status": "success",
  "response": "Directory listing...", 
  "metadata": {
    "directory": "/directory/path"
  }
}
```

**Usage in KB Tools:**
- `list_kb_directory()` - Directory navigation

### POST /context
Load context around a topic.

**Request:**
```json
{"message": "topic name (depth: 2)"}
```

**Response:**
```json
{
  "status": "success",
  "response": "Context information...",
  "metadata": {
    "context_loaded": true
  }
}
```

**Usage in KB Tools:**
- `load_kb_context()` - Topic context loading

### POST /synthesize
Synthesize information from multiple sources.

**Request:**
```json
{"message": "Synthesize from: source1, source2 focusing on: theme"}
```

**Response:**
```json
{
  "status": "success",
  "response": "Synthesis results...",
  "metadata": {
    "sources": ["source1", "source2"]
  }
}
```

**Usage in KB Tools:**
- `synthesize_kb_information()` - Cross-domain information synthesis

### POST /threads
Get active KOS threads.

**Request:**
```json
{"message": "filter criteria"}
```

**Response:**
```json
{
  "status": "success",
  "response": "Thread information...",
  "metadata": {
    "total_threads": 3
  }
}
```

**Usage in KB Tools:**
- Called by multiple tools for thread management

## Error Handling

All endpoints return errors in this format:
```json
{
  "status": "error",
  "response": "Error description",
  "metadata": {}
}
```

## Authentication Example

```bash
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "search query"}' \
  http://kb-service:8000/search
```

## KB Tools Integration

These HTTP endpoints are accessed through the LLM tool-calling system via `kb_tools.py`:

1. **Tool Call**: LLM calls KB tool (e.g., `search_knowledge_base`)
2. **HTTP Request**: `KBToolExecutor` makes HTTP call to appropriate endpoint
3. **Response Processing**: HTTP response formatted for LLM consumption
4. **Final Response**: LLM generates natural language response using KB data

## Testing

```bash
# Direct endpoint testing
curl -X POST -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"message": "test"}' http://kb-service:8000/search

# Via unified chat (recommended)
./scripts/test.sh --local unified "Search my knowledge base for test"
```

## Service Architecture

The KB service runs independently from the chat service:
- **Separation of Concerns**: KB operations isolated from chat logic
- **Horizontal Scaling**: KB service can be scaled independently
- **Standard HTTP**: Uses REST patterns for easy debugging and integration
- **Tool Integration**: Natural fit with LLM tool-calling systems