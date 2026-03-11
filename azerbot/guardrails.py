from utils import check_guardrails

def validate_text(text: str) -> bool:
    return check_guardrails(text)
