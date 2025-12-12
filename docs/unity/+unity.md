# Unity Integration

This directory contains documentation specifically for developers integrating Unity clients with the GAIA platform.

---

## Key Documents

**[unity-integration-guide.md](unity-integration-guide.md)**
*   **Summary**: This guide provides a quick reference for Unity developers integrating with the GAIA platform's chat services. It specifies the API endpoint, request/response formats for both basic and streaming chat, and provides a C# code example using `Best.HTTP` for handling Server-Sent Events (SSE), as the standard EventSource class does not support the required POST requests. The guide also covers parsing for embedded JSON directives and identifying message roles (system, assistant, user) to control what is displayed to the player.
