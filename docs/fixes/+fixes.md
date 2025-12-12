# Fixes

This directory contains documentation for specific bug fixes implemented in the Gaia platform. Each document typically details the issue, root cause, the implemented fix, and steps for verification.

---

## Bug Fixes

**[persona-lost-after-tool-calls.md](persona-lost-after-tool-calls.md)**
*   **Summary**: This document details a fix for a high-severity bug where Knowledge Base tool calls were losing their persona context. The issue stemmed from `app/services/chat/unified_chat.py`, where a hardcoded generic system prompt ("You are a helpful assistant") was used in the second LLM call following a tool execution, overriding the original persona. The fix ensures persona consistency by passing the original `system_prompt` to all subsequent LLM calls within the same request flow.