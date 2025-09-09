# architecture

System architecture and design patterns.

## Subdirectories

- `patterns/` - Architectural patterns and decisions
- `chat/` - Chat service architecture
- `database/` - Database design and strategy
- `services/` - Individual service specifications

## Files

- `README.md` - Human-readable overview

## Index

### patterns/
- `service-discovery-guide.md` - Service discovery implementation
- `service-initialization-pattern.md` - Service startup order
- `service-creation-automation.md` - Automated service creation
- `deferred-initialization-pattern.md` - Fast startup patterns

### chat/
- `chat-routing-and-kb-architecture.md` - Routing system with KB integration
- `chat-request-response-flow.md` - Request lifecycle
- `web-ui-chat-flow.md` - Frontend to backend flow
- `unified-chat-persistence.md` - Conversation persistence
- `chat-v2-clean-architecture.md` - Clean architecture design

### database/
- `database-architecture.md` - Hybrid PostgreSQL + Redis
- `postgresql-simplicity-lessons.md` - Avoiding overengineering

### services/
- `asset-service.md` - Media management service
- `llm-service.md` - Language model integration
- `microservices-scaling.md` - Scaling strategies

## Key Patterns

- **Service Discovery**: Dynamic endpoint discovery
- **Intelligent Routing**: Single LLM call optimization
- **Storage Backends**: Git/Database/Hybrid flexibility
- **Database Philosophy**: PostgreSQL + Redis hybrid

## Parent
[../+docs.md](../+docs.md)