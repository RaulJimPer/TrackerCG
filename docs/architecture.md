# TrackerCG — Repository Architecture

TrackerCG is a **Python monolith**: one FastAPI application serves the JSON
API, renders the single-page frontend, and runs the scraping engine — all in
one deployable unit.

This document describes the layout of the repository **as it exists in git**.
Local-only, gitignored artifacts are called out so the tree stays accurate
for anyone cloning the project.

---

## 1. Repository tree

```
trackercg/
├── alembic/                  # Database migrations
│   ├── env.py                # Alembic environment (async engine, FK handling)
│   ├── script.py.mako        # Migration template
│   └── versions/             # 0001_initial_schema, 0002_money_numeric, 0003_usercard_unique_index
├── docs/                     # Project documentation (this folder)
│   ├── features.md
│   ├── architecture.md
│   ├── tech-stack.md
│   ├── ui-ux-design.md
│   ├── deployment.md
│   └── testing.md
├── src/                      # Backend application package
│   ├── __init__.py
│   ├── main.py               # FastAPI app factory, middleware, routers, lifespan
│   ├── config.py             # pydantic-settings — env vars, secrets, paths
│   ├── database.py           # async engine (aiosqlite), session maker, PRAGMA foreign_keys
│   ├── models.py             # SQLModel entities: User, Card, UserCard + enums + UTCDateTime
│   ├── auth.py               # fastapi-users: CookieTransport, JWTStrategy, password policy
│   ├── auth_schemas.py       # fastapi-users schemas (UserRead / UserCreate / UserUpdate)
│   ├── security.py           # SecurityHeadersMiddleware (CSP, HSTS, nosniff, ...)
│   ├── rate_limit.py         # slowapi Limiter with RATE_LIMIT_ENABLED toggle
│   ├── scraper.py            # Scraper orchestration: registry, single-flight, TTL cache, CLI
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── cards.py          # GET /api/cards/search · GET /api/cards/{id} · POST .../refresh-price
│   │   └── collection.py     # /api/collection CRUD + /games + /value + /{id}/split
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── cards.py          # CardResponse, CardSearchResult, PriceRefreshResponse
│   │   └── collection.py     # request/response models (Decimal serialized as string)
│   └── scrapers/
│       ├── __init__.py
│       ├── base.py           # ScraperBase ABC, CardData dataclass, UA rotation, random delays
│       ├── mtg.py            # Scryfall API (httpx)
│       ├── pokemon.py        # Pokémon TCG API (httpx, optional API key)
│       └── yugioh.py         # TCGplayer (Playwright — the only Playwright consumer)
├── static/
│   ├── css/style.css         # Custom styles on top of Tailwind (design tokens, components)
│   └── js/app.js             # SPA: state, i18n, API helper, rendering, modals
├── templates/
│   └── index.html            # Single-page template (Jinja2)
├── test/                     # Automated tests (see docs/testing.md)
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_collection.py
│   ├── test_cards.py
│   ├── test_security.py
│   ├── test_rate_limit.py
│   └── smoke_test.py         # Playwright E2E smoke test
├── .env.example              # Configuration template (copy to .env)
├── .gitignore
├── alembic.ini               # Alembic configuration (script_location, logging)
├── pyproject.toml            # pytest + ruff configuration
├── requirements.txt          # Runtime dependencies (pinned)
├── requirements-dev.txt      # Development/testing dependencies (pinned)
└── README.md                 # Project entry point
```

## 2. Backend layering

```
HTTP request
   → SecurityHeadersMiddleware (CSP / HSTS / nosniff)
   → SlowAPIMiddleware (rate limiting)
   → Router (routes/)                      # FastAPI endpoints, auth dependency
   → Orchestrator (scraper.py)             # search/refresh logic, single-flight, TTL
   → Scrapers (scrapers/)                  # httpx / Playwright against external sources
   → SQLModel models (models.py)           # User, Card, UserCard
   → SQLite via async engine (database.py) # aiosqlite, PRAGMA foreign_keys=ON
```

