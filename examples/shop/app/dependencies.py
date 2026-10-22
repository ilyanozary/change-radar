from .services import normalize_user

def current_user() -> str:
    return normalize_user('Demo User')
