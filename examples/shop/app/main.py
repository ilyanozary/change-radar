from fastapi import FastAPI as API
from .routes import router
app = API()
app.include_router(router, prefix='/v1')
