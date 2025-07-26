# Tool Routing Improvement Specification with KOS Intelligence

**Version**: 2.0  
**Date**: July 26, 2025  
**Status**: Planning  

## Overview

This specification outlines improvements to the Gaia platform's tool routing system to enhance performance, maintainability, and user experience while preserving scalability and backward compatibility. **Version 2.0** incorporates KOS (Knowledge Operating System) intelligence approaches from the consolidated intelligent chat spec, including domain orchestrators and adaptive user context loading.

## KOS Intelligence Integration

### KOS Context Loading
The tool routing system will integrate with user's Knowledge Operating System state:
- **Session State**: Current working threads and active projects
- **Daily Plans**: Today's priorities and scheduled work
- **Cross-References**: Wiki links and document relationships  
- **User Namespaces**: Personal knowledge boundaries and sharing permissions

### Domain Orchestrators
Enhanced routing includes KOS-aware domain specialists:
- **Technical Domain**: Gaia architecture, performance optimization, microservices
- **Consciousness Domain**: MMOIRL frameworks, emergence mechanics, awareness systems
- **Business Domain**: Strategy, partnerships, funding, market positioning
- **Creative Domain**: Narrative design, worldbuilding, storytelling mechanics

## Current Architecture Analysis

### Tool Routing Components
- **Primary Router**: `UnifiedChatHandler` with LLM-based classification
- **Tool Types**: KB tools (6), MCP-agent routing, Asset service routing
- **Architecture**: HTTP-based service communication for scalability
- **Performance**: Hot-loaded MCP contexts, ~1s direct responses, ~2-3s tool responses

### Current Issues
- **60+ scattered chat endpoints** creating maintenance overhead (only 4-5 needed for production)
- **Redundant functionality** - KB, multiagent scenarios, performance variants duplicating unified endpoint capabilities
- **Fragmented tool registration** across different systems
- **HTTP latency** without optimization (connection pooling, caching)
- **Classification accuracy** at ~85% with false positives/negatives
- **Limited tool composition** requiring multiple user interactions
- **Generic error handling** without graceful degradation

## Implementation Plan

## Phase 1: Architectural Simplification (Week 1-2)

### 1.1 Consolidate Chat Endpoints and Handlers  
**Objective**: Reduce complexity from 60+ endpoints to 4-5 production endpoints

**Current State**: 60+ chat endpoints with massive functional overlap
- **Production Core**: `/api/v1/chat` (unified), `/api/v0.2/chat` (legacy)
- **Redundant KB endpoints**: 7 variants (`kb-enhanced`, `kb-research`, etc.)
- **Redundant multiagent endpoints**: 4 scenarios (`gamemaster`, `worldbuilding`, etc.)
- **Performance testing endpoints**: 8+ variants (`ultrafast`, `direct`, etc.)
- **Web interface endpoints**: Separate streaming/form handlers

**Migration Plan**:

**Phase 1A: Verify Unified Endpoint Capabilities**
```bash
# Test KB functionality through unified endpoint
./scripts/test-endpoint-consolidation.sh kb-operations

# Test multiagent scenarios through prompt-based routing
./scripts/test-endpoint-consolidation.sh multiagent-scenarios

# Test web UI with /api/v1/chat streaming
./scripts/test-endpoint-consolidation.sh web-streaming
```

**Phase 1B: Deprecate Redundant Endpoints**
- **KB endpoints → Tool integration**: Remove `/api/v1/chat/kb-*` (7 endpoints)
- **Multiagent → MCP scenarios**: Remove `/api/v1/chat/{gamemaster,worldbuilding,storytelling,problemsolving}` (4 endpoints)  
- **Performance testing → Internal use**: Move `/api/v1/chat/{ultrafast,direct,mcp-agent-hot}` variants to internal testing
- **Web endpoints → Unified streaming**: Remove `/api/chat/{stream,send}` in favor of `/api/v1/chat` with `stream: true`

**Phase 1C: Production Endpoint Set (4 total)**
```
/api/v1/chat/completions  # NEW: Official OpenAI specification compliance (message arrays)
/api/v1/chat              # Current unified intelligent routing (single message)
/api/v0.2/chat            # Legacy Gaia format compatibility
/api/v1/auth/*            # Authentication endpoints  
/health                   # Health checks
```

