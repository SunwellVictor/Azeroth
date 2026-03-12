from typing import Dict, Any, List, Tuple

def require_fields(obj: Dict[str, Any], fields) -> bool:
    for f in fields:
        if f not in obj:
            return False
    return True

def validate_rp_tag_configuration(directives: Dict[str, Any], warnings: List[str]) -> Tuple[bool, Dict[str, Any]]:
    d = dict(directives or {})
    w = list(warnings or [])

    if any(x in w for x in ["multiple_place", "multiple_creature", "multiple_char"]):
        return False, d

    place = str(d.get("place", "")).strip().lower()
    creature = str(d.get("creature", "")).strip().lower()
    char_raw = str(d.get("char", "")).strip().lower()
    env = bool(d.get("env", False))

    if not env and (char_raw or creature):
        return False, d

    if place and "," in place:
        return False, d
    if creature and "," in creature:
        return False, d

    if char_raw:
        char_ids = [x.strip().lower() for x in char_raw.split(",") if x.strip()]
        if not char_ids or len(char_ids) > 2:
            return False, d
        d["_char_ids"] = char_ids
        d["char"] = char_ids[0]

    d["place"] = place
    d["creature"] = creature
    d["env"] = env
    return True, d
