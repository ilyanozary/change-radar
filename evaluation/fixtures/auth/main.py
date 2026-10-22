from fastapi import FastAPI as API
from routers import api

app = API()
app.include_router(api, prefix='/v2')
