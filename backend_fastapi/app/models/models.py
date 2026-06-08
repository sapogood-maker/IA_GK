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
