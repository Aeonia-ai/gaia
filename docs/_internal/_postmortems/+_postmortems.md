# Postmortems

This directory contains postmortem reports detailing incidents, their root causes, resolutions, and lessons learned to prevent recurrence.

---

## Files

**[2024-08-04-ai-response-persistence.md](2024-08-04-ai-response-persistence.md)**
*   **Summary**: This postmortem details a high-severity AI response persistence failure on August 4, 2024. The root cause was identified as the SSE endpoint attempting to save AI responses *after* sending the `[DONE]` signal, causing the browser to close the connection prematurely and preventing the save operation. The resolution involved moving critical save operations to occur *before* yielding completion signals. Lessons learned emphasize understanding SSE lifecycles, the silent nature of such failures, and the importance of E2E testing for data persistence.

## Purpose

Postmortems document significant incidents, root causes, and preventive measures. They serve as learning artifacts to improve system reliability and prevent recurrence.

## Template

Each postmortem should include:
- **Incident Summary**: What happened and impact
- **Timeline**: Key events during the incident
- **Root Cause**: Why it happened
- **Resolution**: How it was fixed
- **Lessons Learned**: What we learned
- **Action Items**: Preventive measures

## Parent
[../+docs.md](../+docs.md)