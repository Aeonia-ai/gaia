# Architectural Patterns

This section details common architectural patterns and best practices used throughout the Gaia Platform's microservices, covering service initialization, creation, discovery, and deferred loading.

---

## Architectural Patterns Documents

**[deferred-initialization-pattern.md](deferred-initialization-pattern.md)**
*   **Summary**: This document addresses the problem of slow service startups due to extensive initialization tasks (e.g., cloning large Git repositories, downloading models) by introducing the deferred initialization pattern. It outlines an architecture where services start immediately, perform time-consuming tasks in the background, and store data on persistent volumes. The document details the implementation (immediate startup, background task, enhanced health endpoint), benefits (fast startup, persistent data, observable status), use cases, and anti-patterns to avoid, with a real-world example from the KB service.

**[service-creation-automation.md](service-creation-automation.md)**
*   **Summary**: This guide details the automated process for creating new microservices within the Gaia Platform, significantly reducing boilerplate. It introduces a `create-new-service.sh` script for scaffolding service directories, Dockerfiles, and Fly.io configs, alongside a `ServiceRegistry` pattern for centralized configuration. The document provides a step-by-step process for adding a new service, including local testing and deployment to Fly.io, and discusses advanced patterns like generic route forwarding and service-to-service communication.

**[service-discovery-guide.md](service-discovery-guide.md)**
*   **Summary**: This document describes the service discovery architecture of the Gaia platform, which aims to eliminate hardcoded routes in the gateway by enabling automatic discovery of microservice endpoints. It details the solution's core components: a `ServiceRegistry` for healthy services and routes, enhanced health endpoints that expose routes, and dynamic gateway routing. It highlights current implementations in various services and the gateway, but notes a significant discrepancy where the gateway is not currently utilizing the service discovery mechanism, making the document outdated and misleading in that regard.

**[service-initialization-pattern.md](service-initialization-pattern.md)**
*   **Summary**: This document establishes a consistent and industry-recommended pattern for service initialization across all Gaia microservices, addressing previous inconsistencies that hindered service discovery. It outlines a five-step order: (1) FastAPI app with lifespan, (2) basic `/health` endpoint, (3) all middleware, (4) all business logic routes/routers, and finally (5) enhanced health endpoint with route discovery. The document emphasizes why this order matters, highlights common mistakes, and provides a service checklist for verification.