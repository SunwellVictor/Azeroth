import datetime
from typing import Dict, Any

_state: Dict[int, Dict[str, Any]] = {}
INACTIVITY_TIMEOUT_SECONDS = None

def get_state(channel_id: int) -> Dict[str, Any]:
    existing = _state.get(channel_id)
    if existing:
        return existing
    fresh = {
        "active_place_id": "",
        "active_char_id": "",
        "active_creature_id": "",
        "scene_summary": "",
        "last_updated": ""
    }
    _state[channel_id] = fresh
    return fresh

def update_state(channel_id: int, place_id: str = "", char_id: str = "", creature_id: str = "", scene_summary: str = "", place_changed: bool = False):
    st = get_state(channel_id)
    now = datetime.datetime.now(datetime.UTC).isoformat()

    if place_id:
        st["active_place_id"] = place_id
        if place_changed and not creature_id:
            st["active_creature_id"] = ""

    if char_id is not None:
        if char_id:
            st["active_char_id"] = char_id

    if creature_id is not None:
        if creature_id:
            st["active_creature_id"] = creature_id

    if scene_summary:
        st["scene_summary"] = scene_summary

    st["last_updated"] = now
    _state[channel_id] = st

def clear_state(channel_id: int):
    _state.pop(channel_id, None)
