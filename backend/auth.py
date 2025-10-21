# backend/auth.py (FINAL - Clean Slate)
import os
from datetime import datetime, timedelta, timezone
from typing import cast
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from authlib.integrations.starlette_client import OAuth
from jose import JWTError, jwt
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from database import get_session

load_dotenv()

oauth = OAuth()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise ValueError("Google OAuth credentials are not set in .env file.")
oauth.register(
    name='google', client_id=GOOGLE_CLIENT_ID, client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/gmail.modify', 'prompt': 'consent'}
)

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET: raise ValueError("JWT_SECRET is not set in .env file!")
safe_jwt_secret: str = cast(str, JWT_SECRET)
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=3)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, safe_jwt_secret, algorithm=ALGORITHM)

async def find_or_create_user(session: AsyncSession, user_info: dict, token: dict) -> User:
    google_id = user_info.get('sub')
    if not google_id: raise HTTPException(status_code=400, detail="Invalid user info from Google")
    
    statement = select(User).where(User.googleId == google_id)
    result = await session.execute(statement)
    db_user = result.scalar_one_or_none()

    expires_at = datetime.utcnow() + timedelta(seconds=token.get('expires_in', 3600))
    
    if db_user:
        db_user.displayName = user_info.get('name')
        db_user.avatarUrl = user_info.get('picture')
        db_user.oauth_access_token = token.get('access_token')
        if token.get('refresh_token'):
            db_user.oauth_refresh_token = token.get('refresh_token')
        db_user.oauth_token_expiry = expires_at
    else:
        db_user = User(
            googleId=google_id, email=user_info.get('email') or "", displayName=user_info.get('name'),
            avatarUrl=user_info.get('picture'), oauth_access_token=token.get('access_token'),
            oauth_refresh_token=token.get('refresh_token'), oauth_token_expiry=expires_at
        )
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, safe_jwt_secret, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None: raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await session.get(User, int(user_id_str))
    if user is None: raise credentials_exception
    return user

#