from .models import LoginRequest, Session, Profile

def normalize_user(username: str) -> str:
    return username.strip().lower()

def authenticate(request: LoginRequest) -> Session:
    # Deliberately local demo authentication; no real credentials or SMS.
    if request.password != 'demo-only':
        raise ValueError('Invalid demo password')
    user = normalize_user(request.username)
    return Session(access_token='local-demo-session', user_id=user)

def profile(username: str) -> Profile:
    return Profile(user_id=normalize_user(username), display_name=username)