**Implementation Details**:
- **NEW OpenAI endpoint**: `/api/v1/chat/completions` with full OpenAI specification compliance
- **Keep current unified**: Don't modify existing `/chat/unified` handler that's working
- **Message array support**: OpenAI endpoint accepts `messages: [...]` format
- **Legacy compatibility**: Keep v1 (current) and v0.2 (original) for existing clients
- **Multiagent scenarios**: Configure via unified endpoint prompting instead of separate endpoints
- **KB operations**: Use existing KB tools in unified handler instead of separate endpoints
- **Performance variants**: Keep code for internal benchmarking, remove public endpoints

**OpenAI Specification Endpoint**:
```json
// Request format
{
  "messages": [
    {"role": "user", "content": "Hello, how are you?"},
    {"role": "assistant", "content": "I'm doing well, thanks!"},
    {"role": "user", "content": "What's the weather like?"}
  ],
  "model": "claude-3-5-sonnet-20241022",
  "stream": false
}

// Response format (OpenAI compliant)
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "claude-3-5-sonnet-20241022",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "I don't have access to real-time weather data..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 56,
    "completion_tokens": 31,
    "total_tokens": 87
  }
}
```

**Success Criteria**:
- **90% endpoint reduction**: From 60+ endpoints to 4 production endpoints  
- **OpenAI specification compliance**: `/api/v1/chat/completions` fully compatible with OpenAI clients
- **Preserved intelligent routing**: Keep working `/chat/unified` handler unchanged
- **100% backward compatibility**: Existing v1/v0.2 clients continue working
- **Enhanced functionality**: KB, multiagent, streaming all work through unified endpoint
- **Reduced maintenance overhead**: Single handler serving all chat requests with intelligent routing
- **Future v0.3 ready**: Architecture prepared for eventual native Gaia format with KOS intelligence

### 1.2 KOS-Aware Unified Tool Registry
**Objective**: Centralized tool management with KOS context-aware smart presentation

**Current State**: Fragmented tool registration
- KB tools: Hardcoded in `kb_tools.py`
- MCP tools: Dynamic discovery
- Routing tools: Hardcoded in handlers

**Implementation**:
```python
class KOSToolRegistry:
    def get_execution_tools(self, kos_context: Dict[str, Any]) -> List[Tool]     
    def get_classification_tools(self, user_domain: str) -> List[Tool] 
    def get_tools_for_context(self, context: str, session_state: str) -> List[Tool]
    def get_domain_tools(self, domains: List[str]) -> Dict[str, List[Tool]]
```

**KOS-Aware Tool Presentation**:
- **Domain-context filtering** - Show tools relevant to current work domain (technical, consciousness, business)
- **Session-based availability** - Tools adapt to current KOS session state and active threads
- **Cross-reference integration** - Tools that can leverage wiki links and document relationships
- **User namespace awareness** - Respect knowledge boundaries and sharing permissions
- **Performance-based selection** - Prefer faster tools when appropriate

**Success Criteria**:
- Single tool registry managing all tools with KOS awareness
- Domain and session context-aware tool presentation
- Easy addition of new tools with domain classification
- Integration with KOS session state and user namespaces

### 1.3 Improved Classification with System Messaging
**Objective**: Better routing accuracy through clearer guidelines

**Current State**: ~85% accuracy with edge case issues

**Implementation**:
```python
system_prompt = """When a user request could reasonably be handled in multiple ways, 
ask for clarification rather than guessing. 

CLEAR direct response: "What's 2+2?" "What's the capital of France?"
CLEAR KB search: "Find my notes on X" "What did I write about Y?"
ASK FOR CLARIFICATION: "Tell me about X" "How do I approach Y?"

Example clarification:
"Would you like me to give you a general overview of machine learning, 
or search your knowledge base for your specific notes on this topic?"
"""
```

**Success Criteria**:
- Reduced false positives for simple queries
- Proactive clarification for ambiguous requests
- User education about system capabilities

## Phase 2: Performance & Integration (Week 3-4)

### 2.1 Optimized Service Integration
**Objective**: Improve performance while maintaining scalability

