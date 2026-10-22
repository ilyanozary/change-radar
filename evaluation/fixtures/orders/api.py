from fastapi import FastAPI
from consumers import checkout

app = FastAPI()


@app.post('/quote')
def quote():
    return checkout()


@app.get('/health')
def health():
    return {'ok': True}
