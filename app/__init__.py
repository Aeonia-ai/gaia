"""
Gaia Platform - Microservices Backend for Aeonia

This package implements the Gaia Platform, a microservices-based backend
that replaces the LLM Platform monolith while maintaining full client compatibility.

Architecture:
- Gateway Service: Routes client requests to appropriate services  
- Auth Service: Handles authentication (JWT + API keys)
- Asset Service: Universal Asset Server functionality
- Chat Service: LLM interactions with MCP-agent workflows
- Shared modules: Common utilities for all services

The platform maintains backward compatibility with existing Unity, Unreal,
and NextJS clients while adding enhanced inter-service coordination via NATS.
"""

__version__ = "1.0.0"
__author__ = "Aeonia Team"
