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
- 2026-03-12: Hardened RP response delivery and observability.
    - Discord-safe splitting for long replies (`split_for_discord`) with multi-message fallback.
    - Visible failure handling for `!env` generation/assembly/send failures with neutral user-facing messages.
    - Structured error logging (`error_log.jsonl`) and structured debug logging (`debug_log.jsonl`).
    - Per-reply debug fields include parsed/remembered/final place/char/creature, split status, response length, and scene summary strategy/preview.
- 2026-03-12: Stabilized scene continuity to prevent cross-scene contamination.
    - Scene summaries are now short and neutral (max 300 chars) and cleared on place change.
    - When `!char` is active, scene summaries store neutral continuity (place/mood/creature presence) instead of raw response text.
- 2026-03-12: Enforced strict third-person narration with automatic repair.
    - System prompt explicitly bans first-person and second-person outside quoted dialogue.
    - Post-generation validator scans narration outside quotes; one automatic rewrite retry; neutral fallback if still invalid.
- 2026-03-12: Made `!char` conservative and cue-based.
    - Added explicit character presence policy to avoid assumed proximity/intimacy or player interrogation.
    - Detects direct address in the player's post and allows direct response only when cued.
- 2026-03-12: Added moderator scene lifecycle controls.
    - `!scene_end` clears per-channel scene memory (moderator-only).
    - `!scene_status` reports current stored place/summary presence/last update.
- 2026-03-12: Added curated player-character infrastructure.
    - New directory `data/player_characters/` and loader `load_player_character(card_id)`.
    - New bindings file `data/player_bindings.json` and resolver `resolve_player_character(user_id)`.
    - Automatic injection of bound player character card text into prompt context (no tag changes; no effect for unbound users).
- 2026-03-12: Added RP tag validation.
    - Enforces safe tag configuration and prevents pipeline crashes; invalid configs reply with a neutral error message.
- 2026-03-12: Improved audit logging coverage.
    - Scene control actions and per-`!env` tag context now append structured entries into `azerbot/audit_log.jsonl`.
- 2026-03-12: Increased generation headroom to reduce mid-sentence truncation.
    - OpenRouter `max_tokens` increased from 180 to 280.

# Pending
- 2026-02-26: User testing and refinement.
