from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.models.models import User, Club, Coach, Goalkeeper, TrainingSession, Video, ProcessingJob


class BaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> object:
        instance = kwargs.pop('instance')
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def get_by_id(self, model, id: UUID) -> object | None:
        result = await self.db.execute(select(model).where(model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, model) -> list[object]:
        result = await self.db.execute(select(model))
        return result.scalars().all()


class UserRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create(self, email: str, name: str, password_hash: str, role: str = "viewer") -> User:
        user = User(email=email, name=name, password_hash=password_hash, role=role)
        return await super().create(instance=user)


class ClubRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create(self, name: str, city: str | None = None) -> Club:
        club = Club(name=name, city=city)
        return await super().create(instance=club)


class CoachRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create(self, user_id: UUID, club_id: UUID | None = None) -> Coach:
        coach = Coach(user_id=user_id, club_id=club_id)
        return await super().create(instance=coach)


class GoalkeeperRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create(self, club_id: UUID, name: str, birth_date=None, dominant_hand=None, height_cm=None, weight_kg=None) -> Goalkeeper:
        gk = Goalkeeper(
            club_id=club_id,
            name=name,
            birth_date=birth_date,
            dominant_hand=dominant_hand,
            height_cm=height_cm,
            weight_kg=weight_kg
        )
        return await super().create(instance=gk)


class TrainingSessionRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create(self, goalkeeper_id: UUID, coach_id: UUID | None, title: str, session_type: str, session_date, notes: str | None = None) -> TrainingSession:
        session = TrainingSession(
            goalkeeper_id=goalkeeper_id,
            coach_id=coach_id,
            title=title,
            session_type=session_type,
            session_date=session_date,
            notes=notes
        )
        return await super().create(instance=session)


class VideoRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create(
        self,
        training_session_id: UUID,
        filename: str,
        original_filename: str | None = None,
        mime_type: str | None = None,
        file_size_bytes: int | None = None,
        duration_seconds: float | None = None,
        r2_bucket: str | None = None,
        r2_key: str | None = None,
        r2_url: str | None = None,
        upload_status: str = "PENDING"
    ) -> Video:
        video = Video(
            training_session_id=training_session_id,
            filename=filename,
            original_filename=original_filename,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            duration_seconds=duration_seconds,
            r2_bucket=r2_bucket,
            r2_key=r2_key,
            r2_url=r2_url,
            upload_status=upload_status
        )
        return await super().create(instance=video)


class ProcessingJobRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create(
        self,
        video_id: UUID,
        job_type: str | None = None,
        worker_id: str | None = None,
        status: str = "PENDING",
        progress: float = 0.0,
        retry_count: int = 0,
        error_message: str | None = None
    ) -> ProcessingJob:
        job = ProcessingJob(
            video_id=video_id,
            job_type=job_type,
            worker_id=worker_id,
            status=status,
            progress=progress,
            retry_count=retry_count,
            error_message=error_message
        )
        return await super().create(instance=job)
