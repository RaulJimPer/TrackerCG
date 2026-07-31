from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from .config import settings


def _async_database_url() -> str:
    url = settings.database_url or f"sqlite:///{settings.sqlite_path.as_posix()}"
    if url.startswith("sqlite+aiosqlite:///"):
        return url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    raise ValueError("TrackerCG only supports SQLite database URLs")


ASYNC_DATABASE_URL = _async_database_url()


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.debug,
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
