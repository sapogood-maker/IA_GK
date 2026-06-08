from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.models.models import User, Club, Coach, Goalkeeper


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
