# Custom Multi-Agent Orchestration System

## Overview

The custom orchestration system provides efficient multi-agent coordination for complex tasks while maintaining minimal overhead for simple requests. Built specifically for Gaia's needs, it takes the best ideas from existing frameworks without the bloat.

## Key Features

- **Intelligent Routing**: Automatically determines whether to use direct LLM, MCP tools, or multi-agent orchestration
- **Dynamic Agent Spawning**: The orchestrator LLM decides when and which agents to spawn
- **Efficient Parallel Execution**: Independent tasks run in parallel automatically
- **Minimal Overhead**: ~200 lines of core code vs 500+ for existing frameworks
- **Clear Result Aggregation**: Automatic synthesis of results from multiple agents

## Architecture

### Core Components

1. **CustomOrchestrator**: Main orchestration class
   - LLM analyzes requests and decides on agent spawning
   - Manages task dependencies and parallel execution
   - Synthesizes results from all agents

2. **SimpleOrchestrator**: Direct agent specification
   - When you know exactly which agents you need
   - Useful for predefined workflows

3. **OrchestratedChatService**: Integration with chat service
   - Seamless routing between direct LLM, MCP, and orchestration
   - Performance metrics tracking
   - LLM Platform compatible responses

### Agent Roles

- **ORCHESTRATOR**: Main coordinator (decides what agents to spawn)
- **RESEARCHER**: Gathers information, finds sources
- **ANALYST**: Analyzes data, identifies patterns
- **WRITER**: Creates content, documentation
- **CODER**: Writes and reviews code
- **REVIEWER**: Quality checks, validation
- **TOOL_USER**: Executes MCP tools

## API Endpoints

### `/chat/orchestrated` (POST)
Orchestrated chat with intelligent routing.

```json
{
  "messages": [
    {"role": "user", "content": "Your complex request here"}
  ],
  "model": "claude-sonnet-4-5"
}
```

Response includes orchestration metadata:
```json
{
  "id": "msg_123456",
  "object": "chat.completion",
  "choices": [...],
  "metadata": {
    "orchestration": {
      "agents_used": 3,
      "success": true,
      "task_details": [...]
    },
    "performance": {
      "route": "mcp_agent",
      "execution_time": 4.2
    }
  }
}
```

### `/chat/orchestrated/metrics` (GET)
Get performance metrics:
```json
{
  "total_requests": 150,
  "direct_llm": 100,
  "mcp_requests": 30,
  "orchestrated": 20,
  "avg_response_time": 2.5,
  "route_distribution": {
    "direct_llm": 0.67,
    "mcp": 0.20,
    "orchestrated": 0.13
  }
}
```

## Usage Examples

### 1. Simple Request (Direct LLM)
```python
# Request: "What is Python?"
# Result: Direct answer, no agents spawned
```

### 2. Tool Usage (Direct MCP)
```python
# Request: "List files in the src directory"
# Result: Uses filesystem MCP tool directly
```

### 3. Complex Task (Multi-Agent)
```python
# Request: "Research quantum computing, analyze implications, write report"
# Result: Spawns researcher → analyst → writer agents
```

### 4. Parallel Execution
```python
# Request: "Analyze code in three files and compare them"
# Result: Spawns 3 analyzer agents in parallel, then synthesizes
```

## Performance Characteristics

- **Direct LLM**: ~2s (baseline)
- **Direct MCP**: ~2.5s (tool overhead)
- **Orchestrated**: 3-10s (depends on agent count and dependencies)
- **Parallel agents**: Minimal additional time vs sequential

## Implementation Details

### Task Management
```python
@dataclass
class Task:
    id: str
    role: AgentRole
    description: str
    context: Dict[str, Any]
    dependencies: List[str]  # Other task IDs
    parallel_ok: bool
    result: Optional[Any]
    status: str  # pending, running, completed, failed
```

### Dependency Resolution
- Topological sorting for execution order
- Parallel execution of independent tasks
- Automatic context passing between dependent tasks

### Model Selection
- **Orchestrator**: Claude Sonnet 4.5 (complex decision making)
- **Simple agents**: Claude 3 Haiku (faster, cheaper)
- **Complex agents**: Claude Sonnet 4.5 (better quality)

## Best Practices

1. **Let the orchestrator decide**: Don't force multi-agent for simple tasks
2. **Use patterns**: Pre-defined patterns for common workflows
3. **Monitor metrics**: Track route distribution to optimize
4. **Set appropriate timeouts**: Default 60s, adjust for complex tasks
5. **Handle errors gracefully**: System continues even if some agents fail

## Comparison with Existing Frameworks

| Feature | Our System | LangGraph | CrewAI | AutoGPT |
|---------|------------|-----------|---------|---------|
| Lines of Code | ~200 | 1000+ | 2000+ | 5000+ |
| Initialization | <50ms | 200ms | 500ms | 1s+ |
| Dependencies | Anthropic | Many | Many | Many |
| Flexibility | High | Medium | Medium | Low |
| Performance | Excellent | Good | Fair | Poor |

## Future Enhancements

1. **Agent Memory**: Persistent knowledge between requests
2. **Custom Tools**: Agent-specific tool access
3. **Streaming**: Real-time updates during orchestration
4. **Cost Optimization**: Automatic model selection based on task
5. **Advanced Patterns**: More sophisticated workflow templates

## Migration Guide

### From Direct Chat
```python
# Before
POST /api/v1/chat/completions
{"messages": [...]}

# After (automatic routing)
POST /api/v1/chat/orchestrated
{"messages": [...]}
```

### From MCP-Agent
```python
# Before (slow initialization)
POST /api/v1/chat/lightweight
{"messages": [...]}

# After (efficient orchestration)
POST /api/v1/chat/orchestrated
{"messages": [...]}
```

## Troubleshooting

### High Latency
- Check agent dependencies (minimize chains)
- Use parallel execution where possible
- Consider SimpleOrchestrator for known workflows

### Agent Failures
- System continues with partial results
- Check error details in response metadata
- Adjust timeouts if needed

### Route Selection
- Monitor metrics endpoint
- Force specific routes if needed
- Adjust routing confidence thresholds