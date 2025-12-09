# Intelligent Chat Routing

## Overview

The intelligent chat routing system automatically routes messages to the optimal endpoint based on complexity, eliminating the need for users to choose between different chat endpoints. This is **currently implemented** and operational in the GAIA platform.

## API Version Note

**Both `/api/v1/chat` and `/api/v0.3/chat` use the SAME intelligent routing system.**

The only differences are:
- **v0.3**: Cleaner response format without provider details
- **v1**: Maintains backward compatibility with original format
- **Both**: Route to `/chat/unified` endpoint internally
- **Both**: Support streaming, KB tools, and all routing features

## Architecture

### Single LLM Call Approach

Instead of making separate calls for classification and response, we use a single LLM call with Claude Sonnet 4.5 that can:
1. **Respond directly** for simple messages (ultra-fast path ~0.5s)
2. **Classify and route** for complex messages that need special handling

**Implementation Location**: `app/services/chat/intelligent_router.py`

### Routing Paths

1. **Ultra-Fast Direct Response** (~0.5s)
   - Simple greetings, questions, general chat
   - LLM responds immediately without classification
   - No routing overhead - marked as `DIRECT_RESPONSE`

2. **Simple Chat Path** (~1s)
   - Messages needing basic processing
   - Routes to `/chat/direct` endpoint  
   - Minimal overhead

3. **KB + Tools Path** (~2-3s)
   - Messages requiring Knowledge Base access or MCP tools
   - Routes to `/chat/mcp-agent-hot`
   - Uses hot-loaded agents with KB tools available

4. **Complex Multi-Agent Path** (~3-5s)
   - Complex multi-domain requests requiring expert perspectives
   - Routes to `/chat/mcp-agent`
   - Full multiagent orchestration with specialized agents

## Implementation

### Intelligent Router

```python
# Single LLM call with optional classification
response = await multi_provider_selector.chat_completion(
    messages=messages,
    model="claude-sonnet-4-5",
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

## Knowledge Base Integration

When users request KB operations, the routing system automatically provides KB tools to the LLM:

**KB Tools Available**:
- `search_knowledge_base` - "Search my notes on X"
- `load_kos_context` - "Continue where we left off"  
- `read_kb_file` - "Show me that document"
- `list_kb_directory` - "What's in this folder?"
- `synthesize_kb_information` - "How does X relate to Y?"

**KB Usage Flow**:
1. User: "Search my notes on GAIA architecture"
2. Router classifies as MODERATE (needs KB tools)
3. Routes to `/chat/mcp-agent-hot` with KB tools
4. LLM calls `search_knowledge_base("GAIA architecture")`
5. KB service executes ripgrep search (~14ms)
6. Results formatted and returned to user

## Usage

### Intelligent Endpoint

```bash
# Ultra-fast direct response
curl -X POST https://gaia-gateway-dev.fly.dev/api/v1/chat \
  -H "Authorization: Bearer $JWT" \
  -d '{"message": "Hello!"}'  # Direct response ~0.5s

# KB search integration
curl -X POST https://gaia-gateway-dev.fly.dev/api/v1/chat \
  -H "Authorization: Bearer $JWT" \
  -d '{"message": "What do I know about microservices?"}'  # KB search ~2s

# Complex orchestration
curl -X POST https://gaia-gateway-dev.fly.dev/api/v1/chat \
  -H "Authorization: Bearer $JWT" \
  -d '{"message": "Create a fantasy world with multiple kingdoms"}'  # Multi-agent ~4s
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

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

This document describes an architecture that is conceptually similar to the current implementation, but the specific details are **significantly outdated**. The core logic has been consolidated and refactored.

-   **⚠️ Implementation Location:**
    *   **Claim:** The implementation is in `app/services/chat/intelligent_router.py` and `app/services/chat/intelligent_chat.py`.
    *   **Verification:** This is **INCORRECT**. These files are located in an `_archive_2025_01` directory. The current implementation is in `app/services/chat/unified_chat.py`.

-   **✅ Core Architectural Concept:**
    *   **Claim:** A single LLM call with `tool_choice="auto"` is used to decide between a direct response and routing.
    *   **Code Reference:** `app/services/chat/unified_chat.py` (lines 323-331).
    *   **Verification:** This is **VERIFIED**. The `UnifiedChatHandler.process` method uses a single call to `chat_service.chat_completion` with `tool_choice={"type": "auto"}`.

-   **⚠️ Routing Paths:**
    *   **Claim:** Requests are routed to `/chat/direct`, `/chat/mcp-agent-hot`, or `/chat/mcp-agent`.
    *   **Verification:** This is **INCORRECT**. The routing logic in `unified_chat.py` does not forward requests to other HTTP endpoints. Instead, it calls other services/methods directly within the same process (e.g., `self.mcp_hot_service.process_chat`). The concept of different paths exists, but not as separate HTTP endpoints.

-   **✅ Knowledge Base Integration:**
    *   **Claim:** KB tools are provided to the LLM when needed.
    *   **Code Reference:** `app/services/chat/unified_chat.py` (lines 321, 341).
    *   **Verification:** This is **VERIFIED**. The `all_tools` variable includes `KB_TOOLS`, and if a KB tool is called, it is executed by `_execute_kb_tools`.

-   **❌ Discrepancies in Endpoints:**
    *   **Claim:** A `/chat/fast` endpoint exists to bypass routing.
    *   **Verification:** This is **NOT VERIFIED**. This endpoint is not defined in `app/gateway/main.py` or `app/services/chat/unified_chat.py`.
    *   **Claim:** A `/chat/intelligent/metrics` endpoint exists.
    *   **Verification:** This is **NOT VERIFIED**. While the `UnifiedChatHandler` has a `get_metrics` method, it is not exposed as an HTTP endpoint.

**Overall Conclusion:** This document is **outdated and should not be used as a reference for the current implementation**. While the high-level concept of intelligent routing via a single LLM call is correct, the specific file locations, routing mechanisms, and supporting endpoints have all changed. The current implementation is centralized in `app/services/chat/unified_chat.py`.

## Implementation Files

- `app/services/chat/intelligent_router.py` - Classification logic
- `app/services/chat/intelligent_chat.py` - Routing service
- `scripts/test-intelligent-routing.sh` - Routing test
- `scripts/test-intelligent-routing-performance.sh` - Performance test