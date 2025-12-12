# Releases

This directory contains release notes and documentation for various versions and feature enhancements of the Gaia platform.

---

## Release Notes

**[v3-streaming-buffer.md](v3-streaming-buffer.md)**
*   **Summary**: This document details the **v3 StreamBuffer release**, an intelligent streaming enhancement implemented in September 2024. It preserves word boundaries and JSON directives during SSE (Server-Sent Events) streaming, significantly improving the client experience by eliminating split words and fragmented JSON. The solution reduces chunks per message by 40% with negligible processing overhead, simplifying client-side parsing while maintaining backward compatibility.