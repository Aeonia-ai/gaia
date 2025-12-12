# Gateway Documentation

This section provides comprehensive documentation for the Gaia Platform's Gateway service, focusing on its authentication proxying patterns and critical HTTP protocol compliance.

---

## Gateway Documents

**[authentication-proxying-patterns.md](authentication-proxying-patterns.md)**
*   **Summary**: This document describes the `_auth` injection pattern used by the GAIA gateway for proxying authenticated requests to backend services. It details how authentication information is injected into the request body and emphasizes the critical need to manage the `Content-Length` header when modifying request bodies to avoid HTTP protocol errors. The document also outlines the responsibilities for both the gateway and backend services, provides an implementation checklist, and highlights the architectural benefits of service separation, security, performance, and testability.
