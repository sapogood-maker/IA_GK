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


# Training Session Schemas
class TrainingSessionBase(BaseModel):
    goalkeeper_id: UUID
    coach_id: Optional[UUID] = None
    title: str
    session_type: str
    session_date: datetime
    notes: Optional[str] = None


class TrainingSessionCreate(TrainingSessionBase):
    pass


class TrainingSessionUpdate(BaseModel):
    title: Optional[str] = None
    session_type: Optional[str] = None
    session_date: Optional[datetime] = None
    notes: Optional[str] = None


class TrainingSessionResponse(TrainingSessionBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Video Schemas
class VideoBase(BaseModel):
    training_session_id: UUID
    filename: str
    r2_key: Optional[str] = None
    duration_seconds: Optional[float] = None
    size_bytes: Optional[int] = None
    upload_status: str = "pending"


class VideoCreate(VideoBase):
    pass


class VideoUpdate(BaseModel):
    r2_key: Optional[str] = None
    duration_seconds: Optional[float] = None
    size_bytes: Optional[int] = None
    upload_status: Optional[str] = None


class VideoResponse(VideoBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Processing Job Schemas
class ProcessingJobBase(BaseModel):
    video_id: UUID
    status: str = "pending"
    progress: Optional[float] = 0.0
    error_message: Optional[str] = None


class ProcessingJobCreate(ProcessingJobBase):
    pass


class ProcessingJobUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[float] = None
    error_message: Optional[str] = None


class ProcessingJobResponse(ProcessingJobBase):
    id: UUID
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
