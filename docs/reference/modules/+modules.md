# Shared Modules Documentation

This section provides documentation for reusable modules within the Gaia Platform, covering instrumentation, prompt management, and tool provisioning.

---

## Shared Modules Documents

**[instrumentation.md](instrumentation.md)**
*   **Summary**: This document describes the Instrumentation module (`app/shared/instrumentation.py`), which provides tools for comprehensive performance monitoring and timing throughout the platform. It details the `TimingContext` class for tracking request stages, key methods like `record_stage` and `get_total_duration`, and features a global `InstrumentationSystem` for managing contexts and providing decorators (`@instrument_async_operation`) and context managers (`timing_scope`) for automatic timing. It lists typical tracked stages, integration points, and notes minimal performance impact.

**[prompt-manager.md](prompt-manager.md)**
*   **Summary**: This document describes the Prompt Manager module (`app/shared/prompt_manager.py`), which is responsible for managing system prompts for the chat service. It details the `get_system_prompt` method, which retrieves personalized AI system prompts by integrating with the persona system (PostgreSQL-based persona service), falling back to a default persona or a hardcoded default prompt if no user-specific persona is found. It highlights its use by the Chat service and robust error handling.

**[tool-provider.md](tool-provider.md)**
*   **Summary**: This document describes the Tool Provider module (`app/shared/tool_provider.py`), currently a simplified placeholder for LLM tool/function calling capabilities. It outlines the `get_tools_for_activity` method (currently returning an empty list) and the `initialize_tools` method (a no-op), providing the basic infrastructure for future tool integration. It notes its placeholder status and outlines future enhancements like search, calculation, data retrieval, and external API integration tools.
