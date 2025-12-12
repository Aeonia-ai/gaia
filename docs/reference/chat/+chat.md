# Chat Service Documentation

This section provides comprehensive documentation for the GAIA Chat Service, detailing its architecture, implementation, intelligent routing, persistence mechanisms, and integration with personas and VR/AR directives.

---

## Chat Service Documents

**[chat-service-cleanup-analysis.md](chat-service-cleanup-analysis.md)**
*   **Summary**: This document analyzes the GAIA chat service codebase, identifying that a significant portion (80% or ~6,200 lines) consists of unused "dead code" from abandoned experimental optimization attempts. It categorizes files into "production" (to keep) and "dead code" (to delete), highlights files requiring further investigation, and provides a cleanup process with an impact analysis showing substantial reductions in file count and code lines for a clearer, more secure, and faster service.

**[chat-service-implementation.md](chat-service-implementation.md)**
*   **Summary**: This document outlines the GAIA chat service's intelligent routing architecture, which integrates personas, dynamic tool selection, and real-time directives for personalized VR/AR conversations. It details the core service structure, the `UnifiedChatHandler` for routing decisions, the persona system (database schema, CRUD, caching), the tools system (KB and routing tools), system prompt construction, and the directive system (JSON-RPC for VR/AR features like `pause`). Performance optimizations (tool usage reduction, hot loading, intelligent routing, caching) and examples are also covered.

**[chat-v2-clean-architecture.md](chat-v2-clean-architecture.md)**
*   **Summary**: This document proposes a ground-up rebuild of the chat service (V2) based on core principles of single source of truth, clear separation of concerns, performance, testability, and minimalism. It outlines a clean message pipeline, a structured message array (single system message), persona integration (identity, not functionality), a tool-based routing strategy, and a clean file structure. It also details API design, testing strategy, migration, and key differences from V1, emphasizing performance and consistency.

**[directive-system-vr-ar.md](directive-system-vr-ar.md)**
*   **Summary**: This document describes the directive system, which enables real-time control of VR/AR experiences through JSON-RPC commands embedded in chat responses, exemplified by the `pause` method (`{"m":"pause","p":{"secs":X}}`). It explains when directives are enabled (v0.3 API or explicit flag), how they integrate into the system prompt, and provides real-world applications in meditation, exercise, and storytelling. Client-side parsing/execution, future directive types, performance, use cases, verification status, and best practices are also covered.

**[intelligent-tool-routing.md](intelligent-tool-routing.md)**
*   **Summary**: This document details GAIA's intelligent tool routing system, which optimizes LLM response times by using both OpenAI-format tool definitions and natural language "tool instructions" to guide the LLM on when to use tools versus direct responses. It categorizes tools (KB, routing), explains their combination, outlines the request processing flow (context building, prompt assembly, single LLM decision, response handling), provides real-world examples, and discusses performance metrics, configuration, and best practices.

**[unified-chat-persistence.md](unified-chat-persistence.md)**
*   **Summary**: This document describes the conversation persistence architecture for GAIA's unified chat system, focusing on the web UI, gateway, and chat service interaction. It details how the gateway routes `/api/v1/chat` to `/chat/unified` and proxies conversation endpoints. It highlights automatic conversation creation, message persistence, and `conversation_id` delivery in response metadata. The document also identifies redundant web UI conversation management and proposes a migration path for simplification.

**[web-ui-chat-flow.md](web-ui-chat-flow.md)**
*   **Summary**: This document describes the current web UI chat flow, outlining its interaction with the Gateway and Chat Service, use of Server-Sent Events (SSE) for streaming, and manual conversation management. It identifies significant redundancy in the web UI's handling of conversations due to the unified endpoint's automatic persistence. The document proposes simplification opportunities, including removing manual conversation management, switching to a cleaner v0.3 response format, and streamlining web UI chat logic.
