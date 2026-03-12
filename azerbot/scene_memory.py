import datetime
from typing import Dict, Any

_state: Dict[int, Dict[str, Any]] = {}
INACTIVITY_TIMEOUT_SECONDS = None
MAX_SUMMARY_LENGTH = 180

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

    st["active_char_id"] = ""
    st["active_creature_id"] = ""

    if place_id:
        st["active_place_id"] = place_id

    if place_changed:
        st["scene_summary"] = ""

    if scene_summary:
        summary_to_store = str(scene_summary)
        if len(summary_to_store) > MAX_SUMMARY_LENGTH:
            summary_to_store = summary_to_store[:MAX_SUMMARY_LENGTH].rsplit(" ", 1)[0]
        st["scene_summary"] = summary_to_store

    st["last_updated"] = now
    _state[channel_id] = st

def clear_state(channel_id: int):
    _state.pop(channel_id, None)
