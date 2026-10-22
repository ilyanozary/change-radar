from fastapi import APIRouter as Router
from routes import users

api = Router(prefix='/api')
api.include_router(users, prefix='/accounts')
