import re
from typing import Dict, Any, Optional, Tuple, List
from card_loader import load_characters, load_places, load_creatures, resolve_creature, list_creature_ids, resolve_player_character, load_player_character
from scene_memory import get_state

def _index_by_id(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for it in items:
        cid = str(it.get("id", "")).strip().lower()
        if cid:
            out[cid] = it
    return out

def _infer_creature_escalation_permission(rp_text: str, scene_summary: str) -> str:
    text = (rp_text or "").lower()
    summary = (scene_summary or "").lower()

    direct_patterns = [
        r"\blunges\b",
        r"\battacks?\b",
        r"\bcharges?\b",
        r"\bpounces?\b",
        r"\bleaps?\b",
        r"\bslashes?\b",
        r"\bswings?\b",
        r"\bstrikes?\b",
        r"\bgrabs?\b",
        r"\bclaws?\b",
        r"\bbites?\b",
        r"\bis upon\b",
        r"\bcollides?\b",
    ]
    for pat in direct_patterns:
        if re.search(pat, text):
            return "direct_confrontation_allowed"

    engagement_markers = ["combat", "battle", "fight", "brawl", "struggle", "clash", "bleeding", "wounded", "attack", "engaged"]
    if any(m in summary for m in engagement_markers):
        return "direct_confrontation_allowed"

    return "pressure_only"

def _infer_character_interaction_permission(rp_text: str, character: Dict[str, Any]) -> str:
    text = (rp_text or "").lower()
    name = str(character.get("name", "")).strip().lower()
    cid = str(character.get("id", "")).strip().lower()

    cues: List[str] = []
    if name:
        cues.append(name)
    if cid and cid != name:
        cues.append(cid)

    for cue in cues:
        if not cue:
            continue
        if re.search(rf"(^|[\s,.:;!?]){re.escape(cue)}([\s,.:;!?]|$)", text):
            return "direct_address_allowed"
        if f"@{cue}" in text:
            return "direct_address_allowed"
        if f"to {cue}" in text:
            return "direct_address_allowed"
    return "conservative_presence"

def _response_is_incomplete(text: str) -> bool:
    text = str(text or "").strip()

    if not text:
        return True

    if text[-1] not in ".!?\"":
        return True

    incomplete_endings = [
        " as",
        " when",
        " while",
        " from",
        " into",
        " toward",
        " towards",
        " and",
        " but"
    ]

    lower = text.lower()
    for ending in incomplete_endings:
        if lower.endswith(ending):
            return True

    return False

def repair_incomplete_response(response: str) -> str:
    r = str(response or "")
    if _response_is_incomplete(r):
        return r.rstrip() + " The moment settles without further incident."
    return r

def _build_system_prompt(
    place: Dict[str, Any],
    character: Optional[Dict[str, Any]],
    creature: Optional[Dict[str, Any]],
    scene_summary: str,
    creature_escalation_permission: str,
    character_interaction_permission: str,
    player_character_id: str,
    player_character_text: str
) -> str:
    lines = []
    lines.append("You are AzerBot, a roleplay partner for Azeroth.")
    lines.append("You act as a narrative engine and RP partner within Azeroth.")
    lines.append("World knowledge must come only from the provided cards and scene state.")
    lines.append("Do not contradict the active place or the scene summary.")
    lines.append("Do not introduce sudden new locations, time jumps, or major events without cues from the user's post.")
    lines.append("Never control the player's character or describe the player's internal thoughts.")
    lines.append("Do not assume the player's identity, location, emotions, consent, or actions unless explicitly written by the player.")
    lines.append("PLAYER CHARACTER SAFETY RULES:")
    lines.append("- Never control the player's character.")
    lines.append("- Never describe the player's internal thoughts.")
    lines.append("- Never assign gender, pronouns, race, or identity to the player's character unless explicitly stated in the user's post or player character card.")
    lines.append("- If unsure, refer to the player character by name rather than pronouns.")
    lines.append("Characters should react naturally to the player's post; avoid dominating the scene.")
    lines.append("Avoid overly aggressive interrogation or commanding tone unless the player's post clearly demands it.")
    lines.append("")
    lines.append("ACTIVE PLACE CARD (authoritative):")
    lines.append(f"ID: {place.get('id','')}")
    name = place.get("display_name") or place.get("name") or ""
    if name:
        lines.append(f"NAME: {name}")
    region = place.get("region") or ""
    if region:
        lines.append(f"REGION: {region}")
    ptype = place.get("type") or ""
    if ptype:
        lines.append(f"TYPE: {ptype}")
    aliases = place.get("aliases") or []
    if isinstance(aliases, list) and aliases:
        lines.append(f"ALIASES: {', '.join([str(a) for a in aliases if str(a).strip()])}")
    tone = place.get("tone") or []
    traits = place.get("traits") or []
    merged_traits: List[str] = []
    if isinstance(tone, list):
        merged_traits.extend([str(t).strip() for t in tone if str(t).strip()])
    if isinstance(traits, list):
        merged_traits.extend([str(t).strip() for t in traits if str(t).strip()])
    if merged_traits:
        lines.append(f"TONE: {', '.join(merged_traits)}")
    summary = place.get("long_description") or place.get("summary") or ""
    if summary:
        lines.append(f"SUMMARY: {summary}")
    default_scene = place.get("default_scene") or place.get("details") or ""
    if default_scene:
        lines.append(f"DEFAULT_SCENE: {default_scene}")
    sublocations = place.get("sublocations") or []
    if isinstance(sublocations, list) and sublocations:
        names = []
        for s in sublocations:
            if not isinstance(s, dict):
                continue
            dn = str(s.get("display_name", "")).strip()
            sid = str(s.get("id", "")).strip()
            if dn:
                names.append(dn)
            elif sid:
                names.append(sid)
        if names:
            lines.append(f"SUBLOCATIONS: {', '.join(names[:10])}")
    spice_lines = place.get("spice_lines") or []
    if isinstance(spice_lines, list) and spice_lines:
        samples = [str(x).strip() for x in spice_lines if str(x).strip()][:6]
        if samples:
            lines.append("SPICE_LINES:")
            lines.extend(samples)

    monster_table = place.get("monster_table") or []
    if isinstance(monster_table, list) and monster_table:
        entries = []
        for row in monster_table[:10]:
            if not isinstance(row, dict):
                continue
            mid = str(row.get("id", "")).strip()
            weight = row.get("weight", None)
            if mid and weight is not None:
                entries.append(f"{mid}:{weight}")
            elif mid:
                entries.append(mid)
        if entries:
            lines.append(f"MONSTER_TABLE: {', '.join(entries)}")

    wildlife_table = place.get("wildlife_table") or []
    if isinstance(wildlife_table, list) and wildlife_table:
        entries = []
        for row in wildlife_table[:10]:
            if not isinstance(row, dict):
                continue
            wid = str(row.get("id", "")).strip()
            weight = row.get("weight", None)
            if wid and weight is not None:
                entries.append(f"{wid}:{weight}")
            elif wid:
                entries.append(wid)
        if entries:
            lines.append(f"WILDLIFE_TABLE: {', '.join(entries)}")
    lines.append("")

    if character:
        lines.append("ACTIVE CHARACTER CARD (optional overlay):")
        lines.append(f"CHARACTER_INTERACTION_PERMISSION: {character_interaction_permission}")
        lines.append("CHARACTER PRESENCE POLICY:")
        lines.append("- Introduce the character conservatively.")
        lines.append("- Do not assume intimacy, proximity, or prior relationship with the player.")
        lines.append("- Do not assume the player is speaking to the character unless the PLAYER POST clearly cues it.")
        lines.append("- Prefer observational presence and restrained dialogue.")
        lines.append("- Do not invent player-directed questions by default.")
        lines.append("- If the PLAYER POST directly addresses the character, a direct response is allowed.")
        lines.append(f"ID: {character.get('id','')}")
        lines.append(f"NAME: {character.get('name','')}")
        text = str(character.get("text","")).strip()
        if text:
            lines.append("CHARACTER CARD TEXT:")
            lines.append(text)
        else:
            if character.get("voice"):
                lines.append(f"VOICE: {character.get('voice')}")
            if character.get("persona"):
                lines.append(f"PERSONA: {character.get('persona')}")
            if character.get("rules"):
                lines.append(f"RULES: {character.get('rules')}")
        lines.append("")
        lines.append("When responding, narration must remain strict third-person. If the ACTIVE CHARACTER is present, quoted dialogue may be from them.")
    else:
        lines.append("When responding, speak as the world and atmosphere of Azeroth (no random character selection).")

    if player_character_text:
        lines.append("")
        lines.append("PLAYER CHARACTER CARD (automatic context):")
        if player_character_id:
            lines.append(f"ID: {player_character_id}")
        lines.append("PLAYER CHARACTER CARD TEXT:")
        lines.append(player_character_text.strip())

    if creature:
        lines.append("")
        lines.append("ACTIVE CREATURE CARD (optional pressure):")
        lines.append(f"ESCALATION_PERMISSION: {creature_escalation_permission}")
        lines.append("CREATURE ESCALATION POLICY:")
        lines.append("- Default to pressure/presence: signs, sounds, scent, movement, distant silhouettes.")
        lines.append("- Escalate gradually: partial reveal before full reveal.")
        lines.append("- Avoid direct confrontation unless the PLAYER POST clearly implies immediate contact/attack, or RECENT SCENE SUMMARY indicates active engagement.")
        lines.append("- If the tagged creature feels unusual for the place, you may acknowledge the strangeness briefly without blocking it.")
        lines.append(f"ID: {creature.get('id','')}")
        cname = creature.get("display_name") or creature.get("name") or ""
        if cname:
            lines.append(f"NAME: {cname}")
        caliases = creature.get("aliases") or []
        if isinstance(caliases, list) and caliases:
            lines.append(f"ALIASES: {', '.join([str(a) for a in caliases if str(a).strip()])}")
        category = creature.get("category") or ""
        if category:
            lines.append(f"CATEGORY: {category}")
        env_tags = creature.get("environment_tags") or []
        if isinstance(env_tags, list) and env_tags:
            lines.append(f"ENVIRONMENT_TAGS: {', '.join([str(t) for t in env_tags if str(t).strip()])}")
        scene_use = creature.get("scene_use_summary") or ""
        if scene_use:
            lines.append(f"SCENE_USE_SUMMARY: {scene_use}")
        if creature.get("threat"):
            lines.append(f"THREAT: {creature.get('threat')}")
        if creature.get("signs"):
            lines.append(f"SIGNS: {creature.get('signs')}")
        sounds = creature.get("sounds") or []
        if isinstance(sounds, list) and sounds:
            ss = [str(s).strip() for s in sounds if str(s).strip()][:6]
            if ss:
                lines.append(f"SOUNDS: {', '.join(ss)}")

    if scene_summary:
        lines.append("")
        lines.append("RECENT SCENE SUMMARY (do not contradict):")
        lines.append(scene_summary)

    lines.append("")
    lines.append("Output rules:")
    lines.append("- Write a single RP response that continues the user's scene.")
    lines.append("- Stay grounded in the active place; do not drift.")
    lines.append("- Keep continuity with the recent scene summary.")
    lines.append("- If a creature is active, use it as pressure by default; do not force combat language unless strongly cued.")
    lines.append("- Prefer 1–2 compact paragraphs. Avoid long-form over-description.")
    lines.append("- Target roughly 400–900 characters unless the player's post strongly warrants more.")
    lines.append("- Never use first person narration.")
    lines.append("- Never use second person narration.")
    lines.append("- Never address the player as you/your outside quoted dialogue.")
    lines.append("- Remain in strict third-person narration even when a character is active.")
    return "\n".join(lines).strip()

def build_messages(channel_id: int, rp_text: str, place_id: str, char_id: str = "", creature_id: str = "", user_id: str = "") -> Tuple[Optional[List[Dict[str, str]]], str]:
    places = _index_by_id(load_places())
    chars = _index_by_id(load_characters())

    pid = place_id.strip().lower()
    if not pid or pid not in places:
        available = ", ".join(sorted(places.keys()))
        if available:
            return None, f"No active place is set. Use `!place=<id>` with `!env` (available: {available})."
        return None, "No active place is set. Use `!place=<id>` with `!env`."

    place = places[pid]
    character = None
    character_interaction_permission = ""
    if char_id:
        cid = char_id.strip().lower()
        character = chars.get(cid)
        if not character:
            available = ", ".join(sorted(chars.keys()))
            if available:
                return None, f"Unknown character id `{cid}` (available: {available})."
            return None, f"Unknown character id `{cid}`."
        character_interaction_permission = _infer_character_interaction_permission(rp_text, character)

    creature = None
    if creature_id:
        query = creature_id.strip().lower()
        creature, resolved_id = resolve_creature(query)
        if not creature:
            available = ", ".join(list_creature_ids())
            if available:
                return None, f"Unknown creature id `{query}` (available: {available})."
            return None, f"Unknown creature id `{query}`."

    state = get_state(channel_id)
    summary = str(state.get("scene_summary", "")).strip()
    if len(summary) > 600:
        summary = summary[:600]

    player_character_id = resolve_player_character(user_id) if user_id else ""
    player_character_text = load_player_character(player_character_id) if player_character_id else ""

    escalation_permission = _infer_creature_escalation_permission(rp_text, summary) if creature else ""
    system_prompt = _build_system_prompt(
        place,
        character,
        creature,
        summary,
        escalation_permission,
        character_interaction_permission,
        player_character_id or "",
        player_character_text or ""
    )
    user_prompt = f"PLAYER POST:\n{rp_text.strip()}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ], ""
