import json
import os
import random
import datetime
import re
from typing import Dict, List, Any

# File Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
GUARDRAILS_PATH = os.path.join(BASE_DIR, "guardrails.json")
DISTORTION_PATH = os.path.join(BASE_DIR, "distortion.json")
OC_REGISTRY_PATH = os.path.join(BASE_DIR, "oc_registry.json")
OC_PENDING_PATH = os.path.join(BASE_DIR, "oc_pending.json")
USAGE_STATE_PATH = os.path.join(BASE_DIR, "usage_state.json")

def load_json(path: str, default: Any = None) -> Any:
    """Safely loads a JSON file."""
    try:
        if not os.path.exists(path):
            return default if default is not None else {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return default if default is not None else {}

def save_json(path: str, data: Any) -> None:
    """Safely saves data to a JSON file."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving {path}: {e}")

def get_config() -> Dict:
    return load_json(CONFIG_PATH, {})

def get_guardrails() -> Dict:
    return load_json(GUARDRAILS_PATH, {"canon_blocklist": [], "injection_phrases": []})

def get_distortions() -> List[str]:
    return load_json(DISTORTION_PATH, [])

def get_fallback_message() -> str:
    messages = get_distortions()
    if not messages:
        return "[System Notice] Request cannot be fulfilled as written."
    return random.choice(messages)

def get_random_distortion() -> str:
    return get_fallback_message()

def load_oc_registry() -> Dict:
    return load_json(OC_REGISTRY_PATH, {})

def save_oc_registry(data: Dict) -> None:
    save_json(OC_REGISTRY_PATH, data)

def load_oc_pending() -> Dict:
    return load_json(OC_PENDING_PATH, {})

def save_oc_pending(data: Dict) -> None:
    save_json(OC_PENDING_PATH, data)

def load_usage_state() -> Dict:
    """Loads usage tracking data."""
    default_state = {
        "monthly_count": 0,
        "last_reset_month": datetime.date.today().month,
        "daily_counts": {}  # user_id -> count (optional if we want per-user daily caps later)
    }
    return load_json(USAGE_STATE_PATH, default_state)

def save_usage_state(data: Dict) -> None:
    save_json(USAGE_STATE_PATH, data)

def check_guardrails(text: str) -> bool:
    """
    Checks text against guardrails.
    Returns True if a violation is found (FAIL), False if clean (PASS).
    """
    guardrails = get_guardrails()
    text_lower = text.lower()

    # Check Injection Phrases
    for phrase in guardrails.get("injection_phrases", []):
        if phrase.lower() in text_lower:
            return True

    # 2. Regex Pattern Matching (More robust)
    for pattern in guardrails.get("regex_patterns", []):
        if re.search(pattern, text):
            return True

    # 3. Zalgo/Distorted Text Check
    if is_zalgo(text):
        return True

    # 4. Hidden/Invisible Character Check
    if has_hidden_chars(text):
        return True

    return False

def is_zalgo(text: str) -> bool:
    """
    Detects Zalgo text by checking for excessive combining characters.
    Threshold: > 0.5 combining chars per normal char on average.
    """
    combining_chars = 0
    normal_chars = 0
    
    for char in text:
        # Combining Diacritical Marks (0300–036F)
        # Combining Diacritical Marks Supplement (1DC0–1DFF)
        # Combining Diacritical Marks for Symbols (20D0–20FF)
        # Combining Half Marks (FE20–FE2F)
        code = ord(char)
        if (0x0300 <= code <= 0x036F) or \
           (0x1DC0 <= code <= 0x1DFF) or \
           (0x20D0 <= code <= 0x20FF) or \
           (0xFE20 <= code <= 0xFE2F):
            combining_chars += 1
        elif char.isalnum():
            normal_chars += 1
            
    if normal_chars == 0:
        return combining_chars > 0
        
    ratio = combining_chars / normal_chars
    return ratio > 0.5  # Lowered threshold for better detection

def get_model_chain() -> List[str]:
    """Returns the ordered list of models to try."""
    config = get_config()
    chain = config.get("model_chain", [])
    if not chain:
        # Default chain if not configured
        return [
            config.get("openrouter_model", "pygmalionai/mythalion-13b"),
            "sao10k/l3.3-euryale-70b",
            "neversleep/llama-3.1-lumimaid-8b"
        ]
    return chain

def has_hidden_chars(text: str) -> bool:
    """
    Detects invisible characters often used to bypass filters.
    """
    invisible_chars = [
        '\u200b', # Zero width space
        '\u200c', # Zero width non-joiner
        '\u200d', # Zero width joiner
        '\u2060', # Word joiner
        '\u180e', # Mongolian vowel separator
        '\ufeff', # Zero width no-break space
    ]
    
    for char in invisible_chars:
        if char in text:
            return True
    return False

def log_audit_event(user_id: int, channel_id: int, command_type: str, distortion_triggered: bool = False, token_usage: int = 0):
    """
    Logs structured audit data to a file (audit_log.jsonl).
    """
    event = {
        "timestamp": str(datetime.datetime.now()),
        "user_id": user_id,
        "channel_id": channel_id,
        "command_type": command_type,
        "distortion_triggered": distortion_triggered,
        "estimated_token_usage": token_usage
    }
    
    # We append to a JSONL file (JSON Lines) for easy appending
    log_path = os.path.join(BASE_DIR, "audit_log.jsonl")
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"Failed to write audit log: {e}")

def log_audit_event_ex(user_id: int, channel_id: int, command_type: str, details: Dict[str, Any]):
    event = {
        "timestamp": str(datetime.datetime.now()),
        "user_id": user_id,
        "channel_id": channel_id,
        "command_type": command_type,
        "details": details or {}
    }
    log_path = os.path.join(BASE_DIR, "audit_log.jsonl")
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"Failed to write audit log: {e}")
def log_error_event(user_id: int, channel_id: int, directives: Dict[str, Any], stage: str, exc: Exception):
    event = {
        "timestamp": str(datetime.datetime.now()),
        "user_id": user_id,
        "channel_id": channel_id,
        "stage": stage,
        "directives": directives,
        "exception_class": exc.__class__.__name__,
        "exception_message": str(exc)
    }
    log_path = os.path.join(BASE_DIR, "error_log.jsonl")
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"Failed to write error log: {e}")

def log_debug_event(event: Dict[str, Any]):
    payload = dict(event or {})
    payload.setdefault("timestamp", str(datetime.datetime.now()))
    payload.setdefault("event_type", "debug")
    log_path = os.path.join(BASE_DIR, "debug_log.jsonl")
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        print(f"Failed to write debug log: {e}")

def _strip_quoted_dialogue(text: str) -> str:
    s = str(text or "")
    s = re.sub(r"\"[^\"]*\"", "", s, flags=re.DOTALL)
    s = re.sub(r"“[^”]*”", "", s, flags=re.DOTALL)
    return s

def third_person_violations(text: str) -> List[str]:
    body = _strip_quoted_dialogue(text).lower()
    forbidden = [
        r"\bi\b",
        r"\bme\b",
        r"\bmy\b",
        r"\bmine\b",
        r"\bmyself\b",
        r"\bwe\b",
        r"\bus\b",
        r"\bour\b",
        r"\bours\b",
        r"\bourselves\b",
        r"\byou\b",
        r"\byour\b",
        r"\byours\b",
        r"\byourself\b",
        r"\byourselves\b",
        r"\bi['’]m\b",
        r"\bi['’]ve\b",
        r"\bi['’]d\b",
        r"\bi['’]ll\b",
        r"\bwe['’]re\b",
        r"\bwe['’]ve\b",
        r"\bwe['’]d\b",
        r"\bwe['’]ll\b",
        r"\byou['’]re\b",
        r"\byou['’]ve\b",
        r"\byou['’]d\b",
        r"\byou['’]ll\b",
    ]
    hits: List[str] = []
    for pat in forbidden:
        m = re.search(pat, body)
        if m:
            hits.append(m.group(0))
    return sorted(set(hits))

def is_strict_third_person(text: str) -> bool:
    return len(third_person_violations(text)) == 0

def split_for_discord(text: str, limit: int = 1900) -> List[str]:
    raw = str(text or "").strip()
    if not raw:
        return [""]
    if len(raw) <= limit:
        return [raw]

    chunks: List[str] = []
    remaining = raw

    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining.strip())
            break

        window = remaining[:limit + 1]

        cut = window.rfind("\n\n")
        if cut > 0:
            cut = cut + 2
        else:
            sentence_cut = -1
            for m in re.finditer(r"[.!?](?:\"|'|”|’)?(?=\s)", window):
                sentence_cut = m.end()
            if sentence_cut > 0:
                cut = sentence_cut
            else:
                ws_cut = -1
                for m in re.finditer(r"\s+", window):
                    ws_cut = m.start()
                cut = ws_cut if ws_cut > 0 else limit

        chunk_raw = remaining[:cut]
        chunk = chunk_raw.strip()
        if not chunk:
            chunk_raw = remaining[:limit]
            chunk = chunk_raw.strip()
            cut = len(chunk_raw)

        chunks.append(chunk)
        remaining = remaining[cut:].lstrip()

    safe = [c for c in chunks if c]
    if not safe:
        return [raw[:limit]]
    return safe
