from fastapi import APIRouter
from models import Item, Page
from security import CurrentUser

router = APIRouter(prefix='/shop')


@router.get('/items', response_model=Page)
def listing(user: CurrentUser):
    return Page(items=[Item(name=user)])


@router.get('/me')
def me(user: CurrentUser):
    return {'user': user}


@router.get('/health')
def health():
    return {'ok': True}
