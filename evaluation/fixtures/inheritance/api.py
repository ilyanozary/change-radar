from fastapi import FastAPI
from models import OrderRequest as Input, OrderResponse, DetailedResponse, AuditRequest, Health

app = FastAPI()


@app.post('/orders', response_model=OrderResponse)
def create(body: Input):
    return {'id': body.id, 'total': body.quantity * 10}


@app.get('/orders/{id}', response_model=DetailedResponse)
def read(id: str):
    return {'id': id, 'total': 10, 'note': 'local'}


@app.post('/audit')
def audit(body: AuditRequest):
    return {'id': body.id}


@app.get('/health', response_model=Health)
def health():
    return {'ok': True}
