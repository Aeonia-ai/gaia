# KB Agent Overview

**Date**: September 2025
**Status**: Implemented and Production Ready
**Version**: 1.0.0

## Executive Summary

The KB Agent transforms the Knowledge Base service from a static file repository into an **intelligent knowledge interpreter** capable of making decisions, executing workflows, and validating actions based on KB content. This embedded LLM agent provides real-time knowledge interpretation without external service dependencies.

## Key Capabilities

- **🧠 Knowledge Interpretation**: Convert static markdown into actionable intelligence
- **⚡ Workflow Execution**: Execute step-by-step procedures defined in KB markdown
- **⚖️ Rule Validation**: Validate actions against KB-defined rules and guidelines
- **🔄 Decision Making**: Make intelligent decisions based on KB knowledge
- **🔍 Information Synthesis**: Combine insights from multiple knowledge sources
- **🚀 Real-time Performance**: Direct LLM integration with sub-second response times

## Architecture Highlights

### Direct LLM Integration
- **No Inter-service Dependencies**: KB Agent operates independently of chat service
- **Performance Optimized**: Direct API calls eliminate network latency (saves 10-50ms per request)
- **High Reliability**: Continues functioning even if other services are unavailable

### Universal Knowledge Loading
- **Index-Agnostic**: Works with both `+index.md` files and regular `.md` files
- **Backward Compatible**: 100% compatible with existing indexed KB structures
- **Recursive Discovery**: Automatically finds files in nested directory structures
- **Mixed Structure Support**: Handles directories with both indexed and non-indexed content

### Intelligent Model Selection
- **Haiku (Fast)**: Used for validation and simple decision-making
- **Sonnet (Powerful)**: Used for complex workflows and synthesis tasks
- **Automatic Selection**: Based on query complexity and operation mode

### Multi-mode Operation
- **Decision Mode**: Make decisions based on available knowledge
- **Synthesis Mode**: Combine information from multiple sources
- **Validation Mode**: Check actions against established rules

## Quick Start

### Basic Knowledge Interpretation
```bash
curl -X POST http://kb-service:8000/agent/interpret \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How should I handle combat between a player and an orc?",
    "context_path": "/shared/mmoirl-platform/core-mechanics",
    "mode": "decision"
  }'
```

### Workflow Execution
```bash
curl -X POST http://kb-service:8000/agent/workflow \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_path": "combat-resolution.md",
    "parameters": {
      "player_level": 5,
      "weapon": "sword",
      "enemy": "orc"
    }
  }'
```

### Action Validation
```bash
curl -X POST http://kb-service:8000/agent/validate \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "Player casts fireball spell",
    "rules_path": "/shared/mmoirl-platform/magic-system",
    "context": {"player_class": "wizard", "mana": 50}
  }'
```

## Use Cases

### Game Master Intelligence
- **Real-time Decisions**: Make immediate gameplay decisions based on established rules
- **Dynamic Responses**: Interpret player actions against game world knowledge
- **Consistent Rulings**: Apply game rules consistently across all interactions

### Knowledge-Driven Automation
- **Workflow Automation**: Execute complex procedures defined in markdown
- **Rule Enforcement**: Automatically validate actions against documented policies
- **Context-Aware Responses**: Provide intelligent responses based on full knowledge context

### Developer Assistance
- **Code Validation**: Check code changes against development guidelines
- **Architecture Decisions**: Make architectural choices based on documented patterns
- **Knowledge Discovery**: Find relevant information across large knowledge bases

## Integration Points

### Chat Service Integration
The KB Agent complements the chat service by:
- **Specialized Processing**: Handles knowledge-specific queries that require rule interpretation
- **Performance Critical**: Provides sub-second responses for real-time game mechanics
- **Fallback Capability**: Operates independently when chat service is unavailable

### Claude Code Endpoint Relationship
**Complementary, not competing** functionality:
- **KB Agent** (`/agent/*`): Intelligent knowledge interpretation and decision making
- **Claude Code** (`/claude-code`): Technical codebase search and file analysis

**Example distinction**:
- Claude Code: `"search for combat"` → Returns file paths and matches
- KB Agent: `"How should combat work?"` → Returns intelligent game design advice

### Knowledge Base Synergy
- **Live Content**: Always operates on the latest KB content without sync delays
- **Markdown Native**: Directly interprets markdown files as executable knowledge
- **Git Integration**: Automatically incorporates new knowledge as it's committed
- **Universal Structure**: Works with any markdown-based knowledge organization

## Performance Characteristics

- **Response Time**: 1-3 seconds for complex interpretations
- **Concurrency**: Handles multiple simultaneous agent requests
- **Caching**: Intelligent caching of rule interpretations for repeated queries
- **Model Efficiency**: Automatic model selection optimizes cost and performance

## Next Steps

1. **Explore Examples**: See [KB Agent Examples](kb-agent-examples.md) for detailed use cases
2. **API Reference**: Check [KB Agent API](../api/kb-agent-api.md) for complete endpoint documentation
3. **Workflow Creation**: Learn [Workflow Creation Guide](workflows/workflow-creation-guide.md)
4. **Integration**: Review [KB Agent Integration](integration/kb-agent-integration.md) for service integration patterns

## Related Documentation

- [KB Agent API Reference](../api/kb-agent-api.md)
- [KB Agent Examples](kb-agent-examples.md)
- [Workflow Creation Guide](workflows/workflow-creation-guide.md)
- [KB Agent Architecture](../architecture/kb-agent-architecture.md)
- [Performance Tuning](troubleshooting/kb-agent-performance.md)