- **`src/main.py`** is the composition root: it builds the `FastAPI` app,
  registers middleware, mounts `/static`, wires the auth/cards/collection
  routers, applies rate limits to login/register/search/refresh, adds a
  `RateLimitExceeded` handler, and defines the `/health` and `/` routes.
- **Lifespan**: on startup it creates the tables if missing
  (`create_db_and_tables`), starts a 24-hour periodic stale-price refresh task,
  and on shutdown cancels that task, closes the scraper clients (including the
  shared Playwright browser), and disposes the async engine.
- **Routes never scrape directly** — they call the orchestrator
  (`search_cards`, `refresh_card_price`, `refresh_stale_prices`) which owns
  caching, concurrency, and degradation.
- **Each game's background upsert runs in its own `AsyncSession`** — sessions
  are never shared across concurrent `asyncio.gather` tasks.

## 3. Frontend architecture (vanilla JS SPA)

`static/js/app.js` is a single IIFE with no framework:

- **Constants**: `GAME_LABELS` (19 games), `CONDITIONS` (5), `PAGE_SIZE`.
- **i18n**: an `I18N` dictionary (`en`/`es`), selected from the browser locale,
  toggled at runtime, applied via `applyI18n()`.
- **State**: a `state` object holds auth, current view, collection
  (page/game/cache), search (query/game/page/timer), and modal targets.
- **Helpers**: `$`/`$$` selectors, `t()` translator, `formatMoney`,
  `escapeHtml`, `translateError` (maps API error keys to readable messages),
  and an `api()` fetch wrapper that attaches the session cookie, parses JSON,
  and raises typed errors.
- **Modals**: a reusable open/close system with `role="dialog"`,
  `aria-modal`, `aria-labelledby`, initial focus, **focus trap**
  (Tab/Shift+Tab), and background **scroll lock** (`.modal-open-body`).
- **Rendering**: pure functions build HTML strings for cards, filter pills,
  pagination, skeletons, and empty states; `loadCollection`,
  `loadCollectionGames`, `runSearch`, `renderSearchResults` refresh views with
  in-place updates (e.g., a split or price refresh re-renders only what
  changed).
- **Event wiring**: `bindEvents()` attaches all handlers once; `init()` runs
  at DOMContentLoaded.

`templates/index.html` is a single Jinja2 template that renders the header,
the dashboard/search views, all modals, the toast container, and the loading
skeletons; the JS drives everything from there. `static/css/style.css`
provides the design tokens and component styles on top of the Tailwind CDN.

## 4. Database & migrations

- **SQLite** via SQLModel + SQLAlchemy **async** (aiosqlite). `PRAGMA
  foreign_keys=ON` is set on every connection through an engine event.
- **Migrations** use Alembic (`alembic/` + `alembic.ini`):
  - `0001` — initial schema (user, card, usercard) with an idempotent
    reconcile against an existing database;
  - `0002` — money columns as `NUMERIC(10,2)` and partial unique index
    recreation;
  - `0003` — unique variant index on `usercard` with a dedupe step.
- **`alembic/env.py`** runs migrations on an **`AUTOCOMMIT`** connection and
  disables foreign keys for the migration window. This is required because
  SQLite reports `transactional_ddl=False`, and a stray open transaction would
  silently roll back the whole migration (see `docs/testing.md`).

## 5. Conventions

- **Money** is `Decimal`, stored as `NUMERIC(10,2)`, serialized by Pydantic v2
  as **strings** (never floats).
- **Time** is aware UTC everywhere (`UTCDateTime`), serialized as ISO-8601
  with a `Z` suffix.
- **Async-first**: every route and scraping function is `async def`.
- **No Node.js / NPM / bundlers**; the frontend is served as static files.
- **Playwright is confined to `src/scrapers/yugioh.py`** (shared browser,
  serialized page access through a per-loop lock).
