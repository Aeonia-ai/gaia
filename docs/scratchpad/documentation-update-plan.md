# Documentation Update Plan for `experience/interact` Endpoint

**Date:** 2025-11-05

## Overview:
This document outlines the necessary updates to the existing documentation to accurately reflect the current architecture of the GAIA platform, specifically concerning the `POST /experience/interact` endpoint and its two-pass LLM architecture. Many existing documents describe deprecated endpoints or an outdated understanding of the system.

## Key Architectural Changes to Document:
*   **Primary Endpoint:** `POST /experience/interact` is the primary endpoint for all new game logic.
*   **Deprecated Endpoints:** `/game/command` and `/game/test/simple-command` are deprecated and should not be used.
*   **Two-Pass LLM Architecture:** The `/experience/interact` endpoint uses a two-pass LLM architecture:
    *   **Pass 1:** Deterministic logic (JSON output).
    *   **Pass 2:** Creative narrative generation.
*   **Game Logic Location:** Game logic is defined in markdown files located in `experiences/{experience_id}/game-logic/`.
*   **NATS Integration:** Real-time world updates are handled via NATS, with per-request subscriptions.

## Proposed Documentation Updates:

### 1. Rewrite/Major Update (High Priority):
*   `docs/concepts/game-loop.md`: This document likely describes the old game loop. It needs a complete rewrite to focus on `experience/interact`, the two-pass LLM, and NATS integration.
*   `docs/guides/adding-new-game-logic.md`: This guide is critical for developers. It must be rewritten to exclusively use `experience/interact` and detail the process of defining game logic in `experiences/{experience_id}/game-logic/` markdown files.
*   `docs/technical-design/llm-integration.md`: This document needs a major update to detail the two-pass LLM architecture, including the deterministic JSON output and creative narrative generation.
*   `docs/reference/api-endpoints.md`: This document needs to clearly mark `/game/command` and `/game/test/simple-command` as deprecated and provide comprehensive documentation for `POST /experience/interact`.

### 2. Minor Update/Correction (Medium Priority):
*   `docs/README.md`: Update the overview to highlight `experience/interact` as the central interaction point.
*   `docs/guides/getting-started.md`: Ensure any examples or references to game interaction use `experience/interact`.
*   `docs/concepts/realtime-updates.md`: Update to reflect the NATS-based per-request subscription model for world updates.
*   `docs/designs/system-overview.md`: Ensure the system diagram and description accurately reflect the `experience/interact` flow and NATS integration.

### 3. Deprecate/Archive (Low Priority - after critical updates are done):
*   `docs/kb-fastmcp-claude-code-setup.md`: This document is likely outdated given the new architecture. Review and potentially archive or update with a clear deprecation notice.
-   `docs/kb-fastmcp-integration-status.md`: This document is likely a historical status update and can be archived.
-   `docs/kb-fastmcp-mcp-client-config.md`: Review if this is still relevant or needs to be updated for the new `experience/interact` flow.

---

## Verification Status

**Verified By:** Gemini
**Date:** 2025-11-12

This document proposes a plan to update documentation based on several key architectural changes. The verification confirms that the underlying architectural claims are accurate and reflect the current state of the codebase.

-   **✅ Primary Endpoint (`POST /experience/interact`):** **VERIFIED**.
    -   **Evidence:** The endpoint is defined in `app/services/kb/experience_endpoints.py` and is configured as the main entry point for game logic, delegating to the `ExperienceCommandProcessor`.

-   **✅ Deprecated Endpoints (`/game/command`, `/game/test/simple-command`):** **VERIFIED**.
    -   **Evidence:** These endpoints exist in `app/services/kb/game_commands_api.py` but are noted as legacy implementations, with the new `interact` endpoint being the replacement.

-   **✅ Two-Pass LLM Architecture:** **VERIFIED**.
    -   **Evidence:** The `process_llm_command` method in `app/services/kb/kb_agent.py` implements the described two-pass system, with the first pass for deterministic logic and the second for creative narrative generation.

-   **✅ Game Logic Location:** **VERIFIED**.
    -   **Evidence:** The `_load_command_markdown` method in `app/services/kb/kb_agent.py` constructs paths to `experiences/{experience_id}/game-logic/`, confirming this as the location for markdown-based game logic.

-   **✅ NATS Integration:** **VERIFIED**.
    -   **Evidence:** NATS integration for real-time updates is confirmed in `app/services/kb/unified_state_manager.py` (publishing) and `app/services/chat/unified_chat.py` (subscribing), matching the per-request subscription model described.

**Conclusion:** The architectural premises of this documentation update plan are accurate. The plan correctly identifies the key architectural changes that need to be documented.
