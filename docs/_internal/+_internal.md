# Internal Project Artifacts

This section houses internal project artifacts such as Architectural Decision Records (ADRs), post-mortems, reports, and other historical or administrative documents that are not part of the public-facing documentation.

## Directories

- [[_meta/+_meta.md]]: Contains meta-information about the documentation structure itself, including a snapshot of the file tree.
- [[_postmortems/+_postmortems.md]]: Contains postmortem reports detailing incidents, their root causes, resolutions, and lessons learned to prevent recurrence, including AI response persistence failures.
- [[_reports/+_reports.md]]: Contains internal reports and analyses, detailing specific investigations, test results, implementation learnings, and plans for improvement, including security audits and test execution findings.
- [[adr/+adr.md]]: Architectural Decision Records documenting key choices like authentication, automation, and data management.
- [[deprecated/+deprecated.md]]: Contains documents that are deprecated, outdated, or describe architectural decisions and implementations that have been superseded, retained for historical context.
- [[phase-reports/+phase-reports.md]]: Contains reports and plans detailing the progress, completion, and learnings from various development phases, tracking the evolution of features, architectural migrations, and testing strategies.
- [[postmortems/+postmortems.md]]: A placeholder directory for post-mortems of incidents. The active reports are in `_postmortems`.
- [[releases/+releases.md]]: Contains release notes and documentation for various versions and feature enhancements of the Gaia platform, including the v3 StreamBuffer release.
- [[reports/+reports.md]]: A placeholder directory for reports and analyses. The active reports are in `_reports`.
- [[research/+research.md]]: Contains research documents and proposals exploring new technologies, architectural patterns, and integration strategies, including multi-agent orchestration and n8n integration.
- [[roadmap/+roadmap.md]]: Contains documents outlining planned features, improvements, and development status for the Gaia platform, including web interface and overall feature set roadmaps.
- [[session-states/+session-states.md]]: Contains snapshots of the project's state, detailing progress, completed work, and next steps during specific development sessions, serving as historical records of key milestones and debugging efforts.
- [[test-reports/+test-reports.md]]: Contains various reports and analyses related to the test suite, including findings on test reliability, failures, improvement plans, and the overall organization of tests.

## Files

- **[2025-01-14-work-log.md](2025-01-14-work-log.md)**: A work log from January 14, 2025, detailing the assessment and implementation of the generative asset service, including database storage, router integration, and successful end-to-end testing of image generation.
- **[aeonia-website-content.md](aeonia-website-content.md)**: A capture of the content from the `aeonia.ai` website as of July 19, 2025, detailing the company's focus on "Breath-Powered Mixed Reality Experiences" and its technology stack.
- **[AGENT_TEMPLATE.md](AGENT_TEMPLATE.md)**: A template for creating new Claude Code agents, defining the standard structure for agent metadata, purpose, capabilities, boundaries, input/output formats, and testing procedures.
- **[agent-architecture.md](agent-architecture.md)**: A guide to the GAIA Platform's agent architecture, outlining the single responsibility principle, structured communication patterns, and handoff protocols between specialized agents like `Tester`, `Builder`, and `Reviewer`.
- **[architecture-overview.md](architecture-overview.md)**: A high-level overview of the Gaia Platform's microservices architecture, detailing the responsibilities of the six core services (Gateway, Auth, Asset, Chat, KB, Web), data architecture, security model, and communication patterns.
- **[architecture-recent-updates.md](architecture-recent-updates.md)**: Summarizes recent architectural improvements, including the move to Supabase-first authentication, microservice creation automation, the service registry pattern, and KB service enhancements like deferred initialization.
- **[authentication-lessons-learned.md](authentication-lessons-learned.md)**: Captures key lessons from debugging authentication issues, emphasizing the importance of a unified authentication flow, shared configuration, and database-first validation for all API keys to prevent environment-specific failures.
- **[clean-slate-architecture-2025-10-31.md](clean-slate-architecture-2025-10-31.md)**: An exploratory research document designing a new "Dynamic Experiences" system from first principles. It details key architectural decisions, including a hybrid command model, permission-based access control, a granular file structure, and a 4-level spatial hierarchy.
- **[CLIENT_SIDE_SERVER_PLAN.md](CLIENT_SIDE_SERVER_PLAN.md)**: Outlines a development plan for a client-side server to interact with the GAIA v0.3 API, handling authentication, request routing, and response formatting locally. It details a phased implementation, from core server and CLI client to advanced features like SDK generation.
- **[current-directory-README.md](current-directory-README.md)**: A meta-document serving as an index for the `/docs/current/` directory, providing an overview of what is currently working in the main branch, including Authentication, Architecture, Deployment, Development, and Web UI.
- **[deployment-strategy.md](deployment-strategy.md)**: Details the multi-environment deployment strategy for the Gaia Platform (Development, Staging, Production), outlining the service architecture per environment, service coordination via internal DNS and NATS, database strategy, and CI/CD pipeline.
- **[how-to-invoke-agents.md](how-to-invoke-agents.md)**: A practical guide for developers on how to invoke and use Claude Code agents effectively. It covers direct invocation (`/agents:<AGENT-NAME>`), context management (`/clear`, `/compact`), and best practices for providing clear, structured requests.
- **[kb_performance_comparison.md](kb_performance_comparison.md)**: A performance comparison between Git and PostgreSQL storage backends for the KB system. It concludes that PostgreSQL is 79x faster for search, while Git is faster for simple reads. It recommends a hybrid approach for the best balance of performance, collaboration, and data safety.
- **[kb-wiki-mockup.md](kb-wiki-mockup.md)**: This document presents a series of detailed mockups for a web-based wiki interface for the Knowledge Base. It visualizes the home page, file browser, page view, editor, search results, knowledge graph, and chat integration, showcasing a clean, FastHTML-based design.
- **[kos-interface-exploration.md](kos-interface-exploration.md)**: This research document explores a "Unified Intelligence Paradigm" for the KOS interface, reconceptualizing it from a tool for managing multiple conversations into a single, natural conversation with an orchestrating intelligence. It draws inspiration from Claude Code's subagent pattern to propose a system where KOS handles all complexity (agent selection, context switching, threading) invisibly.
- **[lessons-learned.md](lessons-learned.md)**: This file is a duplicate of `authentication-lessons-learned.md`.
- **[README.md](README.md)**: The main README for the `docs/_internal` directory, explaining that it houses internal project artifacts like ADRs, post-mortems, and reports.
- **[READMEFIRST_PERSONAS_PROGRESS.md](READMEFIRST_PERSONAS_PROGRESS.md)**: This file is a duplicate of `docs/personas/README.md`, which details the status and next steps for the persona system.
- **[roadmap.md](roadmap.md)**: This file is a duplicate of `feature-roadmap.md`, which outlines the planned features and improvements for the Gaia chat platform.
- **[tester.md](tester.md)**: This file defines the "Tester" agent, a specialized Claude Code agent responsible for writing, running, and debugging tests for the GAIA platform, with a focus on Pytest, async testing, and E2E browser tests.
- `+_archive.md`: Index of archived documents.
- `+_future.md`: Index of future plans.
- `+_research.md`: Index of research documents.
- `+agents.md`: Index of agent documents.