# TrackerCG — Features

TrackerCG is a centralized digital portfolio for Trading Card Game (TCG)
collectors. It lets users keep a digital record of their physical card
collections and monitor the real-time financial value of those assets using
market data pulled from external sources.

This document breaks down every functional area of the application.

---

## 1. Authentication & Identity

Built on [fastapi-users](https://fastapi-users.github.io/fastapi-users/) v15,
the authentication layer provides secure registration, login, logout, and
session persistence without reinventing proven security machinery.

- **Registration** (`POST /auth/register`): creates an account with
  `email` + `password`. Rate-limited to 5 requests/minute.
- **Login** (`POST /auth/login`): issues a **JWT** stored in an **HTTP-only
  cookie** (`trackercg_session`, `SameSite=strict`). Returns `204` with the
  `Set-Cookie` header. Rate-limited to 10 requests/minute.
- **Logout** (`POST /auth/logout`): clears the session cookie.
- **Current user** (`GET /users/me`): returns the authenticated profile.
- **Password policy** (custom `validate_password`):
  - 8–128 characters;
  - at least one uppercase letter;
  - at least one digit;
  - must not match the account email.
- **Hashing**: passwords are stored with **pwdlib + Argon2** (`$argon2id$`).
- **Error handling**: credentials problems return human-readable messages
  (mapped client-side from `LOGIN_BAD_CREDENTIALS`, `REGISTER_USER_ALREADY_EXISTS`,
  `REGISTER_INVALID_PASSWORD`, etc.).

## 2. Dashboard — My Collection

After login the user lands on their private portfolio view.

- **Portfolio hero**: prominent **Total Portfolio Value** plus **Total Cards**
  and **Unique Cards** counters, computed from current market prices.
- **Collection grid**: responsive card grid (1/2/3/4 columns) showing each
  saved card with image, name, game badge, quantity, condition, and per-item
  total value.
- **Game filter pills**: filter the collection by game (MTG, Pokémon,
  Yu-Gi-Oh!, Riftbound). Pills are loaded from
  `GET /api/collection/games` and never rebuilt from a filtered page, so
  filters never "lose" games.
- **Pagination**: 20 items per page with page controls.
- **Card details modal**: read-only view with image, set, collector number,
  rarity, quantity, condition, language, market price, purchase price, total
  value, and last-updated timestamp.
- **Edit modal**: change quantity, condition, foil, language, and purchase
  price. Saving updates the row in place.
- **Remove card**: delete with an explicit confirmation modal.
- **Separate a copy (split)**: take one copy out of a grouped row. Because of
  the unique variant index, the separated copy must use a **different**
  variant (condition/foil/language) — the modal form values are used. If the
  target variant already exists, quantities merge instead of creating a
  duplicate row.
- **In-place price refresh**: refresh a single card's market price without
  reloading the whole grid (button disabled while fetching, price flashes
  green/red on change).
- **Empty state**: helpful message with a shortcut to the search view.

## 3. Global Card Search

A dedicated search tab independent of the user's collection.

- **Cache-first results**: every local match is returned immediately — fresh
  or stale — so the UI never blocks on scraping. External sources are only
  queried in the background when nothing local is fresh, and only awaited when
  there are no local matches at all.
- **Games without a scraper** (Lorcana, One Piece, Digimon, ...) remain fully
  searchable from the local catalog.
- **Game filter pills**: scope results to a single TCG; the active pill is
  highlighted.
- **Add to Collection**: one-click action that saves a searched card into the
  user's dashboard. Cards already in the collection show an **"In collection"**
  badge.
- **Search fields**: free-text query (`q`) plus structured filters
  (`name`, `set_name`, `collector_number`) and pagination.
- **Debounced input**: keystrokes trigger a search after a short quiet
  period, avoiding request floods.

## 4. Market Data & Price Automation

- **Four scrapers**, each isolated under `src/scrapers/`:

  | Game | Source | Method |
  |------|--------|--------|
  | Magic: The Gathering | Scryfall API | `httpx` (JSON) |
  | Pokémon | Pokémon TCG API (pokemontcg.io) | `httpx` (JSON, optional API key) |
  | Yu-Gi-Oh! | YGOPRODeck API | `httpx` (JSON) |
  | Riftbound | Scrydex API | `httpx` (JSON, API key + team ID) |

- **Price TTL**: cards older than 24 hours are considered stale.
- **Single-flight**: concurrent identical searches share one background
  request instead of duplicating work.
- **Background refresh**: when a query has only stale local matches, an
  external refresh is spawned in the background (never blocking the response).
- **Collection refresh** (`POST /api/collection/refresh-prices`): returns
  `202` immediately and spawns a **tracked** background refresh of stale card
  prices. It is **single-flight**: if a refresh is already running (periodic
  task or a previous request), the request reports `already_running: true`
  and no duplicate task is created. Only runs when the user's collection
  contains games with a scraper.
- **Periodic refresh**: every 24 hours the app refreshes stale card prices for
  cards whose game has a scraper (`refresh_stale_prices`, one session per card,
  1–3 s random delay between requests). The same single-flight guard prevents
  it from colliding with a user-triggered collection refresh.
- **Per-card refresh**: `POST /api/cards/{id}/refresh-price` re-fetches a
  single card's market price; failures log and return the last known price.
- **Politeness**: every external request includes a random 1–3 s delay and
  rotated `User-Agent` headers to mimic human traffic.
- **Resilience**: scraper failures are logged and degrade to local results —
  they never crash a request.

## 5. Data Model

- **Games** (`Game` enum): MTG, POKEMON, YUGIOH, RIFTBOUND.
- **Conditions** (`Condition` enum): Mint, Near Mint, Lightly Played, Played,
  Damaged.
- **Card**: catalog entry (game, name, set, collector number, rarity, image,
  `market_price` as `NUMERIC(10,2)`, `last_updated`, `game_metadata` JSON).
  Unique per `(game, external_id)` when `external_id` is not empty.
- **UserCard**: a user's collection row — `(user, card, condition, is_foil,
  language, quantity, purchase_price)`. A **unique index**
  (`uq_usercard_user_card_variant`) guarantees one row per variant, enforced
  with atomic merge/409 handling in the API.
- **Money**: `Decimal` everywhere, stored as `NUMERIC(10,2)`, serialized by
  Pydantic v2 as strings in JSON responses. Portfolio aggregation (total value)
  is summed in Python with `Decimal` — never with SQL `SUM`, whose float
  arithmetic on SQLite can drift by cents.
- **Time**: aware UTC datetimes (`UTCDateTime` TypeDecorator), serialized as
  ISO-8601 with a `Z` suffix.

## 6. Localization

The SPA ships with an English/Spanish dictionary (`I18N` in
`static/js/app.js`) and a one-click language toggle. The interface, modals,
toasts, and filter labels switch without reloading.
