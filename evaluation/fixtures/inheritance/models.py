from pydantic import BaseModel


class Record(BaseModel):
    id: str


class OrderRequest(Record):
    quantity: int


class OrderResponse(Record):
    total: int


class DetailedResponse(OrderResponse):
    note: str


class AuditRequest(Record):
    action: str


class Health(BaseModel):
    ok: bool
