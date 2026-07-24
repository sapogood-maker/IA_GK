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

Tornada IDEMPOTENTE em 2026-07-24 (ver DATABASE_SCHEMA_SYNC_REPORT.md) -
achado real de producao: o banco do Coolify foi originalmente criado via
Base.metadata.create_all() (removido de app/main.py so na Sprint 6, nunca
via Alembic), num momento em que os models ja tinham as classes
Analysis/Event/Metric/Artifact/Report mas AINDA NAO tinham users.club_id
nem a conversao de upload_status/status para VARCHAR. Rodar esta
migration do jeito original contra esse banco falhava com
DuplicateTable ao tentar recriar as tabelas de IA que ja existiam.
Cada bloco abaixo agora verifica o estado REAL do banco antes de agir -
comportamento IDENTICO a antes em qualquer banco onde nada disto ainda
existe (ex.: um ambiente novo, CI, ou dev local rodando as migrations em
ordem desde o inicio); so passa a pular o que ja estiver la. Nenhuma
mudanca em downgrade() - nao faz parte deste reparo.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def _existing_tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _existing_columns(bind, table: str) -> set[str]:
    return {col["name"] for col in sa.inspect(bind).get_columns(table)}


def _column_udt_name(bind, table: str, column: str) -> str | None:
    """Nome do tipo fisico no Postgres (ex.: "varchar", ou o nome de um
    ENUM nativo como "uploadstatus") - mais confiavel do que comparar
    objetos de tipo do SQLAlchemy entre versoes/dialetos."""
    return bind.execute(
        sa.text(
            "SELECT udt_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).scalar()


def upgrade() -> None:
    bind = op.get_bind()

    # --- users.club_id (tenant) ---
    # Os quatro objetos abaixo sao criados juntos, sempre - basta checar
    # a coluna para saber se este bloco ja rodou.
    if "club_id" not in _existing_columns(bind, "users"):
        op.add_column("users", sa.Column("club_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_index(op.f("ix_users_club_id"), "users", ["club_id"], unique=False)
        op.create_foreign_key(
            "fk_users_club_id_clubs", "users", "clubs", ["club_id"], ["id"], ondelete="SET NULL"
        )
        # NOT VALID: usuarios criados ANTES desta migration (ex.: producao
        # criada via create_all(), antes de club_id existir) podem ter
        # role != 'system_admin' e club_id NULL - violando a regra para
        # linhas historicas. NOT VALID cria a constraint e a aplica a
        # partir de agora (todo INSERT/UPDATE futuro e checado
        # normalmente), sem validar retroativamente linhas ja existentes -
        # preserva 100% dos dados, nunca exige corrigir/apagar nada aqui.
        # Atribuir um club_id real a esses usuarios legados e uma decisao
        # de negocio (qual clube?), fora do escopo de uma migration de
        # schema - ver DATABASE_SCHEMA_SYNC_REPORT.md.
        op.execute(
            "ALTER TABLE users ADD CONSTRAINT ck_users_club_id_required_unless_admin "
            "CHECK (role = 'system_admin' OR club_id IS NOT NULL) NOT VALID"
        )

    # --- videos.upload_status: enum nativo -> VARCHAR ---
    if _column_udt_name(bind, "videos", "upload_status") == "uploadstatus":
        op.alter_column(
            "videos",
            "upload_status",
            type_=sa.String(),
            postgresql_using="upload_status::text",
            existing_nullable=False,
        )
        op.execute("DROP TYPE IF EXISTS uploadstatus")

    # --- processing_jobs.status: enum nativo -> VARCHAR, + novo vocabulario oficial ---
    if _column_udt_name(bind, "processing_jobs", "status") == "processingjobstatus":
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

    existing_tables = _existing_tables(bind)

    # --- Analysis: uma versao de analise de IA sobre um Video ---
    if "analyses" not in existing_tables:
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
    if "events" not in existing_tables:
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
    if "metrics" not in existing_tables:
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
    if "artifacts" not in existing_tables:
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
    if "reports" not in existing_tables:
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
