import os
from utils import get_config

def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)

def get_setting(key: str, default=None):
    cfg = get_config()
    return cfg.get(key, default)
