# Overview
AzerBot v1 is a specialized Discord bot for a Warcraft role-playing community. It focuses on environmental narration and Original Character (OC) management, with strict guardrails against canon character impersonation.

# Goals
- Implement `!env` command for environmental narration using OpenRouter (LLM).
- Implement OC Card system (submission, approval, display) for non-canon characters.
- Enforce strict guardrails and "Veil Distortion" fail-safes.
- Manage costs with daily/monthly caps.

# Progress
- 2026-02-26: Initialized AzerBot v1 directory structure and configuration files.
- 2026-02-26: Defined guardrails, distortion effects, and data storage schemas.
- 2026-02-26: Implemented full bot logic in `azerbot/main.py`.
    - `!env` command with OpenRouter integration, cost control, and Veil Distortion.
    - OC System: `/oc_submit`, `/oc_approve`, `/oc_reject`, `/oc_show` and message triggers.
    - Guardrails & Audit Logging (`audit_log.jsonl`).

# Pending
- 2026-02-26: User testing and refinement.
