from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class Session(BaseModel):
    access_token: str
    user_id: str

class Profile(BaseModel):
    user_id: str
    display_name: str
