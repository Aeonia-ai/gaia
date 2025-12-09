# Chat Routing and KB Architecture

**Status:** Verified
**Date:** 2025-11-12

This document provides a verified overview of the integrated chat routing and Knowledge Base (KB) architecture in the GAIA platform. It reflects the current production implementation, which has superseded earlier designs like the one described in `intelligent-chat-routing.md`.

## Core Architecture: The `UnifiedChatHandler`

The entire chat and tool routing system is centralized in the `UnifiedChatHandler` class, located in `app/services/chat/unified_chat.py`. This handler represents a significant architectural shift towards a single, intelligent model call for routing, rather than a multi-step chain-of-thought process.

### Key Principles:

1.  **Single Model Call:** The system makes one call to the LLM with a full set of available tools, letting the model decide whether to respond directly to the user or to use one or more tools.
2.  **Centralized Tool Definition:** All available tools, both for KB interactions and other functions (like file operations or asset generation), are gathered and passed to the model in this single call.
3.  **Authoritative Data Source:** The KB service remains the authoritative source for game content and world state. The chat service queries it via the `kb_tools`.

## Data Flow

Here is the step-by-step data flow for a typical user request:

1.  **Request Reception:** A user sends a message to the Gateway, which forwards it to the Chat Service's `/api/v0.3/chat` endpoint.

2.  **`UnifiedChatHandler` Initialization:** The `chat` method in `app/services/chat/main.py` instantiates `UnifiedChatHandler`.

3.  **Prompt & Tool Aggregation:**
    *   The handler retrieves the current persona's system prompt using `UnifiedChatHandler.get_routing_prompt()`.
    *   It gathers all available tools:
        *   **KB Tools (`KB_TOOLS`):** Imported from `app/services/chat/kb_tools.py`. These are functions decorated with `@tool` that interact with the KB service (e.g., `get_kb_entry`, `search_kb`).
        *   **Routing Tools (`routing_tools`):** Defined directly within `UnifiedChatHandler`. These include tools for file operations, asset generation, and other non-KB tasks.

4.  **The "Auto" Tool Choice Call:**
    *   The handler invokes the LLM using the `acompletion` method.
    *   Crucially, it sets `tool_choice="auto"`. This gives the LLM the autonomy to decide between:
        a.  **Direct Response:** Generating a text response directly if no tool is needed.
        b.  **Tool Call:** Emitting a tool call if the user's request requires accessing the KB or performing another action.

5.  **Response Handling:**
    *   **If Direct Response:** The handler streams the LLM's response directly back to the user.
    *   **If Tool Call:** The handler executes the tool(s) specified by the model, gets the results, and then sends the results back to the model to generate a final response for the user.

## Code References

-   **Primary Logic:** `app/services/chat/unified_chat.py` (specifically the `UnifiedChatHandler` class and its `chat` method).
-   **KB Tool Definitions:** `app/services/chat/kb_tools.py`.
-   **Endpoint:** `app/services/chat/main.py` (the `/api/v0.3/chat` endpoint).
-   **Prompt Management:** `app/shared/prompt_manager.py`.

## Architectural Diagram

```
+-----------------+      +------------------+      +----------------------+
|   User Client   |----->|     Gateway      |----->|     Chat Service     |
+-----------------+      +------------------+      | (main.py)            |
                                                   +-----------+----------+
                                                               |
                                                               v
+--------------------------------------------------------------+
| `UnifiedChatHandler` (`unified_chat.py`)                     |
|                                                              |
|  1. Get Persona Prompt (`prompt_manager.py`)                 |
|  2. Aggregate Tools:                                         |
|     - `KB_TOOLS` (from `kb_tools.py`)                        |
|     - `routing_tools` (local)                                |
|                                                              |
|  3. LLM Call (`tool_choice="auto"`)                          |
|     |                                                        |
|     +-----> (Direct Response) ----> User                     |
|     |                                                        |
|     +-----> (Tool Call) -> Execute Tool -> LLM -> User       |
|                                                              |
+-----------------------------+--------------------------------+
                              |
                              v
+-----------------------------+--------------------------------+
| KB Service (`kb_agent.py`) or Other Tools (File Ops, etc.)   |
+--------------------------------------------------------------+
```

## Conclusion

This integrated architecture is simpler and more efficient than previous multi-step routing designs. By empowering the LLM with a comprehensive set of tools and the "auto" tool choice, the system can dynamically and intelligently handle a wide range of user requests with minimal latency and code complexity. The `UnifiedChatHandler` is the single source of truth for this critical functionality.

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

This document's claims about the chat routing and KB architecture have been verified against the codebase.

-   **✅ Core Architecture (`UnifiedChatHandler`):** **VERIFIED**.
    -   **Evidence:** The `UnifiedChatHandler` class in `app/services/chat/unified_chat.py` is the central component for chat processing. It uses a single model call with `tool_choice="auto"` and aggregates tools from `kb_tools.py` and its own `routing_tools`.

-   **✅ Data Flow:** **VERIFIED**.
    -   **Evidence:** The data flow described is accurate. Requests are routed from the Gateway to the Chat Service, which uses the `UnifiedChatHandler`. The handler retrieves persona prompts, aggregates tools, and makes a single LLM call. The logic for handling both direct responses and tool calls is present.

-   **✅ Code References:** **VERIFIED**.
    -   **Evidence:** All code references in the document point to the correct files and accurately describe the functionality within those files.

**Conclusion:** This document is a correct and accurate description of the implemented chat routing and KB architecture. All key claims have been verified.