**Current State**: HTTP calls without optimization adding latency

**Implementation**:
- **HTTP connection pooling** - Reuse connections to services
- **Result caching** - Redis cache for KB searches, asset results
- **Async HTTP calls** - Non-blocking I/O for concurrent requests
- **Request batching** - Combine operations where possible
- **Smart retry logic** - Handle transient failures gracefully

**Rationale**: Maintains service independence for scaling while eliminating performance overhead

**Success Criteria**:
- 40% reduction in tool response latency
- Maintained service scalability
- Improved reliability under load

### 2.2 KOS-Aware MCP-Agent as Domain Orchestrator
**Objective**: Leverage MCP-agent for complex tool composition with KOS domain intelligence

**Current State**: Limited to single-tool operations per interaction

**Implementation**:
```
User: "Search my KB for consciousness frameworks, then design an MMOIRL mechanic"
↓
Main LLM: "This needs consciousness domain orchestration with KB integration" 
↓
Route to MCP-agent with KOS context (session state, active threads, domain focus)
↓
MCP-agent: Uses domain-aware orchestration:
  1. Load KOS consciousness domain context
  2. Execute KB search in user's consciousness namespace
  3. Analyze results with MMOIRL design expertise
  4. Generate mechanics with cross-references to existing frameworks
  5. Return complete response with session state updates
```

**KOS-Enhanced MCP-Agent Capabilities**:
- **Domain-specific task decomposition** - Route to consciousness, technical, business specialists
- **KOS context loading** - Access session state, daily plans, cross-references
- **Namespace-aware operations** - Respect user knowledge boundaries and sharing
- **Session state integration** - Update active threads and work context
- **Cross-reference maintenance** - Create and update wiki links between related content
- **Built-in failure handling and retry logic**
- **Agent-to-agent communication with domain handoffs**

**Success Criteria**:
- Support for multi-domain workflows in single interaction
- KOS-aware task decomposition with domain routing
- Session state persistence and cross-reference updates
- Robust error recovery with domain fallbacks

### 2.3 Layered Streaming Architecture
**Objective**: Real-time progress feedback for all operations

**Current State**: Mixed streaming quality (real for LLM, simulated for tools)

**Implementation**:
```python
class StreamingContext:
    def tool_progress(self, tool_name: str, message: str)      # Individual service progress
    def workflow_progress(self, step: str, message: str)       # MCP-agent orchestration
    def combine_streams(self) -> unified_stream                # Unified user experience
```

**User Experience**:
```
🔍 Step 1: Searching knowledge base
  → Searching documents... (tool-level)
  → Found 8 relevant articles (tool-level)
🎨 Step 2: Generating image  
  → Initializing generator... (tool-level)
  → Creating image based on findings... (tool-level)
```

**Success Criteria**:
- Real streaming for all tool operations
- Clear progress indication for long operations
- Layered detail (workflow + tool level)

## Phase 3: Intelligence & Reliability (Week 5-6)

### 3.1 KOS Domain Orchestration with Multiagent Intelligence
**Objective**: Leverage native MCP orchestration capabilities with KOS domain expertise

**Current State**: Underutilizing MCP-agent's built-in orchestration features and domain knowledge

**Implementation**:
Configure MCP-agent with KOS domain-specialized sub-agents:
- **Technical Agent** - Gaia architecture, microservices, performance optimization specialist
- **Consciousness Agent** - MMOIRL frameworks, emergence mechanics, awareness systems
- **Business Agent** - Strategy, partnerships, funding, market positioning
- **KB Agent** - Knowledge base operations, cross-reference management, namespace operations
- **Asset Agent** - Generation tasks with domain context integration
- **Research Agent** - Multi-source synthesis with KOS cross-reference creation

**KOS-Enhanced Orchestration Patterns**:
- **Domain-aware coordination** - Route tasks to appropriate domain specialists with KOS context
- **Cross-domain synthesis** - Combine insights from technical, consciousness, and business domains
- **Session state management** - Persistent context across interactions and domain handoffs
- **Namespace-aware context sharing** - Agents exchange relevant context within user boundaries
- **Dynamic resource management** - Optimize workload distribution based on domain complexity
- **KOS lifecycle integration** - Update session state, daily plans, and active threads

