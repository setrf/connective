import uuid
from pydantic import BaseModel


class LoginRequest(BaseModel):
    token: str  # NextAuth JWT or ID token


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    avatar_url: str | None
