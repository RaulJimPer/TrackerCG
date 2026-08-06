# TrackerCG — Deployment Guide

How to install, configure, run, and use TrackerCG on your own machine.

---

## 1. Prerequisites

- **Python 3.12+** (developed/tested on 3.14).
- **Git** (to clone the repository).
- Internet access for PyPI, the Tailwind CDN, Google Fonts, and the card
  market sources.

## 2. Installation

Create and activate a virtual environment, then install the dependencies:

```powershell
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

```bash
pip install -r requirements.txt
```

For development and testing, also install:

```bash
pip install -r requirements-dev.txt   # pytest, pytest-asyncio, ruff, Playwright
```

> **No API keys are required.** All market data comes from public sources:
> Scryfall (MTG), YGOPRODeck (Yu-Gi-Oh!), and TCGGO's public card pages
> (Pokémon and Riftbound), scraped with `httpx` + BeautifulSoup.

## 3. Configuration

Copy the template and edit it:

```bash
cp .env.example .env
```

| Variable | What to set |
|----------|-------------|
| `SECRET_KEY` | Generate one: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. **Required when `DEBUG=false`.** |
| `DEBUG` | `true` during development; **must be `false` in production**. |
| `COOKIE_SECURE` | `true` when serving over HTTPS (sets the `Secure` flag on the session cookie). |
| `RATE_LIMIT_ENABLED` | Global rate-limit switch (default `true`). |
| `TRUSTED_PROXY` | Set `true` **only** behind a reverse proxy that overwrites `X-Forwarded-For`. |
| `JWT_LIFETIME_SECONDS` | Session length in seconds (default `3600`). |
| `DATABASE_URL` | SQLite URL (default `sqlite:///trackercg.db`). Only SQLite is supported. |

> `.env` is gitignored and must never be committed.

## 4. Database

- On startup the app **auto-creates the schema** if it does not exist
  (`create_db_and_tables` in the lifespan).
- For schema **changes** (migrations), run Alembic:

```bash
alembic upgrade head
```

The database file (`trackercg.db`) is created next to the project root and is
gitignored.

### Optional: seed data (local helper)

`seed_test_data.py` is a **development helper** that ships with the repo. It
seeds:

- Users `test@trackercg.dev` / `TestPass123` and `second@trackercg.dev` /
  `TestPass123`;
- 17 unique cards across MTG, Pokémon, Yu-Gi-Oh!, Riftbound;
- 30 collection items for the main user (page 1 = 20, page 2 = 10).

Run it (deterministic — re-running wipes ALL tables before reseeding):

```bash
venv\Scripts\python.exe seed_test_data.py
```

## 5. Run the application

```powershell
uvicorn src.main:app --reload
```

or, on Windows without relying on PATH:

```powershell
venv\Scripts\python.exe -m uvicorn src.main:app --reload
```

Open <http://127.0.0.1:8000> in your browser.

## 6. Using the application

1. **Create an account** — Register with an email and a password (8+ chars,
   one uppercase letter, one digit).
2. **Sign in** — your session is kept in an HTTP-only cookie.
3. **Dashboard** — see your portfolio value, total/unique cards, and your
   collection grid. Filter by game with the pills and paginate with the page
   controls.
4. **Search cards** — open the Search tab, type a card name (e.g. "blue"),
   optionally scope it to a game, and hit **Add to Collection** to save it.
   Cards already in your collection show an "In collection" badge.
5. **Manage your collection** — open a card for details; edit quantity,
   condition, language, foil, or purchase price; remove a card with
   confirmation; or **separate a copy** into its own variant (choose a
   different condition/foil/language in the edit modal).
6. **Refresh prices** — use the per-card refresh action (or wait for the
   automatic 24 h refresh) to pull fresh market values.
7. **Language** — toggle English/Spanish from the header.

## 7. Production notes

- Set `DEBUG=false`; TrackerCG will then **require** `SECRET_KEY` at startup
  (fail-fast validation).
- Serve over HTTPS and set `COOKIE_SECURE=true`.
- `Strict-Transport-Security` (HSTS) is added automatically when
  `DEBUG=false`.
- Behind a reverse proxy (nginx, Caddy, ...), set `TRUSTED_PROXY=true` so
  rate limiting keys off the real client IP, and make sure the proxy forwards
  `X-Forwarded-For`.
- The 24 h periodic refresh runs inside the app process; keep one instance per
  database file.

## 8. Troubleshooting

| Symptom | Likely fix |
|---------|-----------|
| `ModuleNotFoundError` on startup | Activate the venv / reinstall `requirements.txt`. |
| Yu-Gi-Oh! searches return nothing | Temporary YGOPRODeck outage; check your network and retry later. |
| Pokémon / Riftbound searches return nothing | Temporary TCGGO outage or layout change; check your network and retry later. The app degrades to local results. |
| Port already in use | Change the port: `uvicorn src.main:app --port 8001`. |
| `SECRET_KEY` error at startup | With `DEBUG=false` `SECRET_KEY` is mandatory; set it in `.env`. |
