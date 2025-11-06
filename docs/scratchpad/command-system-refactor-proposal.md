# Command System Refactor Proposal: Unified ExperienceCommandProcessor

**Date:** 2025-11-06
**Status:** Proposed Design
**Related Documents:**
- `websocket-architecture-decision.md`
- `websocket-and-kb-content-analysis.md`
- `simulation-architecture-overview.md`

---

## 1. Problem Statement: Divergent Command Processing

The current GAIA platform exhibits architectural divergence in how player commands are processed:

*   **HTTP `/experience/interact`:** Utilizes a sophisticated "two-pass" LLM system, interpreting Markdown-driven game logic to determine state changes and generate narrative. This is flexible but can be slower.
*   **WebSocket `/ws/experience` (Demo Implementation):** Employs hardcoded Python functions for specific actions (e.g., `collect_bottle`) and canned responses, completely bypassing the LLM logic. This is fast but rigid and not extensible.

This divergence creates:
*   **Technical Debt:** Duplicated logic, inconsistent behavior, and difficulty in maintenance.
*   **Lack of Modularity:** Game logic is tied to specific transport layers.
*   **Limited Scalability:** Inability to easily extend command processing across new interaction channels.

---

## 2. Core Refactoring: Introduce `ExperienceCommandProcessor`

The central piece of the refactor is to introduce a new component: the `ExperienceCommandProcessor`. This will be a module/class within the **KB Service** (`app/services/kb/`) and will serve as the **single, universal entry point for all player commands**, regardless of their origin.

**Nature of the Processor:**
*   **Orchestrator & Smart Router:** Its primary role is to receive a command and intelligently route it to the appropriate handler.
*   **Transport-Agnostic:** It has no knowledge of HTTP, WebSockets, or any other transport layer. It exposes a simple, internal interface like `process_command(user_id, experience_id, command_data)`.
*   **Stateless:** The processor itself is stateless, relying on the `UnifiedStateManager` for all state interactions.

---

## 3. Key Feature Additions & Changes

### 3.1. Unified Command Pipeline (Endpoint Refactoring)

*   **Goal:** Simplify transport layers and funnel all commands through the `ExperienceCommandProcessor`.
*   **Changes:**
    *   **HTTP `/experience/interact` Endpoint:** Will be refactored to become a thin wrapper. It will authenticate the user, extract the command from the request, and pass it directly to the `ExperienceCommandProcessor`.
    *   **WebSocket `/ws/experience` Endpoint:** Will also be refactored into a thin transport layer. It will manage the connection, authenticate the user, extract the command from WebSocket messages, and pass it to the `ExperienceCommandProcessor`.
*   **Benefit:** Eliminates duplicate logic, ensures consistent command handling across all interaction channels.

### 3.2. Standardized Command Contract

*   **Goal:** Ensure all command handlers (Python or LLM-interpreted) adhere to a uniform interface.
*   **Contract:** Every command handler will:
    *   Accept standard inputs (e.g., `user_id`, `experience_id`, `command_parameters`).
    *   Return a **standardized result object** containing the mechanical outcome of the command.
*   **Standard Result Object Structure:**
    ```json
    {
      "success": true,                       // Boolean: Was the command successful?
      "state_changes": { ... },              // Structured JSON: State modifications to apply (e.g., player inventory, world items)
      "message_to_player": "...",            // String: Simple, direct feedback for the player (e.g., "You collected the bottle.")
      "metadata": { ... }                    // Optional: Any other structured data for the client
    }
    ```
*   **Benefit:** Promotes modularity, testability, and allows the `ExperienceCommandProcessor` to uniformly process results without knowing the handler's internal implementation.

### 3.3. Hybrid Command Implementation (Two Types of Handlers)

The `ExperienceCommandProcessor` will route commands to handlers whose implementations can be one of two types:

*   **Hardcoded Python Handlers (The "Fast Path"):**
    *   **Purpose:** For simple, deterministic, high-performance actions.
    *   **Examples:** `collect_item`, `drop_item`, `move_to_location`.
    *   **Implementation:** Pure Python functions that directly interact with the `UnifiedStateManager` to read and modify game state. These handlers have full access to player view and world state.
    *   **Benefit:** Provides low-latency, predictable execution for core mechanics.

*   **LLM-Interpreted Handlers (The "Flexible Logic Path"):**
    *   **Purpose:** For complex, narrative-driven, or context-sensitive actions where flexibility is paramount.
    *   **Examples:** `talk_to_npc`, `look_around`, `examine_item`, `persuade_guard`.
    *   **Implementation:** Python functions that act as orchestrators for an LLM call. They gather context (player state, world state, relevant Markdown game logic files), construct a prompt, and call an LLM. The LLM's output for these handlers will be the **standardized result object** (structured data, not narrative prose).
    *   **Benefit:** Leverages LLM power for dynamic logic without sacrificing structured outcomes.

### 3.4. Refined LLM Role (The "Two-Pass" System 2.0)

The "two-pass" LLM system is formalized and applied consistently:

*   **Pass 1 (Intent Recognition & Logic Execution):**
    *   **Input:** Player's natural language input.
    *   **LLM's Role:** To translate natural language into a **structured command** (e.g., `{"action": "collect_item", "item_id": "bottle_of_joy_3"}`). This command is then fed into the `ExperienceCommandProcessor`.
    *   **For LLM-Interpreted Handlers:** The LLM *within* the handler executes the game logic from Markdown and returns the **standardized result object** (structured data).
*   **Pass 2 (Narrative Generation - Deferred):**
    *   **Input:** The structured result object from the command execution.
    *   **LLM's Role:** To take this structured outcome and generate a rich, creative, natural language response for the player. This pass is explicitly deferred for later implementation.

---

## 4. Architectural Outcome & Benefits

This refactoring creates a robust, modular, and highly flexible command system:
*   **Single Source of Truth:** All game logic is centralized in the `ExperienceCommandProcessor`.
*   **Clear Separation of Concerns:** Transport, command routing, logic execution, and narrative generation are distinct.
*   **Optimal Performance:** The "fast path" ensures low latency for critical actions.
*   **Maximum Flexibility:** LLMs are leveraged where they provide the most value (dynamic logic, natural language understanding).
*   **Testability & Maintainability:** Each component has a clear responsibility and can be tested independently.
*   **Scalability:** The system can be scaled by adding more command handlers or optimizing specific paths.

This proposal provides a clear roadmap for evolving the GAIA platform's interaction model into a production-ready state.
