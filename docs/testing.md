# TrackerCG — Testing Plan

Testing strategy, how to run the suite, and what exactly is covered.

**Status:** Backend verified. Suite: **58 pytest tests** + **Playwright smoke
test (37 checks)** — all green. Migrations `0001`→`0004` applied.

---

## 1. Strategy

| Level | Tool | Location | Scope |
|-------|------|----------|-------|
| API tests | pytest + httpx `ASGITransport` | `test/` | Routes, auth, collection, search, rate limits, security headers |
| E2E smoke test | Playwright (sync API) | `test/smoke_test.py` | Full SPA flow in a real browser |
| Manual verification | Browser + `curl`/`Invoke-WebRequest` | — | Free exploration and visual regression |

Test directory rules:

- All test files live in `test/` (repo root).
- Tests never touch the development database (`trackercg.db`); each test uses
  its own temporary SQLite file.
- `seed_test_data.py` is a data helper for development/manual testing, **not**
  a test — it is gitignored and lives at the repo root.

## 2. How to run

```powershell
# Unit/integration (API) suite
venv\Scripts\python.exe -m pytest test -q

# Linter
venv\Scripts\python.exe -m ruff check src test alembic

# E2E smoke test (needs the server up + seeded DB, see §4)
venv\Scripts\python.exe test\smoke_test.py
```

## 3. The pytest suite (58 tests)

### Harness — `test/conftest.py`

- Every test gets a **fresh temporary SQLite database** (`tmp_path`) built
  from `SQLModel.metadata.create_all`.
- The client is `httpx.AsyncClient` with `ASGITransport`, talking to the
  **real FastAPI app** (`src.main:app`) with **all middleware active** (CSP,
  rate limiting, etc.).
- `src.database` and `src.scraper` session makers are patched to the temp
  database.
- **External scraping is neutralized** (no network in tests): an autouse
  fixture monkeypatches `src.scraper._spawn_background` and
  `_run_single_flight` to no-ops.
- `limiter.reset()` runs before/after each test so rate-limit counters never
  leak across cases.
- Helpers: `register_user`, `login` (returns the session-cookie token),
  `auth_headers`, `create_card` (direct DB insert), `add_to_collection`.

### Coverage breakdown

| File | Tests | What is covered |
|------|------:|-----------------|
| `test_auth.py` | 11 | Register: success `201`, duplicate email `400`, weak/too-long/email-matching password `400`, invalid email `422`. Login: success sets the cookie, bad credentials `400`. `/users/me`: `401` unauthenticated, `200` authenticated. Logout: `204` clears the session. |
| `test_collection.py` | 23 | Auth required (`401`). Add: OK, missing card `404`, **merge by variant** (same condition/foil/language → same row), different condition → new row. List: pagination, game filter, `games` reflects the user's collection. `value`: total/cards/unique + **exact Decimal aggregation** (0.10 × 3 = "0.30"). Update/delete: OK, `404`. **Split**: to a different variant `201`, same variant `400` (unique index), quantity ≥ available `400`, missing item `404`, **merge into an existing variant**, update into an existing variant → `409`, **source purchase price preserved on split**. **Refresh-prices**: `202` with empty collection (no spawn), `202` + `games` with an MTG card (tracked background spawn). **User isolation** (Bob cannot read/delete Alice's rows). |
| `test_cards.py` | 11 | Search: auth `401`, **fresh+stale regression** (Riftbound card is never hidden), local lookup, Riftbound game OK, unknown game `422`, empty DB. Get card: auth, OK, `404`. Refresh-price: `404`, auth. |
| `test_security.py` | 3 | Security headers on `/health` and on unauthenticated API responses (CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`); login cookie with `HttpOnly` + `SameSite=strict`. |
| `test_rate_limit.py` | 2 | `429` after exceeding the `/api/cards/search` limit (30/min), presence of `x-ratelimit-*` headers, and the 429 handler reporting the exact configured limit (`x-ratelimit-limit: 30`). |
| `test_parsers.py` | 8 | Offline unit tests for the TCGGO HTML scraper: EUR price parsing (`100,00 €`, `10.729 €`, `N/A`), set-code/collector-number extraction (`VEN-168/166`, `OGN 202b`, `MEP 023`), search-card parsing for Riftbound & Pokémon, sealed-product filtering, and detail-page price precedence (US Market before EU Low). |

## 4. E2E smoke test (Playwright)

`test/smoke_test.py` drives a real Chromium browser against the running app.

### Prerequisites

1. Seed the database (reseed is idempotent):

   ```powershell
   venv\Scripts\python.exe seed_test_data.py
   ```

2. Start the server:

   ```powershell
   venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000
   ```

3. Run the smoke test (exit code `0` = all checks passed):

   ```powershell
   venv\Scripts\python.exe test\smoke_test.py
   ```

### What it verifies (37 checks)

1. Index loads with the login button.
2. **Accessibility**: modals expose `role="dialog"` + `aria-modal`, focus
   moves into the modal, and the focus trap wraps correctly.
3. **fix1** — Login errors render as a readable message inside the modal,
   without overflowing it.
4. **fix2** — Registration errors are human-readable (duplicate email, weak
   password), never raw error keys.
5. Login works; portfolio loads.
6. **fix4** — Collection pills = All + 4 games; the active game stays
   highlighted; other pills persist; "All" restores the grid.
7. **Pagination** — page 1 = 20 cards, page 2 = 10, back to page 1.
8. **fix6** — Details modal shows name and market price; `Esc` closes it.
9. **fix7** — Split button visible on a card with quantity > 1; selecting a
   different condition ("Damaged") and splitting shows the success toast.
10. **fix3** — Logout confirmation: cancel keeps the session; confirm signs
    out, resets the portfolio to `$0.00`, and shows the toast.
11. **fix5** — Search pills highlight the active game; the four enum games are
    offered as filters.
12. **fix8** — Local search results appear immediately (< 3 s), Riftbound cards
    are found locally, and the "In collection" badge renders for owned cards.
13. **i18n** — Switching to Spanish and back keeps pills and modals intact.
14. **Console hygiene** — zero JavaScript errors. Expected network noise is
    filtered (intentional 4xx from the flow and `ERR_NAME_NOT_RESOLVED` from
    unreachable CDNs); real JS errors via `pageerror` always fail the test.
