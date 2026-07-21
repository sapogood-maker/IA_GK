from sqlalchemy import Column, String, DateTime, UUID, Integer, Float, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
from enum import Enum
from app.db.base import Base


class UserRole(str, Enum):
    """Papel do usuario humano no sistema. Nao usado pela autenticacao do
    futuro AI Worker (Service Account/API Key separado - ver AI_WORKER_ARCHITECTURE.md)."""
    SYSTEM_ADMIN = "system_admin"
    CLUBE = "clube"
    TREINADOR = "treinador"
    ANALISTA = "analista"


class UploadStatus(str, Enum):
    """Status do arquivo de video em si (upload para o R2), nao do
    pipeline de IA (ver ProcessingJobStatus)."""
    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingJobStatus(str, Enum):
    """Estados oficiais do pipeline de processamento de IA. Usados por
    ProcessingJob e Analysis, e futuramente por Backend/Frontend/AI Worker/
    Telegram (ver AI_WORKER_ARCHITECTURE.md e SPRINT5_REPORT.md)."""
    QUEUED = "QUEUED"
    DOWNLOADING = "DOWNLOADING"
    PREPROCESSING = "PREPROCESSING"
    INFERENCE = "INFERENCE"
    POSTPROCESSING = "POSTPROCESSING"
    GENERATING_REPORT = "GENERATING_REPORT"
    UPLOADING_RESULTS = "UPLOADING_RESULTS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role = 'system_admin' OR club_id IS NOT NULL",
            name="ck_users_club_id_required_unless_admin",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    # unique=True ja cria um indice implicito; nao adicionar index=True aqui
    # (gerava um segundo indice redundante sobre a mesma coluna - ver
    # migration 005 e SPRINT6_REPORT.md).
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default=UserRole.TREINADOR.value)
    # Tenant do usuario. Nulo somente para SYSTEM_ADMIN (acesso a todos os
    # clubes). Todo outro papel enxerga exclusivamente os dados deste clube.
    club_id = Column(UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    coaches = relationship("Coach", back_populates="user")
    club = relationship("Club", foreign_keys=[club_id])


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
    original_filename = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    r2_bucket = Column(String, nullable=True)
    r2_key = Column(String, nullable=True)
    r2_url = Column(String, nullable=True)
    # String simples (nao enum nativo do Postgres) - trocar/adicionar valores
    # no futuro nao exige migration de tipo, so validacao na aplicacao.
    upload_status = Column(String, nullable=False, default=UploadStatus.PENDING.value)
    uploaded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    training_session = relationship("TrainingSession", back_populates="videos")
    processing_jobs = relationship("ProcessingJob", back_populates="video")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String, nullable=True)
    worker_id = Column(String, nullable=True)
    # String simples (nao enum nativo do Postgres) - ver ProcessingJobStatus.
    status = Column(String, nullable=False, default=ProcessingJobStatus.QUEUED.value)
    progress = Column(Float, nullable=True, default=0.0)
    retry_count = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    video = relationship("Video", back_populates="processing_jobs")
    analysis = relationship("Analysis", back_populates="processing_job", uselist=False)


class Analysis(Base):
    """Uma versao de analise de IA sobre um Video. Nunca e sobrescrita: um
    novo processamento do mesmo video cria uma nova linha com version+1,
    preservando o historico completo (v1, v2, v3, ...).

    Tabela criada vazia nesta sprint - sera populada pelo futuro AI Worker,
    exclusivamente via API do backend (nunca escrita direta no banco pelo
    worker - ver AI_WORKER_ARCHITECTURE.md, secao 12).
    """
    __tablename__ = "analyses"
    __table_args__ = (
        UniqueConstraint("video_id", "version", name="uq_analyses_video_version"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey("processing_jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    version = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default=ProcessingJobStatus.QUEUED.value)
    # Versao/identificador do modelo de IA que gerou esta analise (ex.:
    # "yolov8n-gk-v1"). Permite trocar de modelo sem afetar analises antigas
    # (ver AI_WORKER_ARCHITECTURE.md, secao 10).
    model_version = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    video = relationship("Video")
    processing_job = relationship("ProcessingJob", back_populates="analysis")
    events = relationship("Event", back_populates="analysis", cascade="all, delete-orphan")
    metrics = relationship("Metric", back_populates="analysis", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="analysis", cascade="all, delete-orphan")


class Event(Base):
    """Evento tecnico detectado dentro de uma Analysis (ex.: defesa, saida,
    reposicao). Tabela criada vazia nesta sprint."""
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    timestamp_seconds = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    # Campo flexivel (bbox, track_id, etc.) para nao exigir migration de
    # schema a cada novo tipo de metadado que o pipeline de IA vier a gerar.
    event_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    analysis = relationship("Analysis", back_populates="events")
    artifacts = relationship("Artifact", back_populates="event")


class Metric(Base):
    """Metrica quantitativa de uma Analysis (ex.: tempo de reacao medio).
    Formato nome/valor/unidade generico para suportar metricas futuras sem
    alterar o schema. Tabela criada vazia nesta sprint."""
    __tablename__ = "metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    analysis = relationship("Analysis", back_populates="metrics")


class Artifact(Base):
    """Arquivo gerado pela analise (thumbnail, clipe, heatmap) ou lote de
    predicoes brutas por frame, armazenado no R2 (nunca como linhas
    individuais no Postgres - ver AI_WORKER_ARCHITECTURE.md, secao 2).
    Pode pertencer a analise inteira (event_id nulo) ou a um evento
    especifico (ex.: o clipe daquela defesa). Tabela criada vazia nesta
    sprint."""
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True)
    artifact_type = Column(String, nullable=False)
    r2_bucket = Column(String, nullable=True)
    r2_key = Column(String, nullable=True)
    r2_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    analysis = relationship("Analysis", back_populates="artifacts")
    event = relationship("Event", back_populates="artifacts")


class Report(Base):
    """Relatorio agregando uma ou mais analises de um goleiro ao longo do
    tempo (ex.: evolucao mensal). Tabela criada vazia nesta sprint."""
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    goalkeeper_id = Column(UUID(as_uuid=True), ForeignKey("goalkeepers.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default=ProcessingJobStatus.QUEUED.value)
    r2_bucket = Column(String, nullable=True)
    r2_key = Column(String, nullable=True)
    r2_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    goalkeeper = relationship("Goalkeeper")
