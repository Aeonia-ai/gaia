# FastAPI to MCP Integration Guide

## Overview

The mcp-agent framework in Gaia provides the ability to wrap existing FastAPI services as MCP (Model Context Protocol) servers, making them available as tools for AI agents.

## How It Works

### 1. MCP Server Wrapper

MCP servers expose tools that AI agents can discover and use. Any FastAPI endpoint can be wrapped as an MCP tool:

```python
# Your existing FastAPI service
from fastapi import FastAPI

app = FastAPI()

@app.post("/analyze")
async def analyze_data(data: str, threshold: float = 0.5):
    """Analyze data and return insights"""
    # Your business logic
    return {"result": "analysis", "confidence": 0.85}

@app.get("/status/{service_id}")
async def get_service_status(service_id: str):
    """Get current status of a service"""
    return {"service": service_id, "status": "healthy"}
```

### 2. MCP Server Configuration

Create an MCP server that wraps your FastAPI endpoints:

```yaml
# mcp_server_config.yaml
name: "business-tools"
description: "Business logic tools from our FastAPI services"

tools:
  - name: "analyze_data"
    description: "Analyze data and return insights"
    input_schema:
      type: object
      properties:
        data:
          type: string
          description: "Data to analyze"
        threshold:
          type: number
          description: "Analysis threshold"
      required: ["data"]
    
  - name: "get_service_status"
    description: "Get current status of a service"
    input_schema:
      type: object
      properties:
        service_id:
          type: string
          description: "ID of the service to check"
      required: ["service_id"]
```

### 3. Integration with Gaia

The `/mcp-agent` endpoint can use these wrapped services:

```python
# Request to Gaia with MCP tools
POST /api/v1/chat/mcp-agent
{
    "message": "Check if the payment service is healthy and analyze recent transaction data",
    "mcp_servers": ["business-tools"]
}

# The AI can now:
# 1. Call get_service_status("payment-service")
# 2. Call analyze_data(transaction_data)
# 3. Combine results in its response
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FASTAPI → MCP ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Existing Services                  MCP Layer                   AI Agent    │
│  ┌──────────────┐                 ┌─────────────┐             ┌─────────┐ │
│  │   FastAPI    │                 │ MCP Server  │             │  Claude │ │
│  │   Service    │◄────────────────│   Wrapper   │◄────────────│   with  │ │
│  │              │                 │             │             │  Tools  │ │
│  │ POST /analyze│  HTTP Calls     │ - Discovery │  Tool Calls │         │ │
│  │ GET /status  │                 │ - Schema    │             │         │ │
│  │ PUT /update  │                 │ - Execution │             │         │ │
│  └──────────────┘                 └─────────────┘             └─────────┘ │
│         ▲                                                                   │
│         │                                                                   │
│         └─────────── Your existing business logic remains unchanged        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Benefits

### 1. **Leverage Existing Code**
- No need to rewrite business logic
- Existing FastAPI validations work
- Authentication/authorization preserved

### 2. **AI-Accessible APIs**
- AI can discover available tools
- Schema validation for AI calls
- Automatic error handling

### 3. **Composability**
- AI can chain multiple tool calls
- Combine results intelligently
- Create complex workflows

## Implementation Example

### Step 1: Create MCP Wrapper

```python
# mcp_wrapper.py
from mcp import Server, Tool
import httpx

class FastAPIWrapper(Server):
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def analyze_data(self, data: str, threshold: float = 0.5):
        """Wrapper for FastAPI analyze endpoint"""
        response = await self.client.post(
            f"{self.base_url}/analyze",
            json={"data": data, "threshold": threshold}
        )
        return response.json()
    
    async def get_service_status(self, service_id: str):
        """Wrapper for FastAPI status endpoint"""
        response = await self.client.get(
            f"{self.base_url}/status/{service_id}"
        )
        return response.json()
```

### Step 2: Register with mcp-agent

```yaml
# mcp_agent.config.yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-5

mcp_servers:
  # Existing MCP servers
  - filesystem:
      module: mcp_server_filesystem
  
  # Your wrapped FastAPI service
  - business_tools:
      module: mcp_wrapper
      args:
        base_url: "http://your-fastapi-service:8000"
```

### Step 3: Use in Conversations

```python
# User query
"Can you check if our payment processing is working and analyze 
 the last hour of transactions for anomalies?"

# AI response (using tools behind the scenes)
"I'll check the payment service status and analyze recent transactions.

[Calling get_service_status("payment-service")]
✓ Payment service is healthy with 99.9% uptime

[Calling analyze_data(last_hour_transactions)]
✓ Analyzed 1,247 transactions:
  - No anomalies detected
  - Average transaction: $47.23
  - Peak activity: 2:15 PM

Everything looks normal with your payment processing system."
```

## Advanced Patterns

### 1. **Conditional Tool Access**
```python
# Only expose certain tools based on user permissions
if user.has_permission("admin"):
    mcp_servers.append("admin-tools")
```

### 2. **Dynamic Tool Generation**
```python
# Generate MCP tools from OpenAPI specs
def create_mcp_from_openapi(spec_url: str):
    spec = load_openapi_spec(spec_url)
    return generate_mcp_tools(spec)
```

### 3. **Caching and Optimization**
```python
# Cache frequently used tool results
@cache(ttl=300)  # 5 minute cache
async def get_dashboard_metrics():
    return await wrapped_api.get_metrics()
```

## Performance Considerations

### Current Implementation
- **Initial overhead**: 2-3s for mcp-agent initialization
- **Per-tool call**: 50-200ms depending on FastAPI endpoint
- **Total latency**: 3-5s for tool-using requests

### Optimization Strategies
1. **Use hot-loading**: Keep mcp-agent initialized
2. **Batch operations**: Multiple tool calls in parallel
3. **Smart routing**: Only use MCP when tools needed
4. **Cache results**: For read-heavy operations

## Security Considerations

### 1. **Authentication Propagation**
```python
# Forward user auth to wrapped services
headers = {"Authorization": f"Bearer {user_token}"}
response = await client.post(url, headers=headers)
```

### 2. **Rate Limiting**
```python
# Implement per-user tool usage limits
@rate_limit(calls=100, period="hour")
async def wrapped_tool_call(user_id: str):
    # Tool execution
```

### 3. **Audit Logging**
```python
# Log all tool usage for compliance
logger.info(f"Tool called: {tool_name} by {user_id}")
```

## Best Practices

1. **Start Simple**: Wrap one or two critical endpoints first
2. **Document Tools**: Clear descriptions help AI use tools correctly
3. **Handle Errors**: Graceful fallbacks when tools fail
4. **Monitor Usage**: Track which tools are most valuable
5. **Iterative Improvement**: Refine tool schemas based on usage

## Conclusion

The FastAPI → MCP integration in Gaia allows you to:
- Make existing APIs AI-accessible without code changes
- Create powerful agent workflows using your business logic
- Maintain performance with intelligent routing

Use the `/mcp-agent` endpoint when you need tool access, and faster endpoints like `/ultrafast-redis-v3` for regular chat.