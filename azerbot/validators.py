from typing import Dict, Any

def require_fields(obj: Dict[str, Any], fields) -> bool:
    for f in fields:
        if f not in obj:
            return False
    return True
