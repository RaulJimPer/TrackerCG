from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from .config import settings

ASYNC_DATABASE_URL = settings.database_url.replace(
    "sqlite:///", "sqlite+aiosqlite:///"
)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)

async_session_maker = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


async def create_db_and_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_async_session():
    async with async_session_maker() as session:
        yield session
