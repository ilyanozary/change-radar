from fastapi import APIRouter as Router, Depends as Inject, HTTPException
from .models import LoginRequest, Session, Profile
from .services import authenticate, profile
from .dependencies import current_user

router = Router(prefix='/auth')

@router.post('/login', response_model=Session)
async def login(payload: LoginRequest):
    try:
        return authenticate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail='Invalid credentials') from exc

@router.get('/me', response_model=Profile)
def me(user: str = Inject(current_user)):
    return profile(user)

@router.get('/session', response_model=Session)
def session(user: str = Inject(current_user)):
    return Session(access_token='local-demo-session', user_id=user)
