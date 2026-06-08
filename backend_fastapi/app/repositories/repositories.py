from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.models.models import User, Club, Coach, Goalkeeper, TrainingSession, Video, ProcessingJob


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, email: str, name: str, password_hash: str, role: str = "viewer") -> User:
        user = User(email=email, name=name, password_hash=password_hash, role=role)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[User]:
        result = await self.db.execute(select(User))
        return result.scalars().all()


class ClubRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str, city: str | None = None) -> Club:
        club = Club(name=name, city=city)
        self.db.add(club)
        await self.db.commit()
        await self.db.refresh(club)
        return club

    async def get_by_id(self, club_id: UUID) -> Club | None:
        result = await self.db.execute(select(Club).where(Club.id == club_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Club]:
        result = await self.db.execute(select(Club))
        return result.scalars().all()


class CoachRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: UUID, club_id: UUID | None = None) -> Coach:
        coach = Coach(user_id=user_id, club_id=club_id)
        self.db.add(coach)
        await self.db.commit()
        await self.db.refresh(coach)
        return coach

    async def get_by_id(self, coach_id: UUID) -> Coach | None:
        result = await self.db.execute(select(Coach).where(Coach.id == coach_id))
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> Coach | None:
        result = await self.db.execute(select(Coach).where(Coach.user_id == user_id))
        return result.scalar_one_or_none()


class GoalkeeperRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, club_id: UUID, name: str, birth_date=None, dominant_hand=None, height_cm=None, weight_kg=None) -> Goalkeeper:
        gk = Goalkeeper(
            club_id=club_id,
            name=name,
            birth_date=birth_date,
            dominant_hand=dominant_hand,
            height_cm=height_cm,
            weight_kg=weight_kg
        )
        self.db.add(gk)
        await self.db.commit()
        await self.db.refresh(gk)
        return gk

    async def get_by_id(self, gk_id: UUID) -> Goalkeeper | None:
        result = await self.db.execute(select(Goalkeeper).where(Goalkeeper.id == gk_id))
        return result.scalar_one_or_none()

    async def get_by_club_id(self, club_id: UUID) -> list[Goalkeeper]:
        result = await self.db.execute(select(Goalkeeper).where(Goalkeeper.club_id == club_id))
        return result.scalars().all()


class TrainingSessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, goalkeeper_id: UUID, coach_id: UUID | None, title: str, session_type: str, session_date, notes: str | None = None) -> TrainingSession:
        session = TrainingSession(
            goalkeeper_id=goalkeeper_id,
            coach_id=coach_id,
            title=title,
            session_type=session_type,
            session_date=session_date,
            notes=notes
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: UUID) -> TrainingSession | None:
        result = await self.db.execute(select(TrainingSession).where(TrainingSession.id == session_id))
        return result.scalar_one_or_none()

    async def get_by_goalkeeper_id(self, goalkeeper_id: UUID) -> list[TrainingSession]:
        result = await self.db.execute(select(TrainingSession).where(TrainingSession.goalkeeper_id == goalkeeper_id))
        return result.scalars().all()

    async def get_by_coach_id(self, coach_id: UUID) -> list[TrainingSession]:
        result = await self.db.execute(select(TrainingSession).where(TrainingSession.coach_id == coach_id))
        return result.scalars().all()

    async def get_all(self) -> list[TrainingSession]:
        result = await self.db.execute(select(TrainingSession))
        return result.scalars().all()

    async def update(self, session_id: UUID, **kwargs) -> TrainingSession | None:
        session = await self.get_by_id(session_id)
        if not session:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(session, key, value)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def delete(self, session_id: UUID) -> bool:
        session = await self.get_by_id(session_id)
        if not session:
            return False
        await self.db.delete(session)
        await self.db.commit()
        return True


class VideoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, training_session_id: UUID, filename: str, r2_key: str | None = None, duration_seconds: float | None = None, size_bytes: int | None = None, upload_status: str = "pending") -> Video:
        video = Video(
            training_session_id=training_session_id,
            filename=filename,
            r2_key=r2_key,
            duration_seconds=duration_seconds,
            size_bytes=size_bytes,
            upload_status=upload_status
        )
        self.db.add(video)
        await self.db.commit()
        await self.db.refresh(video)
        return video

    async def get_by_id(self, video_id: UUID) -> Video | None:
        result = await self.db.execute(select(Video).where(Video.id == video_id))
        return result.scalar_one_or_none()

    async def get_by_training_session_id(self, session_id: UUID) -> list[Video]:
        result = await self.db.execute(select(Video).where(Video.training_session_id == session_id))
        return result.scalars().all()

    async def get_all(self) -> list[Video]:
        result = await self.db.execute(select(Video))
        return result.scalars().all()

    async def update(self, video_id: UUID, **kwargs) -> Video | None:
        video = await self.get_by_id(video_id)
        if not video:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(video, key, value)
        await self.db.commit()
        await self.db.refresh(video)
        return video

    async def delete(self, video_id: UUID) -> bool:
        video = await self.get_by_id(video_id)
        if not video:
            return False
        await self.db.delete(video)
        await self.db.commit()
        return True


class ProcessingJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, video_id: UUID, status: str = "pending", progress: float = 0.0, error_message: str | None = None) -> ProcessingJob:
        job = ProcessingJob(
            video_id=video_id,
            status=status,
            progress=progress,
            error_message=error_message
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_by_id(self, job_id: UUID) -> ProcessingJob | None:
        result = await self.db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
        return result.scalar_one_or_none()

    async def get_by_video_id(self, video_id: UUID) -> list[ProcessingJob]:
        result = await self.db.execute(select(ProcessingJob).where(ProcessingJob.video_id == video_id))
        return result.scalars().all()

    async def get_by_status(self, status: str) -> list[ProcessingJob]:
        result = await self.db.execute(select(ProcessingJob).where(ProcessingJob.status == status))
        return result.scalars().all()

    async def get_all(self) -> list[ProcessingJob]:
        result = await self.db.execute(select(ProcessingJob))
        return result.scalars().all()

    async def update(self, job_id: UUID, **kwargs) -> ProcessingJob | None:
        job = await self.get_by_id(job_id)
        if not job:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(job, key, value)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def delete(self, job_id: UUID) -> bool:
        job = await self.get_by_id(job_id)
        if not job:
            return False
        await self.db.delete(job)
        await self.db.commit()
        return True
