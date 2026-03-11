import re
from typing import Dict, Any, Tuple, List

_DIRECTIVE_KEYS = ("place", "char", "creature")

def parse_trailing_directives(message: str) -> Tuple[str, Dict[str, Any], List[str]]:
    parts = message.strip().split()
    directives: Dict[str, Any] = {"place": "", "char": "", "creature": "", "env": False}
    warnings: List[str] = []

    trailing: List[str] = []
    while parts:
        token = parts[-1]
        cleaned = token.rstrip(".,!?")
        if cleaned == "!env":
            trailing.append(parts.pop())
            directives["env"] = True
            continue

        m = re.match(r"^!(place|char|creature)=(.+)$", cleaned, re.IGNORECASE)
        if m:
            trailing.append(parts.pop())
            key = m.group(1).lower()
            value = m.group(2).strip().lower()
            if directives.get(key):
                warnings.append(f"multiple_{key}")
                continue
            directives[key] = value
            continue

        break

    rp_text = " ".join(parts).strip()
    return rp_text, directives, warnings
