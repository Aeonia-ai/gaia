# KB Agent API Reference

**Version**: 1.0.0
**Base URL**: `http://kb-service:8000/agent`
**Authentication**: X-API-Key header required

## Overview

The KB Agent API provides intelligent knowledge interpretation capabilities through RESTful endpoints. All endpoints require authentication and return structured JSON responses.

**🎯 Key Distinction from Claude Code Endpoint:**
- **KB Agent** (`/agent/*`): Intelligent knowledge interpretation, decision making, and workflow execution
- **Claude Code** (`/claude-code`): Technical codebase search and file analysis via subprocess execution

The KB Agent transforms static knowledge into actionable intelligence, while Claude Code provides traditional developer tooling for code exploration.

## Authentication

All requests must include an API key in the header:

```http
X-API-Key: your-api-key-here
Content-Type: application/json
```

## Endpoints

### GET /agent/status

Get KB agent status and capabilities.

**Response:**
```json
{
  "status": "success",
  "agent_status": {
    "initialized": true,
    "cache_entries": 0,
    "capabilities": [
      "knowledge_interpretation",
      "workflow_execution",
      "rule_validation",
      "decision_making",
      "information_synthesis"
    ],
    "supported_modes": ["decision", "synthesis", "validation"]
  }
}
```

### POST /agent/interpret

Interpret knowledge from KB and generate intelligent response.

**Request Body:**
```json
{
  "query": "string",              // Required: Query or decision request
  "context_path": "string",       // Optional: KB path to search (default: "/")
  "mode": "string",              // Optional: "decision"|"synthesis"|"validation" (default: "decision")
  "model_hint": "string"         // Optional: Preferred model to use
}
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "interpretation": "string",    // LLM interpretation result
    "model_used": "string",       // Model that processed the request
    "context_files": 0,           // Number of knowledge files loaded
    "mode": "decision",           // Processing mode used
    "cached": false               // Whether result was cached
  },
  "metadata": {
    "user_id": "string",
    "context_path": "string",
    "mode": "string"
  }
}
```

**Mode Details:**

#### Decision Mode
- **Purpose**: Make decisions based on available knowledge
- **Model**: Automatic selection based on complexity
- **Temperature**: 0.7 (balanced creativity/consistency)
- **Use Case**: "How should I handle this combat scenario?"

#### Synthesis Mode
- **Purpose**: Combine information from multiple knowledge sources
- **Model**: Prefers Sonnet for complex reasoning
- **Temperature**: 0.7
- **Use Case**: "Synthesize all combat mechanics across different game modes"

#### Validation Mode
- **Purpose**: Validate actions against established rules
- **Model**: Haiku for fast, consistent responses
- **Temperature**: 0.3 (high consistency)
- **Use Case**: "Is this action allowed by the game rules?"

### POST /agent/workflow

Execute a workflow defined in markdown.

**Request Body:**
```json
{
  "workflow_path": "string",     // Required: Path to workflow markdown file
  "parameters": {}               // Optional: Parameters to pass to workflow
}
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "workflow": "string",         // Path to executed workflow
    "parameters": {},             // Parameters that were used
    "execution_result": "string", // Step-by-step execution results
    "model_used": "string"        // Model used for execution
  },
  "metadata": {
    "user_id": "string",
    "workflow_path": "string",
    "parameters_count": 0
  }
}
```

**Workflow Format:**

Workflows are markdown files with structured content:

```markdown
# Workflow Name

Brief description of what this workflow does.

## Steps:
1. First step description
2. Second step description
3. Final step description

## Parameters:
- param1: Description of parameter 1
- param2: Description of parameter 2

## Expected Output:
Description of what the workflow should produce.
```

### POST /agent/validate

Validate an action against rules defined in KB.

**Request Body:**
```json
{
  "action": "string",           // Required: Action to validate
  "rules_path": "string",       // Required: KB path containing rules
  "context": {}                 // Optional: Additional context for validation
}
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "action": "string",          // Action that was validated
    "validation_result": "string", // VALID/INVALID with explanation
    "rules_checked": 0,          // Number of rule files examined
    "model_used": "string"       // Model used for validation
  },
  "metadata": {
    "user_id": "string",
    "action": "string",
    "rules_path": "string"
  }
}
```

