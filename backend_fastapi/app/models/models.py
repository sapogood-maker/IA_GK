from sqlalchemy import Column, String, DateTime, UUID, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="viewer")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    coaches = relationship("Coach", back_populates="user")


class Club(Base):
    __tablename__ = "clubs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    city = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    coaches = relationship("Coach", back_populates="club")
    goalkeepers = relationship("Goalkeeper", back_populates="club")


class Coach(Base):
    __tablename__ = "coaches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    club_id = Column(UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="coaches")
    club = relationship("Club", back_populates="coaches")
    training_sessions = relationship("TrainingSession", back_populates="coach")


class Goalkeeper(Base):
    __tablename__ = "goalkeepers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    club_id = Column(UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    birth_date = Column(DateTime(timezone=True), nullable=True)
    dominant_hand = Column(String, nullable=True)
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    club = relationship("Club", back_populates="goalkeepers")
    training_sessions = relationship("TrainingSession", back_populates="goalkeeper")


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    goalkeeper_id = Column(UUID(as_uuid=True), ForeignKey("goalkeepers.id", ondelete="CASCADE"), nullable=False, index=True)
    coach_id = Column(UUID(as_uuid=True), ForeignKey("coaches.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String, nullable=False)
    session_type = Column(String, nullable=False)
    session_date = Column(DateTime(timezone=True), nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    goalkeeper = relationship("Goalkeeper", back_populates="training_sessions")
    coach = relationship("Coach", back_populates="training_sessions")
    videos = relationship("Video", back_populates="training_session")


class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    training_session_id = Column(UUID(as_uuid=True), ForeignKey("training_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    r2_key = Column(String, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    upload_status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    training_session = relationship("TrainingSession", back_populates="videos")
    processing_jobs = relationship("ProcessingJob", back_populates="video")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, default="pending")
    progress = Column(Float, nullable=True, default=0.0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    video = relationship("Video", back_populates="processing_jobs")
