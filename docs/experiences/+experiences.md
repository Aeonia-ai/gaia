# Experiences

This directory contains documentation related to specific interactive game experiences built on the GAIA platform, such as Wylding Woods. It includes details about their game world architecture, mechanics, and testing procedures.

---

## Experience-Specific Documents

**[testing-experience-changes.md](testing-experience-changes.md)**
*   **Summary**: This guide outlines how to test changes to the markdown-based experience logic. It emphasizes the use of direct API testing against the `/experience/interact` endpoint with Python validation scripts. The document highlights that markdown files and `world.json` are hot-loaded, meaning that most content and logic changes do not require a Docker rebuild. It provides example test scripts, common troubleshooting tips for issues like timeouts and incorrect location context, and best practices for writing atomic, state-aware tests.

**[wylding-woods-game-world.md](wylding-woods-game-world.md)**
*   **Summary**: This document details the game world architecture for the **Wylding Woods** experience, which uses a hybrid GPS (outdoor) + VPS (indoor) positioning model. It focuses on the Phase 1 demo scope within Woander's Magical Shop, outlining the sublocations (e.g., `counter`, `fairy_door_main`), NPCs (Woander and Louisa), and the core "dream bottle" scavenger hunt quest. It also covers the technical implementation, including the file structure, `/experience/interact` API endpoint, and the two-pass LLM execution model for separating game logic from narrative generation.