"""Add R2 integration and video processing enhancements

Revision ID: 003
Revises: 002
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to videos table
    op.add_column("videos", sa.Column("original_filename", sa.String(), nullable=True))
    op.add_column("videos", sa.Column("mime_type", sa.String(), nullable=True))
    op.add_column("videos", sa.Column("file_size_bytes", sa.Integer(), nullable=True))
    op.add_column("videos", sa.Column("r2_bucket", sa.String(), nullable=True))
    op.add_column("videos", sa.Column("r2_url", sa.String(), nullable=True))
    op.add_column("videos", sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True))
    
    # Rename size_bytes to file_size_bytes for existing data
    # Note: This will be handled by the data migration
    
    # Update upload_status to use enum type
    # First, create the enum type
    op.execute("CREATE TYPE upload_status_enum AS ENUM ('PENDING', 'UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED')")
    
    # Add new columns to processing_jobs table
    op.add_column("processing_jobs", sa.Column("job_type", sa.String(), nullable=True))
    op.add_column("processing_jobs", sa.Column("worker_id", sa.String(), nullable=True))
    op.add_column("processing_jobs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    
    # Create the processing job status enum
    op.execute("CREATE TYPE processing_job_status_enum AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')")


def downgrade() -> None:
    # Remove columns from videos table
    op.drop_column("videos", "uploaded_at")
    op.drop_column("videos", "r2_url")
    op.drop_column("videos", "r2_bucket")
    op.drop_column("videos", "file_size_bytes")
    op.drop_column("videos", "mime_type")
    op.drop_column("videos", "original_filename")
    
    # Remove columns from processing_jobs table
    op.drop_column("processing_jobs", "retry_count")
    op.drop_column("processing_jobs", "worker_id")
    op.drop_column("processing_jobs", "job_type")
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS processing_job_status_enum")
    op.execute("DROP TYPE IF EXISTS upload_status_enum")
