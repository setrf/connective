import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse

router = APIRouter()


def _create_token(user_id: str) -> str:
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=settings.jwt_expire_minutes
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a NextAuth token for a backend JWT. Upserts the user.

    Accepts either:
    - A JSON string with {email, name, picture} (from NextAuth server-side callback)
    - A JWT token whose claims contain email/name/picture
    """
    import json

    email = name = picture = None

    # Try parsing as JSON first (from NextAuth server-side callback)
    try:
        payload = json.loads(req.token)
        email = payload.get("email")
        name = payload.get("name")
        picture = payload.get("picture")
    except (json.JSONDecodeError, TypeError):
        pass

    # Fall back to decoding as JWT
    if not email:
        try:
            from jose import jwt as jose_jwt
            payload = jose_jwt.get_unverified_claims(req.token)
            email = payload.get("email")
            name = payload.get("name")
            picture = payload.get("picture")
        except Exception:
            pass

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token must contain email",
        )

    # Upsert user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(email=email, name=name, avatar_url=picture)
        db.add(user)
    else:
        if name:
            user.name = name
        if picture:
            user.avatar_url = picture
        user.updated_at = datetime.datetime.now(datetime.UTC)

    await db.commit()
    await db.refresh(user)

    token = _create_token(str(user.id))
    return LoginResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
    )
