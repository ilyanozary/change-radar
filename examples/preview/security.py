from typing import Annotated
from fastapi import Depends as Need


def read_token() -> str:
    return 'offline-demo-user'


def current_user(token: str = Need(read_token)) -> str:
    return token


CurrentUser = Annotated[str, Need(dependency=current_user)]