**KOS Parent Agent Pattern** (from consolidated spec):
```python
class KOSParentAgent:
    """Main agent that orchestrates KOS-aware conversations like Claude Code's parent agent"""
    
    async def process_message(self, message: str) -> dict:
        """Orchestrate response with KOS domain awareness"""
        
        # 1. Load KOS context (session state, threads, daily plan)
        kos_context = await self.load_kos_context()
        
        # 2. Analyze message for domain requirements
        analysis = await self.analyze_domains_and_complexity(message, kos_context)
        
        # 3. Route to appropriate domain orchestration
        if analysis['domains'] == ['technical']:
            return await self.technical_domain_orchestration(message, kos_context)
        elif 'consciousness' in analysis['domains']:
            return await self.consciousness_domain_orchestration(message, kos_context)
        elif len(analysis['domains']) > 1:
            return await self.cross_domain_synthesis(message, analysis, kos_context)
        else:
            return await self.general_kos_response(message, kos_context)
```

**Success Criteria**:
- Sophisticated multi-domain workflows with KOS integration
- Cross-domain synthesis capabilities (technical + consciousness + business)
- Session state persistence and cross-reference updates
- Built-in failure handling and domain fallbacks
- Extensible domain-specific agent ecosystem

### 3.2 Service-Level Error Recovery
**Objective**: Graceful degradation and transparent communication

**Current State**: Generic error messages without alternatives

**Implementation**:

**Graceful Degradation**:
```
KB service unavailable → "I can't access your knowledge base right now, 
but I can give you a general answer about X. Would you like me to try 
the KB search again later?"
```

**Automatic Fallbacks**:
```
Asset generation fails → Try different model → Try simpler prompt → 
Fallback to detailed description → Explain what went wrong
```

**Circuit Breaker Pattern**:
- Monitor service health
- Temporarily route around failing services
- Automatic recovery detection

**Success Criteria**:
- Clear user communication about service status
- Automatic fallback strategies
- Improved system reliability

## Technical Architecture

### Service Communication with KOS Integration
```
Main LLM Classification → KOS Context Loading → Domain Analysis → Execution/Routing
                     ↓                          ↓
             Simple Query → Direct Response     Domain-specific Route:
             KB Query → KOS-aware KB Service   - Technical → Architecture optimization
             Complex Query → Domain Orchestration - Consciousness → MMOIRL design
                                              - Business → Strategy synthesis
                                              - Cross-domain → Parent agent coordination
```

### KOS-Aware Tool Registry Structure
```python
KOSToolRegistry:
  ├── execution_tools/
  │   ├── kb_tools (search, read, synthesize, cross_reference)
  │   ├── direct_mcp_tools (file ops, web search)
  │   ├── asset_tools (generation, editing)
  │   └── kos_tools (session_state, daily_plan, thread_management)
  ├── classification_tools/
  │   ├── domain_analysis (technical, consciousness, business, creative)
  │   ├── use_mcp_agent (with domain context)
  │   └── route_to_multiagent (with KOS orchestration)
  ├── domain_tools/
  │   ├── technical_domain (architecture, performance, microservices)
  │   ├── consciousness_domain (MMOIRL, frameworks, emergence)
  │   ├── business_domain (strategy, partnerships, funding)
  │   └── creative_domain (narrative, worldbuilding, storytelling)
  └── context_filters/
      ├── user_namespaces (knowledge boundaries)
      ├── session_state (active threads, current focus)
      ├── performance_preferences
      ├── domain_access_levels
      └── capability_availability
```

### KOS-Aware Streaming Architecture
```
User Request → KOS Context Load → Domain Classification → Tool Selection → Execution
                                                                              ↓
                                                                      Layered Streaming:
                                                                      - KOS State Updates (session, threads)
                                                                      - Domain Progress (technical, consciousness, business)
                                                                      - Workflow Progress (MCP-agent orchestration)
                                                                      - Tool Progress (Individual services)
                                                                      - Cross-Reference Creation (wiki links)
                                                                      - Unified User Experience
```

## Success Metrics

