from typing import Dict, Any, Optional, Tuple, List
from card_loader import load_characters, load_places, load_creatures, resolve_creature, list_creature_ids
from scene_memory import get_state

def _index_by_id(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for it in items:
        cid = str(it.get("id", "")).strip().lower()
        if cid:
            out[cid] = it
    return out

def _build_system_prompt(place: Dict[str, Any], character: Optional[Dict[str, Any]], creature: Optional[Dict[str, Any]], scene_summary: str) -> str:
    lines = []
    lines.append("You are AzerBot, a roleplay partner for Azeroth.")
    lines.append("World knowledge must come only from the provided cards and scene state.")
    lines.append("Do not contradict the active place or the scene summary.")
    lines.append("Do not introduce sudden new locations, time jumps, or major events without cues from the user's post.")
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
        lines.append("When responding, speak in-character as the ACTIVE CHARACTER.")
    else:
        lines.append("When responding, speak as the world and atmosphere of Azeroth (no random character selection).")

    if creature:
        lines.append("")
        lines.append("ACTIVE CREATURE CARD (optional pressure):")
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
    lines.append("- If a creature is active, add tension and sensory cues; do not force combat.")
    return "\n".join(lines).strip()

def build_messages(channel_id: int, rp_text: str, place_id: str, char_id: str = "", creature_id: str = "") -> Tuple[Optional[List[Dict[str, str]]], str]:
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
    if char_id:
        cid = char_id.strip().lower()
        character = chars.get(cid)
        if not character:
            available = ", ".join(sorted(chars.keys()))
            if available:
                return None, f"Unknown character id `{cid}` (available: {available})."
            return None, f"Unknown character id `{cid}`."

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

    system_prompt = _build_system_prompt(place, character, creature, summary)
    user_prompt = f"PLAYER POST:\n{rp_text.strip()}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ], ""
