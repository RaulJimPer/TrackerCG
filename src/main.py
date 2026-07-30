from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models  # noqa: F401 - register tables in SQLModel.metadata
from .auth import auth_backend, fastapi_users, current_user
from .auth_schemas import UserCreate, UserRead, UserUpdate
from .config import settings
from .database import async_engine, create_db_and_tables, get_async_session
from .models import Card, Game
from .scraper import refresh_card_price, search_cards

BASE_DIR = settings.base_dir
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield
    await async_engine.dispose()


app = FastAPI(
    title="TrackerCG",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "TrackerCG"},
    )


@app.get("/api/cards/search")
async def api_search_cards(
    game: Game,
    q: str,
    db: AsyncSession = Depends(get_async_session),
):
    cards = await search_cards(db, game, q)
    return cards


@app.post("/api/cards/{card_id}/refresh-price")
async def api_refresh_price(
    card_id: int,
    db: AsyncSession = Depends(get_async_session),
    user: models.User = Depends(current_user),
):
    stmt = select(models.Card).where(models.Card.id == card_id)
    result = await db.execute(stmt)
    card = result.scalar_one_or_none()
    if card is None:
        return {"error": "Card not found"}, 404
    price = await refresh_card_price(db, card)
    return {"card_id": card_id, "market_price": price}
