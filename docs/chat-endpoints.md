# Chat Endpoints Overview

## Current Chat Endpoints (After Refactoring)

### Standard Endpoints

#### `/api/v1/chat` (POST)
- **Purpose**: Standard multi-provider chat
- **Speed**: ~2-3s
- **Features**: Provider selection, fallback support
- **Use when**: You want automatic provider selection

#### `/api/v1/chat/completions` (POST)
- **Purpose**: OpenAI-compatible endpoint
- **Speed**: Same as `/chat`
- **Note**: Limited OpenAI parameter support
- **Use when**: Using OpenAI SDK (but with limitations)

### Performance-Optimized Endpoints

#### `/api/v1/chat/direct` (POST)
- **Purpose**: Direct Anthropic API calls
- **Speed**: ~2s (fastest)
- **Features**: No framework overhead
- **Use when**: You need the fastest response

#### `/api/v1/chat/direct-db` (POST)
- **Purpose**: Direct chat with PostgreSQL memory
- **Speed**: ~2s + minimal DB overhead
- **Features**: Conversation persistence
- **Use when**: You need fast responses with memory

### Framework-Based Endpoints

#### `/api/v1/chat/mcp-agent` (POST)
- **Purpose**: Uses mcp-agent framework
- **Speed**: ~3-5s (initialization overhead)
- **Features**: MCP tool integration ready
- **Use when**: You need MCP tool capabilities

#### `/api/v1/chat/mcp-agent-hot` (POST)
- **Purpose**: Keeps mcp-agent initialized
- **Speed**: First request ~3-5s, then ~0.5-1s
- **Features**: Faster subsequent requests
- **Use when**: Making multiple MCP-agent requests

### Advanced Endpoints

#### `/api/v1/chat/orchestrated` (POST)
- **Purpose**: Intelligent routing with multi-agent support
- **Speed**: 2-10s (depends on complexity)
- **Features**: 
  - Automatic routing (direct LLM, MCP tools, multi-agent)
  - Dynamic agent spawning
  - Parallel execution
- **Use when**: You have complex tasks that might benefit from multiple agents

#### `/api/v1/chat/orchestrated/metrics` (GET)
- **Purpose**: Get performance metrics
- **Returns**: Request counts, route distribution, average times

## Endpoint Selection Guide

### For Simple Questions
Use `/api/v1/chat/direct` - Fastest response, no overhead

### For Standard Usage
Use `/api/v1/chat` - Good balance of features and performance

### For Complex Tasks
Use `/api/v1/chat/orchestrated` - Automatically determines best approach

### For MCP Tools
Use `/api/v1/chat/mcp-agent` - When you specifically need MCP capabilities

## Performance Comparison

| Endpoint | First Request | Subsequent | Best For |
|----------|--------------|------------|----------|
| `/direct` | ~2s | ~2s | Simple Q&A |
| `/chat` | ~2-3s | ~2-3s | General use |
| `/mcp-agent` | ~3-5s | ~3-5s | MCP tools |
| `/mcp-agent-hot` | ~3-5s | ~0.5-1s | Multiple MCP requests |
| `/orchestrated` | 2-10s | 2-10s | Complex tasks |

## Migration Guide

### From Old Names
- `/chat/lightweight` → `/chat/mcp-agent`
- `/chat/lightweight-simple` → `/chat/direct`
- `/chat/lightweight-hot` → `/chat/mcp-agent-hot`
- `/chat/lightweight-db` → `/chat/direct-db`

### Recommended Migration Path
1. Start with `/chat` (standard endpoint)
2. Use `/chat/direct` for performance-critical simple queries
3. Use `/chat/orchestrated` for complex multi-step tasks
4. Only use `/chat/mcp-agent` if you specifically need MCP tools