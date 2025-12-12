# Streaming API

This section provides comprehensive documentation for GAIA's Streaming API, covering Server-Sent Events (SSE) implementation, message formats, and client integration guides for real-time AI responses.

---

## Streaming API Documents

**[sse-chunking-implementation.md](sse-chunking-implementation.md)**
*   **Summary**: This document details the implementation of Server-Sent Events (SSE) chunking in the GAIA chat service. It explains how the service converts LLM streaming responses into properly formatted SSE events, including headers, various event types (`start`, `content`, `done`), and the necessary client-side buffering requirements. It highlights the v3 StreamBuffer, which intelligently preserves word and JSON boundaries and batches phrases for improved client-friendliness and a reduced chunk count.

**[streaming-api-guide.md](streaming-api-guide.md)**
*   **Summary**: This guide documents how to use GAIA's streaming API for real-time AI responses using Server-Sent Events (SSE). It covers the request/response formats for the `/api/v0.3/chat` and `/api/v1/chat` endpoints when `stream: true` is set, and provides detailed C# and Python client implementation examples for consuming the SSE stream, including handling event types and client-side buffering.
