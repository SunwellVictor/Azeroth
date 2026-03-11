import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from utils import BASE_DIR

DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
logger = logging.getLogger(__name__)

def _load_json_dir(path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not os.path.isdir(path):
        return items
    for name in sorted(os.listdir(path)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(path, name)
        try:
            with open(p, "r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, dict):
                    obj["_source_file"] = name
                items.append(obj)
        except Exception:
            pass
    return items

def _load_txt_dir(path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not os.path.isdir(path):
        return items
    for name in sorted(os.listdir(path)):
        if not name.endswith(".txt"):
            continue
        p = os.path.join(path, name)
        try:
            with open(p, "r", encoding="utf-8") as f:
                text = f.read()
            first = text.splitlines()[0].strip() if text else ""
            items.append({
                "id": os.path.splitext(name)[0].lower(),
                "name": first if first else os.path.splitext(name)[0],
                "text": text,
                "_source_file": name
            })
        except Exception:
            pass
    return items

def load_characters() -> List[Dict[str, Any]]:
    chars_path = os.path.join(DATA_DIR, "characters")
    return _load_txt_dir(chars_path) + _load_json_dir(chars_path)

def load_places() -> List[Dict[str, Any]]:
    return _load_json_dir(os.path.join(DATA_DIR, "places"))

def load_creatures() -> List[Dict[str, Any]]:
    return _load_json_dir(os.path.join(DATA_DIR, "creatures"))

def _normalize_key(value: str) -> str:
    return str(value or "").strip().lower()

_creature_index_cache: Optional[Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]] = None

def index_creatures(force_reload: bool = False) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    global _creature_index_cache
    if _creature_index_cache is not None and not force_reload:
        return _creature_index_cache

    by_id: Dict[str, Dict[str, Any]] = {}
    by_alias: Dict[str, str] = {}

    for c in load_creatures():
        if not isinstance(c, dict):
            continue
        cid = _normalize_key(c.get("id", ""))
        if not cid:
            continue

        if cid in by_id:
            existing = by_id[cid]
            existing_score = len(existing.keys())
            incoming_score = len(c.keys())
            if incoming_score > existing_score:
                by_id[cid] = c
            logger.warning(f"Duplicate creature id '{cid}' across files")
        else:
            by_id[cid] = c

    for cid, c in by_id.items():
        aliases = c.get("aliases", [])
        if not isinstance(aliases, list):
            continue
        for raw in aliases:
            a = _normalize_key(raw)
            if not a:
                continue
            if a in by_alias and by_alias[a] != cid:
                logger.warning(f"Duplicate creature alias '{a}' for ids '{by_alias[a]}' and '{cid}'")
                continue
            by_alias[a] = cid

    _creature_index_cache = (by_id, by_alias)
    return _creature_index_cache

def list_creature_ids() -> List[str]:
    by_id, _ = index_creatures()
    return sorted(by_id.keys())

def resolve_creature(creature_id_or_alias: str) -> Tuple[Optional[Dict[str, Any]], str]:
    q = _normalize_key(creature_id_or_alias)
    if not q:
        return None, ""
    by_id, by_alias = index_creatures()
    if q in by_id:
        return by_id[q], q
    if q in by_alias:
        resolved_id = by_alias[q]
        return by_id.get(resolved_id), resolved_id
    return None, ""
