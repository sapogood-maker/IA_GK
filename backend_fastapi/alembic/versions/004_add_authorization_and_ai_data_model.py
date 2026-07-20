"""Add multi-tenancy authorization and AI data model

Revision ID: 004
Revises: 003
Create Date: 2026-07-20

Adds:
- users.club_id (tenant do usuario) + constraint garantindo que so
  SYSTEM_ADMIN pode ter club_id nulo.
- Converte videos.upload_status e processing_jobs.status de enum nativo do
  Postgres para VARCHAR (mais facil de estender no futuro - ver
  SPRINT5_REPORT.md), e atualiza o vocabulario oficial de status do
  pipeline de IA.
- Tabelas vazias Analysis/Event/Metric/Artifact/Report, preparadas para o
  futuro AI Worker (ver AI_WORKER_ARCHITECTURE.md).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users.club_id (tenant) ---
    op.add_column("users", sa.Column("club_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_users_club_id"), "users", ["club_id"], unique=False)
    op.create_foreign_key(
        "fk_users_club_id_clubs", "users", "clubs", ["club_id"], ["id"], ondelete="SET NULL"
    )
    op.create_check_constraint(
        "ck_users_club_id_required_unless_admin",
        "users",
        "role = 'system_admin' OR club_id IS NOT NULL",
    )

    # --- videos.upload_status: enum nativo -> VARCHAR ---
    op.alter_column(
        "videos",
        "upload_status",
        type_=sa.String(),
        postgresql_using="upload_status::text",
        existing_nullable=False,
    )
    op.execute("DROP TYPE IF EXISTS uploadstatus")

    # --- processing_jobs.status: enum nativo -> VARCHAR, + novo vocabulario oficial ---
    op.alter_column(
        "processing_jobs",
        "status",
        type_=sa.String(),
        postgresql_using="status::text",
        existing_nullable=False,
    )
    op.execute("DROP TYPE IF EXISTS processingjobstatus")
    # Jobs que ainda estavam com o status antigo "PENDING" passam a refletir
    # o novo vocabulario oficial (QUEUED e o estado inicial equivalente).
    op.execute("UPDATE processing_jobs SET status = 'QUEUED' WHERE status = 'PENDING'")

    # --- Analysis: uma versao de analise de IA sobre um Video ---
    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="QUEUED"),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_job_id"], ["processing_jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("processing_job_id"),
        sa.UniqueConstraint("video_id", "version", name="uq_analyses_video_version"),
    )
    op.create_index(op.f("ix_analyses_video_id"), "analyses", ["video_id"], unique=False)

    # --- Event: evento tecnico detectado dentro de uma Analysis ---
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("timestamp_seconds", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_events_analysis_id"), "events", ["analysis_id"], unique=False)

    # --- Metric: metrica quantitativa de uma Analysis ---
    op.create_table(
        "metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_metrics_analysis_id"), "metrics", ["analysis_id"], unique=False)

    # --- Artifact: arquivo gerado (thumbnail, clipe, heatmap, predicoes em lote) ---
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("r2_bucket", sa.String(), nullable=True),
        sa.Column("r2_key", sa.String(), nullable=True),
        sa.Column("r2_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_artifacts_analysis_id"), "artifacts", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_artifacts_event_id"), "artifacts", ["event_id"], unique=False)

    # --- Report: relatorio agregando analises de um goleiro ao longo do tempo ---
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goalkeeper_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="QUEUED"),
        sa.Column("r2_bucket", sa.String(), nullable=True),
        sa.Column("r2_key", sa.String(), nullable=True),
        sa.Column("r2_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["goalkeeper_id"], ["goalkeepers.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_reports_goalkeeper_id"), "reports", ["goalkeeper_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reports_goalkeeper_id"), table_name="reports")
    op.drop_table("reports")

    op.drop_index(op.f("ix_artifacts_event_id"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_analysis_id"), table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index(op.f("ix_metrics_analysis_id"), table_name="metrics")
    op.drop_table("metrics")

    op.drop_index(op.f("ix_events_analysis_id"), table_name="events")
    op.drop_table("events")

    op.drop_index(op.f("ix_analyses_video_id"), table_name="analyses")
    op.drop_table("analyses")

    op.execute("CREATE TYPE processingjobstatus AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')")
    op.execute("UPDATE processing_jobs SET status = 'PENDING' WHERE status = 'QUEUED'")
    op.alter_column(
        "processing_jobs",
        "status",
        type_=postgresql.ENUM("PENDING", "RUNNING", "COMPLETED", "FAILED", name="processingjobstatus"),
        postgresql_using="status::processingjobstatus",
        existing_nullable=False,
    )

    op.execute("CREATE TYPE uploadstatus AS ENUM ('PENDING', 'UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED')")
    op.alter_column(
        "videos",
        "upload_status",
        type_=postgresql.ENUM("PENDING", "UPLOADED", "PROCESSING", "COMPLETED", "FAILED", name="uploadstatus"),
        postgresql_using="upload_status::uploadstatus",
        existing_nullable=False,
    )

    op.drop_constraint("ck_users_club_id_required_unless_admin", "users", type_="check")
    op.drop_constraint("fk_users_club_id_clubs", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_club_id"), table_name="users")
    op.drop_column("users", "club_id")