### Performance Targets
- **Response time reduction**: 40% for tool-based queries
- **Classification accuracy**: >95% (from current ~85%) with domain awareness
- **False positive elimination**: <5% for simple queries
- **Service reliability**: 99.9% uptime with graceful degradation
- **KOS context loading**: <200ms for session state and domain context
- **Cross-reference creation**: Real-time wiki link generation and updates

### User Experience Goals  
- **Multi-domain workflows**: Single interaction for technical + consciousness + business synthesis
- **KOS-aware responses**: Context from session state, active threads, and domain focus
- **Clear progress feedback**: Real-time status for all operations including domain handoffs
- **Cross-reference navigation**: Automatic wiki links between related content
- **Session persistence**: Conversations maintain context across domain boundaries
- **Transparent error handling**: Users understand issues and alternatives
- **Maintained compatibility**: 100% backward compatibility

### System Quality Improvements
- **Code complexity reduction**: Single chat handler with KOS integration
- **Maintainability**: Centralized tool management with domain classification
- **Extensibility**: Easy addition of new tools, agents, and domain specializations
- **Scalability**: Independent service scaling maintained with KOS context caching
- **Domain expertise**: Specialized routing for technical, consciousness, business, and creative domains
- **Knowledge integration**: Session state updates and cross-reference maintenance

## Implementation Priorities

**Immediate Phase (Preserve Working System):**
1. **Add OpenAI-compliant endpoint** (`/api/v1/chat/completions`) for message array support
2. **Remove redundant endpoints** (~55 variants of kb-*, ultrafast-*, multiagent scenarios)
3. **Keep unified handler unchanged** (it's working well with intelligent routing)
4. **HTTP optimization** (connection pooling, caching for performance)

**Future Phases:**
5. **v0.3 endpoint** with native Gaia format and KOS intelligence (when ready)
6. **KOS-aware unified tool registry** (domain classification and context awareness)
7. **Domain-aware MCP-agent orchestration** (cross-domain workflows)
8. **Enhanced streaming with KOS updates** (session persistence and state management)

## Risk Mitigation

### Backward Compatibility
- **v0.2 → v1 proxy** maintains existing client compatibility
- **Gradual migration** of internal systems
- **Comprehensive testing** of API contracts

### Performance Considerations
- **HTTP optimization** before architectural changes
- **Caching strategies** to reduce service load
- **Monitoring and metrics** to track improvements

### Rollback Strategy
- **Feature flags** for new routing logic
- **A/B testing** for classification improvements
- **Service-by-service rollout** to limit blast radius

## Timeline

**Week 1-2: Foundation**
- Chat handler consolidation
- Tool registry implementation
- Classification improvements

**Week 3-4: Performance** 
- HTTP optimization
- MCP-agent integration
- Streaming enhancements

**Week 5-6: Intelligence**
- Advanced orchestration
- Error recovery
- Monitoring and metrics

**Week 7+: Optimization**
- Performance tuning
- User feedback integration
- Advanced features

## Future Considerations

### Potential Extensions
- **User-defined KOS workflows** - Custom tool combinations with domain awareness
- **Learning from domain usage** - Adaptive classification based on user's domain preferences
- **Cross-session KOS context** - Persistent session state and thread continuity
- **Advanced KOS caching** - Intelligent result reuse with cross-reference optimization
- **Multi-user KOS collaboration** - Shared domain knowledge and session state
- **Adaptive UI based on domain focus** - Interface changes based on technical vs consciousness vs business work

### KOS-Enhanced Monitoring and Analytics
- **Domain usage patterns** - Understand user focus across technical, consciousness, business domains
- **Cross-reference network analysis** - Track knowledge graph evolution and connection strength
- **Session state persistence metrics** - Measure context continuity across conversations
- **Performance metrics** - Response times and error rates by domain
- **Classification accuracy by domain** - Continuous improvement data for each specialization
- **User satisfaction by workflow complexity** - Feedback loops for multi-domain orchestration optimization

---

*This specification provides a roadmap for transforming the current complex tool routing system into a streamlined, KOS-aware, domain-intelligent platform while preserving scalability and reliability. The integration of KOS intelligence enables sophisticated cross-domain synthesis capabilities that leverage user's personal knowledge context and session state for more relevant and contextually-aware responses.*