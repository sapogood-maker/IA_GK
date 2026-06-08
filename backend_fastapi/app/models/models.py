from sqlalchemy import Column, String, DateTime, UUID
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


class Club(Base):
    __tablename__ = "clubs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    city = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Coach(Base):
    __tablename__ = "coaches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    club_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Goalkeeper(Base):
    __tablename__ = "goalkeepers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    club_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False)
    birth_date = Column(DateTime(timezone=True), nullable=True)
    dominant_hand = Column(String, nullable=True)
    height_cm = Column(String, nullable=True)
    weight_kg = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
