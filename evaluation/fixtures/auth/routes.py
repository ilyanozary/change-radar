from fastapi import APIRouter as R, Depends as Inject
from security import principal as user_dep

users = R(prefix='/users')


@users.get('/me')
def me(user=Inject(user_dep)):
    return {'user': user}


@users.get('/sessions')
def sessions(user=Inject(user_dep)):
    return {'sessions': [], 'user': user}


@users.get('/health')
def health():
    return {'ok': True}
