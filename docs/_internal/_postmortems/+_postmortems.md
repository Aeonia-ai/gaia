# Postmortems

This directory contains postmortem reports detailing incidents, their root causes, resolutions, and lessons learned to prevent recurrence.

## Files

**[2024-08-04-ai-response-persistence.md](2024-08-04-ai-response-persistence.md)**
*   **Summary**: This postmortem details a high-severity AI response persistence failure on August 4, 2024. The root cause was identified as the SSE endpoint attempting to save AI responses *after* sending the `[DONE]` signal, causing the browser to close the connection prematurely and preventing the save operation. The resolution involved moving critical save operations to occur *before* yielding completion signals. Lessons learned emphasize understanding SSE lifecycles, the silent nature of such failures, and the importance of E2E testing for data persistence.