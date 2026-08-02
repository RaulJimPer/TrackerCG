# TrackerCG — Technology Stack

TrackerCG is a Python-based monolithic web application. This page documents
every technology in use and the rationale behind the choices.

---

## 1. Backend & API

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ (developed/tested on 3.14) | Application language |
| FastAPI | 0.115.0 | Async web framework: routing, validation, OpenAPI |
| Uvicorn | 0.30.0 | ASGI server (with `standard` extras: watchfiles, websockets) |
| SQLModel | 0.0.22 | ORM on top of SQLAlchemy + Pydantic models |
| SQLAlchemy | (bundled) | Async ORM core (`AsyncSession`, async engine) |
| aiosqlite | 0.22.1 | Async SQLite driver |
| Alembic | 1.18.5 | Database migrations |
| fastapi-users | 15.0.5 | Authentication: registration, login, JWT, user management |
| PyJWT | 2.12.0 (`[crypto]`) | JWT signing/verification |
| pwdlib | 0.3.0 (`[argon2,bcrypt]`) | Password hashing (Argon2) |
| email-validator | >=1.1.0,<2.4 | Email validation for registration |
| python-multipart | >=0.0.22 | Form parsing (OAuth2 password flow) |
| pydantic-settings | 2.14.2 | Typed environment configuration (`.env`) |
| httpx | 0.27.2 | Async HTTP client (scrapers) |
| slowapi | 0.1.10 | Rate limiting |

**Why these choices:**

- **FastAPI** brings native `async`/`await` — ideal for concurrent web
  scraping — and generates typed endpoints and validation for free.
- **SQLModel** keeps a single set of models for both the ORM and the Pydantic
  validation layer, reducing duplication.
- **SQLite** is a lightweight, serverless database perfectly sized for a
  local card catalog; no external DB server is required.
- **fastapi-users** provides a battle-tested authentication stack (cookie +
  JWT) instead of hand-rolled session handling.

## 2. Web Scraping & Data Extraction

| Technology | Version | Where |
|------------|---------|-------|
| httpx | 0.27.2 | Scryfall (MTG) and Pokémon TCG API (JSON) |
| BeautifulSoup4 | 4.12.3 | HTML parsing (all scrapers) |
| Playwright | 1.61.0 | Yu-Gi-Oh! (TCGplayer, JS-rendered pages) — **only** in `src/scrapers/yugioh.py` |

**Design rules:**

- All scraping logic lives under `src/scrapers/`; route handlers never scrape.
- A shared `httpx.AsyncClient` per scraper instance with rotated
  `User-Agent` headers.
- A random 1–3 s delay precedes every external request to avoid rate-limit /
  IP bans.
- Playwright uses a **module-level shared browser**, serialized page access
  through a per-event-loop lock (`_page()` async context manager), and is
  closed via `close_playwright()` on shutdown.

## 3. Frontend & User Interface

| Technology | Version | Purpose |
|------------|---------|---------|
| HTML5 + CSS3 | — | Markup and styling |
| Vanilla JavaScript | — | SPA logic (no framework, no build step) |
| Jinja2 | 3.1.4 | Server-side template for `templates/index.html` |
| Tailwind CSS | CDN | Utility-first styling (`cdn.tailwindcss.com`) |
| Inter (Google Fonts) | — | UI font stack |

**Constraints:** Node.js, NPM, and frontend bundlers (Webpack, Vite, ...) are
**strictly forbidden** — the frontend is served as static files and must stay
dependency-light.

## 4. Development & Testing

| Technology | Version | Purpose |
|------------|---------|---------|
| pytest | 8.4.2 | Test runner |
| pytest-asyncio | 1.3.0 | Async test support (`asyncio_mode = "auto"`) |
| ruff | 0.14.11 | Linter/formatter (`line-length = 100`) |
| Playwright | 1.61.0 | E2E browser smoke test (`test/smoke_test.py`) |

## 5. Security & Operations

| Component | Detail |
|-----------|--------|
| Session | JWT in HTTP-only cookie (`trackercg_session`, `SameSite=strict`) |
| CSP | Pragmatic policy allowing Tailwind CDN, Google Fonts, and `https:` images |
| Headers | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `X-XSS-Protection: 0`, HSTS (production only) |
| Rate limiting | slowapi on `/auth/login`, `/auth/register`, `/api/cards/search`, `/api/cards/{id}/refresh-price` (toggleable) |
| Config | `pydantic-settings` reading a gitignored `.env` (see `.env.example`) |

## 6. Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///trackercg.db` | Database location (SQLite only) |
| `DEBUG` | `true` | Dev mode; must be `false` in production |
| `SECRET_KEY` | auto-generated in debug | JWT signing secret (required in production) |
| `JWT_LIFETIME_SECONDS` | `3600` | Session length |
| `POKEMON_TCG_API_KEY` | empty | Optional pokemontcg.io key (recommended in production) |
| `COOKIE_SECURE` | `false` | Sets the `Secure` cookie flag (HTTPS) |
| `RATE_LIMIT_ENABLED` | `true` | Global slowapi switch |
| `TRUSTED_PROXY` | `false` | Trust `X-Forwarded-For` only behind a reverse proxy |
