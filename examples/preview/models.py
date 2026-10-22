from pydantic import BaseModel


class Item(BaseModel):
    name: str


class Page(BaseModel):
    items: list[Item]
