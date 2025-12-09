# Designs

This directory contains design documents for the Aeonia Gaia platform.

## Related Design Documentation

While this directory is currently minimal, extensive design documentation exists throughout the repository:

### Architecture & System Design
- [Architecture Overview](/Users/jasbahr/Development/Aeonia/server/gaia/docs/_internal/architecture-overview.md)
- [Clean Slate Architecture (2025-10-31)](/Users/jasbahr/Development/Aeonia/server/gaia/docs/_internal/clean-slate-architecture-2025-10-31.md)
- [Chat Routing and KB Architecture](/Users/jasbahr/Development/Aeonia/server/gaia/docs/chat-routing-and-kb-architecture.md)

### Experience System Designs
- [KB Experience Architecture Deep Dive](/Users/jasbahr/Development/Aeonia/server/gaia/docs/scratchpad/kb-experience-architecture-deep-dive.md)
- [Admin Command System Design](/Users/jasbahr/Development/Aeonia/server/gaia/docs/scratchpad/admin-command-system-comprehensive-design.md)
- [Markdown Command Architecture](/Users/jasbahr/Development/Aeonia/server/gaia/docs/scratchpad/markdown-command-architecture.md)
- [Simulation Architecture Overview](/Users/jasbahr/Development/Aeonia/server/gaia/docs/scratchpad/simulation-architecture-overview.md)

### WebSocket & Real-Time Designs
- [AOI WebSocket Design (2025-11-10)](/Users/jasbahr/Development/Aeonia/server/gaia/docs/scratchpad/aoi-websocket-design-2025-11-10.md)
- [WebSocket Architecture Decision](/Users/jasbahr/Development/Aeonia/server/gaia/docs/scratchpad/websocket-architecture-decision.md)

### Database & Scaling
- [Database Architecture](/Users/jasbahr/Development/Aeonia/server/gaia/docs/reference/database/database-architecture.md)
- [Portable Database Architecture](/Users/jasbahr/Development/Aeonia/server/gaia/docs/reference/database/portable-database-architecture.md)
- [Scaling Architecture](/Users/jasbahr/Development/Aeonia/server/gaia/docs/reference/services/scaling-architecture.md)

### Deep Dive Documents
- [Dynamic Experiences Phase 1 MVP](/Users/jasbahr/Development/Aeonia/server/gaia/docs/concepts/deep-dives/dynamic-experiences/phase-1-mvp/)
  - [MVP File-Based Design](/Users/jasbahr/Development/Aeonia/server/gaia/docs/concepts/deep-dives/dynamic-experiences/phase-1-mvp/000-mvp-file-based-design.md)
  - [KB Agent Architecture](/Users/jasbahr/Development/Aeonia/server/gaia/docs/concepts/deep-dives/dynamic-experiences/phase-1-mvp/002-kb-agent-architecture.md)
  - [Design Decisions](/Users/jasbahr/Development/Aeonia/server/gaia/docs/concepts/deep-dives/dynamic-experiences/phase-1-mvp/101-design-decisions.md)

## Contributing Design Documents

When adding new design documents, consider:
- Should it be an ADR (Architecture Decision Record)? → Place in `/docs/decisions/`
- Is it a deep-dive on a specific feature? → Place in `/docs/concepts/deep-dives/`
- Is it exploratory/draft work? → Place in `/docs/scratchpad/`
- Is it reference architecture? → Place in `/docs/reference/`

For questions about documentation organization, see `/docs/_planning/PLAN.md`.
