from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from uuid import UUID


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "viewer"


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ClubBase(BaseModel):
    name: str
    city: Optional[str] = None


class ClubCreate(ClubBase):
    pass


class ClubResponse(ClubBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class CoachBase(BaseModel):
    user_id: UUID
    club_id: Optional[UUID] = None


class CoachCreate(CoachBase):
    pass


class CoachResponse(CoachBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class GoalkeeperBase(BaseModel):
    club_id: UUID
    name: str
    birth_date: Optional[datetime] = None
    dominant_hand: Optional[str] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[int] = None


class GoalkeeperCreate(GoalkeeperBase):
    pass


class GoalkeeperResponse(GoalkeeperBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
