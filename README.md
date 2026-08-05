# TrackerCG

A fullstack web application for managing personal Trading Card Game (TCG)
collections — currently **Magic: The Gathering, Pokémon, Yu-Gi-Oh!, and
Riftbound**. TrackerCG automatically pulls real-time market values from
external sources and computes the total value of your inventory through a
clean, dark-themed interface.

> **Documentation is organized in [`docs/`](docs/)** — this README is the entry
> point; each topic has a dedicated page with full detail.

## Highlights

- **Secure accounts** — registration, login, and sessions via
  [fastapi-users](https://fastapi-users.github.io/fastapi-users/) with JWT in
  an HTTP-only cookie, Argon2 password hashing, and a strict password policy.
- **Portfolio dashboard** — total value hero, responsive card grid, per-game
  filter pills, pagination, card details, and in-place editing.
- **Global card search** — cache-first local results returned immediately,
  with background scraping from Scryfall (MTG), TCGGO (Pokémon and Riftbound),
  and YGOPRODeck (Yu-Gi-Oh!) — all from public sources, no API keys.
- **Automated valuation** — 24 h price TTL, single-flight refreshes, a
  periodic refresh task, and per-card refresh — all priced with exact
  `Decimal` arithmetic.
- **Accessible SPA** — vanilla JavaScript, ES/EN localization, keyboard
  navigation, focus-trapped modals, and zero build tooling.

## Quickstart

```powershell
# 1. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1          # Windows
# source venv/bin/activate           # macOS / Linux

# 2. Install dependencies (+ dev/testing extras)
pip install -r requirements.txt
pip install -r requirements-dev.txt  # optional: dev/testing (Playwright smoke test)

# 3. Configure (optional but recommended)
#    copy .env.example to .env and adjust SECRET_KEY / DEBUG / etc.

# 4. Apply migrations (the schema also auto-creates on first startup)
alembic upgrade head

# 5. Run
uvicorn src.main:app --reload
```

Then open <http://127.0.0.1:8000>. Full setup, configuration, and usage
details are in the **[Deployment Guide](docs/deployment.md)**.

## Documentation

| Page | Contents |
|------|----------|
| [Features](docs/features.md) | Authentication, dashboard, search, price automation, data model, i18n |
| [Architecture](docs/architecture.md) | Repository tree, backend layering, frontend SPA, migrations, conventions |
| [Tech Stack](docs/tech-stack.md) | Every technology, version, and the rationale behind it |
| [UI/UX Design](docs/ui-ux-design.md) | Palette, typography, components, states, accessibility |
| [Deployment](docs/deployment.md) | Install, configure, run, use, and production notes |
| [Testing](docs/testing.md) | How to run the tests and what the suite covers |

## Testing at a glance

- **58 pytest tests** (`test/`) — auth, collection CRUD/merge/split,
  search, security headers, rate limits — each on a fresh temporary database
  with external scraping neutralized.
- **Playwright smoke test** (`test/smoke_test.py`) — 37 end-to-end checks of
  the real UI (fixes, pagination, accessibility, i18n, console hygiene).

```powershell
venv\Scripts\python.exe -m pytest test -q
venv\Scripts\python.exe -m ruff check src test alembic
venv\Scripts\python.exe test\smoke_test.py   # requires the server on :8000
```

See the **[Testing Plan](docs/testing.md)** for details.

## Tech stack (summary)

- **Backend:** Python · FastAPI · SQLModel/SQLAlchemy (async) · SQLite
  (aiosqlite) · Alembic · fastapi-users · pwdlib/Argon2 · slowapi · Uvicorn
- **Scraping:** httpx · BeautifulSoup4 · Scryfall · YGOPRODeck · TCGGO (HTML)
- **Frontend:** HTML5 · CSS3 · Vanilla JS · Jinja2 · Tailwind CSS (CDN) · Inter
- **Dev/QA:** pytest · pytest-asyncio · ruff · Playwright (smoke test only)

## License

This project is licensed under the **PolyForm Noncommercial License 1.0.0**.
You are free to use, modify, and distribute this software for personal, educational, and non-commercial purposes. Commercial use or monetization of this project or its variants is strictly prohibited. See the [LICENSE](LICENSE) file for details.

## Warning notice
> **Status: in development.** TrackerCG is an active work-in-progress and
> supports **four** TCGs with automated market-data scraping for now: Magic:
> The Gathering (Scryfall), Pokémon (TCGGO), Yu-Gi-Oh! (YGOPRODeck),
> and Riftbound (TCGGO). Expanding to more games is on the
> roadmap; each
> new game requires a dedicated scraper under `src/scrapers/` plus a migration
> to extend the `Game` enum. Features and behavior may change at any time.