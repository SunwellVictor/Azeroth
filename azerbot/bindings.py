import os
import json
from typing import Dict, Any
from utils import BASE_DIR

DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
BINDINGS_PATH = os.path.join(DATA_DIR, "bindings.json")

def load_bindings() -> Dict[str, Any]:
    if not os.path.exists(BINDINGS_PATH):
        return {"channels": {}}
    try:
        with open(BINDINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"channels": {}}

def resolve_place_id(channel_id: int) -> str:
    data = load_bindings()
    channels = data.get("channels", {})
    return str(channels.get(str(channel_id), "")) or ""
