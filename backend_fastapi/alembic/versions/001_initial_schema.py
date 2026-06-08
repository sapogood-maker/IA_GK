"""create initial tables

Revision ID: 001
Revises:
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "clubs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "coaches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("club_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_coaches_user_id"), "coaches", ["user_id"], unique=False)
    op.create_index(op.f("ix_coaches_club_id"), "coaches", ["club_id"], unique=False)

    op.create_table(
        "goalkeepers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("club_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("birth_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dominant_hand", sa.String(), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_goalkeepers_club_id"), "goalkeepers", ["club_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_goalkeepers_club_id"), table_name="goalkeepers")
    op.drop_table("goalkeepers")
    op.drop_index(op.f("ix_coaches_club_id"), table_name="coaches")
    op.drop_index(op.f("ix_coaches_user_id"), table_name="coaches")
    op.drop_table("coaches")
    op.drop_table("clubs")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
