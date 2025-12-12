# Designs

This directory serves as a central hub for major design artifacts, linking to key design documentation for architecture, experience systems, real-time services, and database scaling located throughout the repository.

## Related Design Documentation

While this directory is currently minimal, extensive design documentation exists throughout the repository:

### Architecture & System Design
- [[../_internal/architecture-overview.md]]: High-level overview of the Gaia Platform's microservices architecture.
- [[../_internal/clean-slate-architecture-2025-10-31.md]]: An exploratory research document designing a new "Dynamic Experiences" system from first principles.
- [[../chat-routing-and-kb-architecture.md]]: Details on the chat routing and Knowledge Base integration.

### Experience System Designs
- [[../scratchpad/kb-experience-architecture-deep-dive.md]]: Deep dive into the KB experience architecture.
- [[../scratchpad/admin-command-system-comprehensive-design.md]]: Comprehensive design for the admin command system.
- [[../scratchpad/markdown-command-architecture.md]]: Architecture for the markdown-driven command system.
- [[../scratchpad/simulation-architecture-overview.md]]: Overview of the simulation architecture.

### WebSocket & Real-Time Designs
- [[../scratchpad/aoi-websocket-design-2025-11-10.md]]: Design for Area of Interest (AOI) with WebSockets.
- [[../scratchpad/websocket-architecture-decision.md]]: Architectural decisions for WebSocket implementation.

### Database & Scaling
- [[../reference/database/database-architecture.md]]: The hybrid PostgreSQL and Redis database architecture.
- [[../reference/database/portable-database-architecture.md]]: Design for a portable database architecture.
- [[../reference/services/scaling-architecture.md]]: Strategies for scaling the platform's services.

### Deep Dive Documents
- [[../concepts/deep-dives/dynamic-experiences/phase-1-mvp/+phase-1-mvp.md]]: The foundational architecture for creating interactive experiences.
  - [[../concepts/deep-dives/dynamic-experiences/phase-1-mvp/000-mvp-file-based-design.md]]: The original, superseded file-based MVP design.
  - [[../concepts/deep-dives/dynamic-experiences/phase-1-mvp/002-kb-agent-architecture.md]]: The architecture of the KB Agent.
  - [[../concepts/deep-dives/dynamic-experiences/phase-1-mvp/101-design-decisions.md]]: Key design decisions made during the MVP phase.

## Contributing Design Documents

When adding new design documents, consider:
- Should it be an ADR (Architecture Decision Record)? → Place in `[[../_internal/adr/+adr.md]]`
- Is it a deep-dive on a specific feature? → Place in `[[../concepts/deep-dives/+deep-dives.md]]`
- Is it exploratory/draft work? → Place in `[[../scratchpad/+scratchpad.md]]`
- Is it reference architecture? → Place in `[[../reference/+reference.md]]`

For questions about documentation organization, see `[[../_planning/PLAN.md]]`.