# Authentication

This section provides documentation on the GAIA platform's authentication mechanisms, including the current API key and JWT system, and future plans for OAuth 2.0 integration.

---

## Authentication Documents

**[api-authentication-guide.md](api-authentication-guide.md)**
*   **Summary**: This guide establishes the critical rules for API authentication, mandating the use of a single shared `API_KEY` from `.env` that is validated against the database. It explicitly forbids service-specific API keys and configurations to ensure 100% code and behavior parity between local and remote environments.

**[gateway-auth-api-contract.md](gateway-auth-api-contract.md)**
*   **Summary**: This document defines the HTTP status codes and response formats for the v1 and v0.3 authentication endpoints (`/login`, `/register`, `/validate`, `/refresh`) provided by the Gateway service, ensuring a predictable and consistent contract for clients.

**[oauth-2-extension-spec.md](oauth-2-extension-spec.md)**
*   **Summary**: A **design specification** for a future, unimplemented OAuth 2.0 extension to the GAIA platform. It outlines the plan to add full support for Authorization Code and Client Credentials flows, scoped permissions, and client registration to enable third-party integrations and enterprise SSO, while maintaining backward compatibility with the existing authentication system.
