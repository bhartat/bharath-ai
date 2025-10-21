# backend/models.py (FINAL - Clean Slate)
from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    googleId: str = Field(unique=True, index=True)
    email: str = Field(unique=True)
    displayName: Optional[str] = Field(default=None)
    avatarUrl: Optional[str] = Field(default=None, max_length=512)
    oauth_access_token: Optional[str] = Field(default=None, max_length=2048)
    oauth_refresh_token: Optional[str] = Field(default=None, max_length=2048)
    oauth_token_expiry: Optional[datetime] = Field(default=None)