"""Add training sessions, videos, and processing jobs tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goalkeeper_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coach_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("session_type", sa.String(), nullable=False),
        sa.Column("session_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["goalkeeper_id"], ["goalkeepers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["coach_id"], ["coaches.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_training_sessions_goalkeeper_id"), "training_sessions", ["goalkeeper_id"], unique=False)
    op.create_index(op.f("ix_training_sessions_coach_id"), "training_sessions", ["coach_id"], unique=False)

    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("training_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("r2_key", sa.String(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("upload_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["training_session_id"], ["training_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_videos_training_session_id"), "videos", ["training_session_id"], unique=False)

    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_processing_jobs_video_id"), "processing_jobs", ["video_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_processing_jobs_video_id"), table_name="processing_jobs")
    op.drop_table("processing_jobs")
    op.drop_index(op.f("ix_videos_training_session_id"), table_name="videos")
    op.drop_table("videos")
    op.drop_index(op.f("ix_training_sessions_coach_id"), table_name="training_sessions")
    op.drop_index(op.f("ix_training_sessions_goalkeeper_id"), table_name="training_sessions")
    op.drop_table("training_sessions")
