import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_users.manager import BaseUserManager
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from . import models  # noqa: F401 - register tables in SQLModel.metadata
from .auth import auth_backend, fastapi_users, get_user_manager
from .auth_schemas import UserCreate, UserRead, UserUpdate
from .config import settings
from .database import async_engine, create_db_and_tables
from .rate_limit import limiter
from .routes.cards import router as cards_router
from .routes.collection import router as collection_router
from .scraper import close_scrapers, refresh_stale_prices

PRICE_REFRESH_INTERVAL_HOURS = 24

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

BASE_DIR = settings.base_dir
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

AUTH_LOGIN_LIMIT = "10/minute"
AUTH_REGISTER_LIMIT = "5/minute"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()

    async def _periodic_refresh() -> None:
        """Refresh stale card prices every 24h while the app runs."""
        while True:
            await asyncio.sleep(PRICE_REFRESH_INTERVAL_HOURS * 3600)
            try:
                await refresh_stale_prices()
            except Exception:
                logging.getLogger(__name__).exception("Periodic price refresh failed")

    refresh_task = asyncio.create_task(_periodic_refresh())

    try:
        yield
    finally:
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass
        await close_scrapers()
        await async_engine.dispose()


app = FastAPI(
    title="TrackerCG",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please retry later."},
    )


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

auth_router = fastapi_users.get_auth_router(auth_backend)

for route in auth_router.routes:
    if getattr(route, "path", None) == "/login":
        route.endpoint = limiter.limit(AUTH_LOGIN_LIMIT)(route.endpoint)

app.include_router(auth_router, prefix="/auth", tags=["auth"])

_original_register = None
for route in fastapi_users.get_register_router(UserRead, UserCreate).routes:
    if getattr(route, "path", None) == "/register":
        _original_register = route.endpoint
        break


@app.post("/auth/register", response_model=UserRead, status_code=201, name="register:register")
@limiter.limit(AUTH_REGISTER_LIMIT)
async def register_rate_limited(
    request: Request,
    response: Response,
    user_create: UserCreate,
    user_manager: BaseUserManager = Depends(get_user_manager),
):
    return await _original_register(request, user_create, user_manager)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

app.include_router(cards_router)
app.include_router(collection_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "TrackerCG"},
    )
