# Intelligent Chat Routing

## Overview

The intelligent chat routing system automatically routes messages to the optimal endpoint based on complexity, eliminating the need for users to choose between different chat endpoints.

## Architecture

### Single LLM Call Approach

Instead of making separate calls for classification and response, we use a single LLM call that can:
1. **Respond directly** for simple messages (no classification overhead)
2. **Classify and route** for complex messages that need special handling

### Routing Paths

1. **Direct Response** (~1s)
   - Simple greetings, questions, general chat
   - LLM responds immediately without classification
   - No routing overhead

2. **Fast Path** (~1s)
   - Messages needing basic processing
   - Routes to `/chat/direct` endpoint
   - Minimal overhead

3. **Tool Path** (~2-3s)
   - Messages requiring MCP tools
   - Routes to `/chat/mcp-agent-hot`
   - Uses hot-loaded agents

4. **Orchestrated Path** (~3-5s)
   - Complex multi-domain requests
   - Routes to `/chat/mcp-agent`
   - Full multiagent orchestration

## Implementation

### Intelligent Router

```python
# Single LLM call with optional classification
response = await multi_provider_selector.chat_completion(
    messages=messages,
    model="claude-3-5-sonnet-20241022",
    tools=[{"type": "function", "function": classification_function}],
    tool_choice="auto",  # LLM decides whether to classify
    temperature=0.7,
    max_tokens=2000  # Enough for full response
)

if response.get("tool_calls"):
    # Complex message - route to appropriate endpoint
    return route_to_endpoint(classification)
else:
    # Simple message - return direct response
    return response["response"]
```

### Smart Prompt

The system prompt encourages direct responses:

```
For messages you can answer directly without needing special tools or multiple agents:
- Just respond naturally
- Don't use the classification function

ONLY use the classify_chat_complexity function when:
- The request explicitly needs tools
- Multiple specialist perspectives are needed
- Complex orchestration is required
```

## Language Support

The system works with all languages:
- No English-specific patterns
- LLM understands context in any language
- Universal routing logic

## Usage

### Intelligent Endpoint

```bash
# Automatically routes based on complexity
curl -X POST https://gaia-gateway-dev.fly.dev/chat/intelligent \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Hello!"}'  # Direct response ~1s

curl -X POST https://gaia-gateway-dev.fly.dev/chat/intelligent \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Create a fantasy world with multiple kingdoms"}'  # Orchestrated ~3s
```

### Fast Endpoint (No Routing)

```bash
# Bypasses all routing for guaranteed speed
curl -X POST https://gaia-gateway-dev.fly.dev/chat/fast \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "What is the weather?"}'  # Always ~1s
```

## Performance

- **Simple messages**: ~1s (same as direct endpoint)
- **Tool-required messages**: ~2-3s (classification + execution)
- **Complex orchestration**: ~3-5s (classification + multiagent)

## Testing

Test intelligent routing performance:

```bash
./scripts/test-intelligent-routing-performance.sh https://gaia-chat-dev.fly.dev
```

Expected results:
- Ultra-fast responses for greetings: <1s
- Fast responses for simple questions: ~1s
- Moderate for tool usage: ~2s
- Complex for orchestration: ~3s

## Metrics

Get routing metrics:

```bash
curl https://gaia-gateway-dev.fly.dev/chat/intelligent/metrics \
  -H "X-API-Key: $API_KEY"
```

Returns:
- Routing distribution (simple/moderate/complex)
- Average classification times
- Total requests processed
- Error rates

## Implementation Files

- `app/services/chat/intelligent_router.py` - Classification logic
- `app/services/chat/intelligent_chat.py` - Routing service
- `scripts/test-intelligent-routing.sh` - Routing test
- `scripts/test-intelligent-routing-performance.sh` - Performance test