# Database Documentation

This section provides comprehensive documentation for the Gaia Platform's database architecture, implementation, portability, and lessons learned from its development.

---

## Database Documents

**[database-architecture.md](database-architecture.md)**
*   **Summary**: This document outlines the simplified hybrid database architecture of the Gaia Platform, utilizing PostgreSQL for all application data, Supabase for authentication, and Redis for caching across local, dev, staging, and production environments. It details the distribution of these databases, the data flow, what's stored where (including current tables and planned RBAC/Experience Platform tables), and the authentication flow. It also highlights important limitations of shared authentication, best practices, security considerations, and migration strategies.

**[portable-database-architecture.md](portable-database-architecture.md)**
*   **Summary**: This document defines a portable database architecture for the Gaia Platform, emphasizing one database per environment (`gaia-db-dev`, `gaia-db-staging`, `gaia-db-prod`), complete environment isolation, and a provider-agnostic design using standard PostgreSQL features. It details core and service-specific schema structures, connection string patterns for various cloud providers (Fly.io, AWS RDS, Google Cloud SQL), portability features like automatic URL conversion and connection pooling, deployment processes, scaling strategies (vertical, horizontal, future sharding), backup/recovery, monitoring, and security considerations.

**[postgresql-simplicity-lessons.md](postgresql-simplicity-lessons.md)**
*   **Summary**: This document captures critical meta-learning lessons from implementing RBAC with PostgreSQL, highlighting the "fast approach" trap, the anti-pattern of compatibility layers, and the importance of understanding error message progression. It emphasizes using databases for their strengths, avoiding over-engineering, and the value of starting with minimal implementations. Key takeaways include committing to simplicity, avoiding leaky abstractions, validating at boundaries, and recognizing when to stop and rethink complex approaches.