### POST /agent/cache/clear

Clear the KB agent's rule cache.

**Response:**
```json
{
  "status": "success",
  "message": "Cache cleared: N entries removed"
}
```

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error description"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (missing/invalid API key)
- `500`: Internal Server Error (agent/LLM failure)

## Rate Limiting

- **Concurrent Requests**: 10 per user
- **Request Timeout**: 30 seconds
- **Model Switching**: Automatic fallback if primary model unavailable

## Performance Notes

### Response Times
- **Decision Mode**: 1-2 seconds typical
- **Synthesis Mode**: 2-4 seconds typical (more complex)
- **Validation Mode**: 0.5-1 seconds typical (optimized for speed)
- **Workflow Execution**: 3-5 seconds typical (depends on complexity)

### Caching
- **Rule Cache**: Successful interpretations cached for repeat queries
- **Cache Key**: `{context_path}:{query_first_50_chars}`
- **Cache TTL**: Session-based (cleared on service restart)

### Universal Knowledge Loading
- **Index Support**: Works with both `+index.md` files and regular `.md` files
- **Recursive Search**: Automatically traverses subdirectories
- **Mixed Structures**: Handles directories with both indexed and non-indexed content
- **Backward Compatibility**: 100% compatible with existing KB structures
- **Performance**: Direct file access without index dependency requirements

### Model Selection

The agent automatically selects models based on:

| Operation | Preferred Model | Reason |
|-----------|----------------|---------|
| Validation | claude-3-5-haiku-20241022 | Fast, consistent responses |
| Simple Decisions | claude-3-5-haiku-20241022 | Cost-effective for basic queries |
| Complex Synthesis | claude-3-5-sonnet-20241022 | Superior reasoning capabilities |
| Workflows | claude-3-5-sonnet-20241022 | Multi-step execution handling |

## Integration Examples

### Python Client
```python
import requests

class KBAgentClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }

    def interpret(self, query, context_path="/", mode="decision"):
        response = requests.post(
            f"{self.base_url}/agent/interpret",
            json={
                "query": query,
                "context_path": context_path,
                "mode": mode
            },
            headers=self.headers
        )
        return response.json()

    def execute_workflow(self, workflow_path, parameters={}):
        response = requests.post(
            f"{self.base_url}/agent/workflow",
            json={
                "workflow_path": workflow_path,
                "parameters": parameters
            },
            headers=self.headers
        )
        return response.json()

# Usage
client = KBAgentClient("http://kb-service:8000", "your-api-key")
result = client.interpret("How should I handle player combat?", "/shared/combat")
```

### JavaScript/Node.js Client
```javascript
class KBAgentClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.headers = {
            'X-API-Key': apiKey,
            'Content-Type': 'application/json'
        };
    }

    async interpret(query, contextPath = "/", mode = "decision") {
        const response = await fetch(`${this.baseUrl}/agent/interpret`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                query,
                context_path: contextPath,
                mode
            })
        });
        return response.json();
    }

    async validateAction(action, rulesPath, context = {}) {
        const response = await fetch(`${this.baseUrl}/agent/validate`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                action,
                rules_path: rulesPath,
                context
            })
        });
        return response.json();
    }
}

// Usage
const client = new KBAgentClient("http://kb-service:8000", "your-api-key");
const result = await client.interpret("Should I allow this spell casting?");
```

## Best Practices

### Query Optimization
- **Be Specific**: Clear, specific queries get better responses
- **Use Context Paths**: Narrow context improves relevance and speed
- **Choose Appropriate Mode**: Match mode to your use case

### Workflow Design
- **Clear Steps**: Use numbered lists for workflow steps
- **Document Parameters**: Always describe expected parameters
- **Expected Outputs**: Define what the workflow should produce

### Error Handling
- **Timeout Handling**: Set appropriate timeouts for your use case
- **Graceful Degradation**: Handle agent failures gracefully
- **Retry Logic**: Implement exponential backoff for retries

### Performance
- **Cache Awareness**: Similar queries may be cached for faster responses
- **Batch Operations**: Group related queries when possible
- **Monitor Response Times**: Track performance for capacity planning