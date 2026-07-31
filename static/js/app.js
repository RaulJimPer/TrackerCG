/* ============================================================
   TrackerCG — Frontend application (Vanilla JS)
   SPA: Dashboard (collection) + Search + Auth modals
   ============================================================ */
(() => {
  "use strict";

  /* ---------------- Constants ---------------- */

  const GAME_LABELS = {
    MTG: "Magic: The Gathering",
    POKEMON: "Pokémon",
    YUGIOH: "Yu-Gi-Oh!",
    LORCANA: "Lorcana",
    ONEPIECE: "One Piece",
    DIGIMON: "Digimon",
    FLESH_AND_BLOOD: "Flesh and Blood",
    VANGUARD: "Cardfight!! Vanguard",
    WEISS_SCHWARZ: "Weiss Schwarz",
    DBS: "Dragon Ball Super",
    FF_TCG: "Final Fantasy TCG",
    FORCE_OF_WILL: "Force of Will",
    L5R: "Legend of the Five Rings",
    BATTLE_SPIRITS: "Battle Spirits",
    GUNDAM: "Gundam TCG",
    STAR_WARS: "Star Wars Unlimited",
    KEYFORGE: "KeyForge",
    SORCERY: "Sorcery: Contested Realm",
    OTHER: "Other",
  };

  const CONDITIONS = ["Mint", "Near Mint", "Lightly Played", "Played", "Damaged"];
  const PAGE_SIZE = 20;

  /* ---------------- i18n ---------------- */

  const I18N = {
    en: {
      nav_dashboard: "Dashboard",
      nav_search: "Search",
      portfolio_value: "Total Portfolio Value",
      total_cards: "Total Cards",
      unique_cards: "Unique Cards",
      empty_title: "No cards yet",
      empty_hint: "Search and add your first card!",
      search_cards_btn: "Search cards",
      search_placeholder: "Search cards by name, set or collector number...",
      search_hint: "Searching external sources... this may take a few seconds.",
      search_no_results: "No cards found. Try a different search.",
      all_games: "All",
      login: "Sign in",
      register: "Register",
      logout: "Log out",
      login_title: "Welcome back",
      register_title: "Create your account",
      email: "Email",
      password: "Password",
      login_cta: "Sign in",
      register_cta: "Create account",
      no_account: "Don't have an account?",
      register_link: "Register",
      have_account: "Already have an account?",
      login_link: "Sign in",
      password_rule: "At least 8 characters, one uppercase letter and one digit.",
      add_title: "Add to collection",
      edit_title: "Edit item",
      quantity: "Quantity",
      condition: "Condition",
      language: "Language",
      purchase_price: "Purchase price",
      foil: "Foil",
      add_to_collection: "Add to collection",
      save: "Save changes",
      delete_title: "Remove card",
      delete_message: "This item will be removed from your collection. This cannot be undone.",
      cancel: "Cancel",
      delete_confirm: "Remove",
      market: "Market",
      refresh: "Refresh price",
      edit: "Edit",
      remove: "Remove",
      in_collection: "In collection",
      loading_search: "Searching...",
      loading_adding: "Adding...",
      toast_login_ok: "Welcome back!",
      toast_register_ok: "Account created. You can now sign in.",
      toast_logout: "You have been signed out.",
      toast_added: "Card added to your collection.",
      toast_updated: "Item updated.",
      toast_removed: "Card removed from your collection.",
      toast_price_updated: "Market price updated.",
      toast_rate_limit: "Too many requests. Please wait a moment.",
      toast_session_expired: "Your session has expired. Please sign in again.",
      toast_error: "Something went wrong. Please try again.",
      card_count: "{{count}} cards",
      game_filter: "Game",
      err_bad_credentials: "Incorrect email or password.",
      err_email_exists: "An account with this email already exists.",
      err_invalid_password: "Password must be at least 8 characters with an uppercase letter and a number.",
      err_user_active: "This account is already active.",
      err_invalid_email: "Please enter a valid email address.",
      err_bad_token: "Invalid or expired link.",
      split_btn: "Split one off",
      split_title: "Split copy",
      split_message: "Move 1 copy of this item into its own entry so it can be edited separately.",
      toast_split: "One copy separated into its own entry.",
      details_title: "Card details",
      details_updated: "Last market update: {{date}}",
      total_value: "Total value",
      logout_title: "Sign out?",
      logout_message: "You will be returned to the home screen.",
      logout_confirm: "Sign out",
      toast_split_error: "This item has only one copy and cannot be split.",
    },
    es: {
      nav_dashboard: "Colección",
      nav_search: "Buscar",
      portfolio_value: "Valor total del portafolio",
      total_cards: "Cartas totales",
      unique_cards: "Cartas únicas",
      empty_title: "Aún no tienes cartas",
      empty_hint: "¡Busca y añade tu primera carta!",
      search_cards_btn: "Buscar cartas",
      search_placeholder: "Busca cartas por nombre, edición o número de colección...",
      search_hint: "Buscando en fuentes externas... puede tardar unos segundos.",
      search_no_results: "No se encontraron cartas. Prueba con otra búsqueda.",
      all_games: "Todos",
      login: "Iniciar sesión",
      register: "Registrarse",
      logout: "Cerrar sesión",
      login_title: "Bienvenido de nuevo",
      register_title: "Crea tu cuenta",
      email: "Correo electrónico",
      password: "Contraseña",
      login_cta: "Iniciar sesión",
      register_cta: "Crear cuenta",
      no_account: "¿No tienes cuenta?",
      register_link: "Regístrate",
      have_account: "¿Ya tienes cuenta?",
      login_link: "Inicia sesión",
      password_rule: "Mínimo 8 caracteres, una mayúscula y un dígito.",
      add_title: "Añadir a la colección",
      edit_title: "Editar artículo",
      quantity: "Cantidad",
      condition: "Condición",
      language: "Idioma",
      purchase_price: "Precio de compra",
      foil: "Foil",
      add_to_collection: "Añadir a la colección",
      save: "Guardar cambios",
      delete_title: "Eliminar carta",
      delete_message: "Este artículo se eliminará de tu colección. No se puede deshacer.",
      cancel: "Cancelar",
      delete_confirm: "Eliminar",
      market: "Mercado",
      refresh: "Actualizar precio",
      edit: "Editar",
      remove: "Eliminar",
      in_collection: "En colección",
      loading_search: "Buscando...",
      loading_adding: "Añadiendo...",
      toast_login_ok: "¡Bienvenido de nuevo!",
      toast_register_ok: "Cuenta creada. Ya puedes iniciar sesión.",
      toast_logout: "Has cerrado sesión.",
      toast_added: "Carta añadida a tu colección.",
      toast_updated: "Artículo actualizado.",
      toast_removed: "Carta eliminada de tu colección.",
      toast_price_updated: "Precio de mercado actualizado.",
      toast_rate_limit: "Demasiadas peticiones. Espera un momento.",
      toast_session_expired: "Tu sesión ha expirado. Inicia sesión de nuevo.",
      toast_error: "Algo salió mal. Inténtalo de nuevo.",
      card_count: "{{count}} cartas",
      game_filter: "Juego",
      err_bad_credentials: "Correo o contraseña incorrectos.",
      err_email_exists: "Ya existe una cuenta con este correo.",
      err_invalid_password: "La contraseña debe tener al menos 8 caracteres, una mayúscula y un número.",
      err_user_active: "Esta cuenta ya está activa.",
      err_invalid_email: "Introduce un correo electrónico válido.",
      err_bad_token: "Enlace inválido o caducado.",
      split_btn: "Separar una copia",
      split_title: "Separar copia",
      split_message: "Mover 1 copia de este artículo a su propia entrada para poder editarla por separado.",
      toast_split: "Se separó una copia en su propia entrada.",
      details_title: "Detalles de la carta",
      details_updated: "Última actualización de mercado: {{date}}",
      total_value: "Valor total",
      logout_title: "¿Cerrar sesión?",
      logout_message: "Volverás a la pantalla de inicio.",
      logout_confirm: "Cerrar sesión",
      toast_split_error: "Este artículo solo tiene una copia y no se puede separar.",
    },
  };

  /* ---------------- State ---------------- */

  const defaultLang = (navigator.language || "en").startsWith("es") ? "es" : "en";

  const state = {
    user: null,
    view: "dashboard",
    lang: localStorage.getItem("trackercg_lang") || defaultLang,
    collection: { game: null, page: 1, items: [], total: 0, pages: 0, inFlight: false, games: [] },
    search: { query: "", game: null, page: 1, items: [], total: 0, pages: 0, inFlight: false, timer: null },
    addTarget: null,
    editTarget: null,
    deleteTarget: null,
  };

  /* ---------------- DOM helpers ---------------- */

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  /* ---------------- Utilities ---------------- */

  function t(key) {
    const dict = I18N[state.lang] || I18N.en;
    return dict[key] || I18N.en[key] || key;
  }

  function gameLabel(game) {
    return GAME_LABELS[game] || game || t("all_games");
  }

  function formatMoney(value) {
    const num = parseFloat(value);
    if (Number.isNaN(num)) return "$0.00";
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
  }

  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return new Intl.DateTimeFormat(state.lang === "es" ? "es-ES" : "en-US", { year: "numeric", month: "short", day: "numeric" }).format(d);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function debounce(fn, ms) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }

  /* ---------------- API wrapper ---------------- */

  const ERROR_MAP = {
    LOGIN_BAD_CREDENTIALS: "err_bad_credentials",
    REGISTER_USER_ALREADY_EXISTS: "err_email_exists",
    REGISTER_INVALID_PASSWORD: "err_invalid_password",
    REGISTER_USER_IS_ACTIVE: "err_user_active",
    REGISTER_INVALID_EMAIL: "err_invalid_email",
    UPDATE_USER_ALREADY_EXISTS: "err_email_exists",
    VERIFY_USER_BAD_TOKEN: "err_bad_token",
    FORGOT_PASSWORD_BAD_EMAIL: "err_email_exists",
    RESET_PASSWORD_BAD_TOKEN: "err_bad_token",
    RESET_PASSWORD_INVALID_PASSWORD: "err_invalid_password",
  };

  function translateError(detail) {
    if (!detail) return null;
    if (typeof detail === "string" && ERROR_MAP[detail]) return t(ERROR_MAP[detail]);
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (first && typeof first === "object" && typeof first.msg === "string") return first.msg;
    }
    return null;
  }

  async function api(path, options = {}) {
    const isRawBody = options.body instanceof FormData || options.body instanceof URLSearchParams;
    const opts = {
      method: options.method || "GET",
      credentials: "same-origin",
      headers: { ...(options.headers || {}) },
      ...options,
    };
    if (opts.body && !isRawBody && typeof opts.body === "object") {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
    let res;
    try {
      res = await fetch(path, opts);
    } catch {
      throw new ApiError(0, t("toast_error"));
    }

    if (res.status === 401) {
      const wasAuthed = state.user !== null;
      state.user = null;
      applyAuthUI();
      if (options.silent401) throw new ApiError(401, t("toast_session_expired"));
      if (wasAuthed) toast(t("toast_session_expired"), "error");
      openModal("modal-login");
      throw new ApiError(401, t("toast_session_expired"));
    }
    if (res.status === 429) {
      toast(t("toast_rate_limit"), "error");
      throw new ApiError(429, t("toast_rate_limit"));
    }

    const contentType = res.headers.get("content-type") || "";
    const data = res.status === 204 ? null : contentType.includes("application/json") ? await res.json() : await res.text();

    if (!res.ok) {
      const rawDetail = data && typeof data === "object" ? data.detail || data.message : data;
      const translated = translateError(rawDetail);
      const msg = translated || (typeof rawDetail === "string" ? rawDetail : JSON.stringify(rawDetail || ""));
      throw new ApiError(res.status, msg || t("toast_error"));
    }
    return data;
  }

  class ApiError extends Error {
    constructor(status, message) {
      super(message);
      this.status = status;
    }
  }

  /* ---------------- Toasts ---------------- */

  function toast(message, type = "info") {
    const container = $("#toast-container");
    const el = document.createElement("div");
    el.className = `toast toast-${type}`;
    const icon =
      type === "success"
        ? '<svg class="w-5 h-5 text-emerald-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>'
        : type === "error"
          ? '<svg class="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>'
          : '<svg class="w-5 h-5 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';
    el.innerHTML = `${icon}<span>${escapeHtml(message)}</span>`;
    container.appendChild(el);
    setTimeout(() => {
      el.classList.add("toast-leave");
      setTimeout(() => el.remove(), 300);
    }, 3500);
  }

  /* ---------------- Modals ---------------- */

  function openModal(id) {
    const modal = $(`#${id}`);
    if (!modal) return;
    modal.classList.add("modal-open");
    requestAnimationFrame(() => modal.classList.add("modal-visible"));
  }

  function closeModal(id) {
    const modal = $(`#${id}`);
    if (!modal) return;
    modal.classList.remove("modal-visible");
    setTimeout(() => modal.classList.remove("modal-open"), 150);
  }

  function closeAllModals() {
    $$(".modal-open").forEach((m) => {
      m.classList.remove("modal-visible");
      setTimeout(() => m.classList.remove("modal-open"), 150);
    });
  }

  function showError(containerId, msg) {
    const el = $(containerId);
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
  }

  function clearError(containerId) {
    const el = $(containerId);
    if (el) el.classList.add("hidden");
  }

  /* ---------------- Views & nav ---------------- */

  function switchView(view) {
    state.view = view;
    $$(".view").forEach((v) => (v.hidden = true));
    $(`#view-${view}`).hidden = false;
    $$(".nav-btn").forEach((btn) => btn.classList.toggle("active", btn.dataset.view === view));
    if (view === "dashboard" && state.user) loadCollection(1);
    if (view === "search" && state.user) $("#search-input").focus();
  }

  /* ---------------- Skeletons ---------------- */

  function renderSkeletons(grid, count = 8) {
    grid.innerHTML = Array.from({ length: count }, () => `
      <div class="skeleton-card animate-pulse">
        <div class="skeleton skeleton-img"></div>
        <div class="p-4 space-y-2">
          <div class="skeleton skeleton-line w-3/4"></div>
          <div class="skeleton skeleton-line w-1/2"></div>
          <div class="skeleton skeleton-line w-2/3"></div>
        </div>
      </div>`).join("");
  }

  /* ---------------- Card components ---------------- */

  function cardImageHtml(imageUrl, alt) {
    if (imageUrl) {
      return `<img class="tcg-card-image" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(alt)}" loading="lazy" onload="this.classList.add('loaded')" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" />
        <div class="tcg-card-image tcg-card-image--empty hidden" data-fallback>
          <svg class="w-12 h-12 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
        </div>`;
    }
    return `<div class="tcg-card-image tcg-card-image--empty">
      <svg class="w-12 h-12 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
    </div>`;
  }

  function collectionCardHtml(item) {
    const card = item.card;
    const quantity = item.quantity;
    const hasPurchase = item.purchase_price !== null && parseFloat(item.purchase_price) > 0;
    let pnl = null;
    if (hasPurchase) {
      const market = parseFloat(card.market_price);
      const purchase = parseFloat(item.purchase_price);
      pnl = market >= purchase ? (market - purchase) / purchase : -((purchase - market) / purchase);
    }
    const priceHtml = formatMoney(card.market_price);
    return `
    <article class="tcg-card" data-item-id="${item.id}">
      ${cardImageHtml(card.image_url, card.name)}
      <div class="p-4 flex flex-col gap-2 flex-1">
        <div class="flex items-start justify-between gap-2">
          <h3 class="font-semibold text-white leading-snug line-clamp-2">${escapeHtml(card.name)}</h3>
        </div>
        <div class="flex items-center gap-1.5 flex-wrap">
          <span class="badge-game">${escapeHtml(gameLabel(card.game))}</span>
          <span class="text-xs text-slate-500">×${quantity}</span>
          ${item.is_foil ? '<span class="text-xs px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">FOIL</span>' : ""}
        </div>
        <div class="mt-auto pt-2">
          <div class="flex items-baseline justify-between">
            <span class="price price-gain text-lg">${formatMoney(item.total_value)}</span>
            ${pnl !== null ? pnlPill(pnl) : `<span class="text-xs text-slate-500">${escapeHtml(item.condition)}</span>`}
          </div>
          <div class="flex items-center justify-between mt-1 text-xs text-slate-500">
            <span>${escapeHtml(t("market"))}: <span class="price text-slate-300" data-price data-value="${escapeHtml(card.market_price)}">${priceHtml}</span></span>
            ${hasPurchase ? `<span>${formatDate(card.last_updated)}</span>` : `<span class="text-xs text-slate-600">${escapeHtml(item.language)}</span>`}
          </div>
          <div class="flex items-center gap-1.5 mt-3">
            <button class="card-action-btn accent flex-1" data-action="refresh" title="${escapeHtml(t("refresh"))}">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            </button>
            <button class="card-action-btn flex-1" data-action="edit" title="${escapeHtml(t("edit"))}">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
            </button>
            <button class="card-action-btn danger flex-1" data-action="delete" title="${escapeHtml(t("remove"))}">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>
        </div>
      </div>
    </article>`;
  }

  function pnlPill(pnl) {
    const gain = pnl >= 0;
    const cls = gain ? "price-gain" : "price-loss";
    const arrow = gain ? "▲" : "▼";
    return `<span class="text-xs font-bold ${cls}">${arrow} ${Math.abs(pnl * 100).toFixed(1)}%</span>`;
  }

  function searchCardHtml(card, inCollection) {
    return `
    <article class="tcg-card" data-card-id="${card.id}">
      ${cardImageHtml(card.image_url, card.name)}
      <div class="p-4 flex flex-col gap-2 flex-1">
        <h3 class="font-semibold text-white leading-snug line-clamp-2">${escapeHtml(card.name)}</h3>
        <div class="flex items-center gap-1.5 flex-wrap">
          <span class="badge-game">${escapeHtml(gameLabel(card.game))}</span>
          ${inCollection ? `<span class="text-xs px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">${escapeHtml(t("in_collection"))}</span>` : ""}
        </div>
        <p class="text-xs text-slate-500 line-clamp-1">${escapeHtml(card.set_name)}${card.collector_number ? ` · #${escapeHtml(card.collector_number)}` : ""}</p>
        <div class="mt-auto pt-2 flex items-end justify-between gap-2">
          <div>
            <p class="text-xs text-slate-500">${escapeHtml(t("market"))}</p>
            <p class="price price-gain text-lg">${formatMoney(card.market_price)}</p>
          </div>
          <button class="px-4 py-2 rounded-lg text-sm font-semibold bg-amber-500 hover:bg-amber-600 text-slate-900 transition-all duration-200" data-action="add">
            ${escapeHtml(t("add_to_collection"))}
          </button>
        </div>
      </div>
    </article>`;
  }

  /* ---------------- Pagination ---------------- */

  function renderPagination(container, current, pages, onPage) {
    container.innerHTML = "";
    container.classList.toggle("hidden", pages <= 1);
    if (pages <= 1) return;

    const prevBtn = paginationBtn("‹", current > 1, () => current > 1 && onPage(current - 1));
    const nextBtn = paginationBtn("›", current < pages, () => current < pages && onPage(current + 1));
    container.appendChild(prevBtn);

    const range = pageRange(current, pages);
    for (const p of range) {
      if (p === "...") {
        const span = document.createElement("span");
        span.className = "page-ellipsis";
        span.textContent = "…";
        container.appendChild(span);
      } else {
        const btn = paginationBtn(String(p), true, () => onPage(p));
        if (p === current) btn.classList.add("active");
        container.appendChild(btn);
      }
    }
    container.appendChild(nextBtn);
  }

  function paginationBtn(label, enabled, onClick) {
    const btn = document.createElement("button");
    btn.className = "page-btn";
    btn.innerHTML = label;
    btn.disabled = !enabled;
    if (enabled) btn.addEventListener("click", onClick);
    return btn;
  }

  function pageRange(current, pages, max = 7) {
    if (pages <= max) return Array.from({ length: pages }, (_, i) => i + 1);
    if (current <= 4) return [1, 2, 3, 4, 5, "...", pages];
    if (current >= pages - 3) return [1, "...", pages - 4, pages - 3, pages - 2, pages - 1, pages];
    return [1, "...", current - 1, current, current + 1, "...", pages];
  }

  /* ---------------- Filter pills ---------------- */

  function renderFilterPills(container, games, current, onSelect) {
    container.innerHTML = "";
    const all = document.createElement("button");
    all.className = `filter-pill ${current === null ? "active" : ""}`;
    all.textContent = t("all_games");
    all.addEventListener("click", () => onSelect(null));
    container.appendChild(all);

    for (const game of games) {
      const btn = document.createElement("button");
      btn.className = `filter-pill ${current === game ? "active" : ""}`;
      btn.textContent = gameLabel(game);
      btn.addEventListener("click", () => onSelect(game));
      container.appendChild(btn);
    }
  }

  /* ---------------- Empty states ---------------- */

  function showEmpty(el) {
    el.classList.remove("hidden");
    el.classList.add("flex");
  }

  function hideEmpty(el) {
    el.classList.add("hidden");
    el.classList.remove("flex");
  }

  /* ---------------- Collection (Dashboard) ---------------- */

  async function loadPortfolio() {
    try {
      const data = await api("/api/collection/value");
      $("#portfolio-total").textContent = formatMoney(data.total_value);
      $("#portfolio-cards").textContent = data.cards_count;
      $("#portfolio-unique").textContent = data.unique_cards;
    } catch (err) {
      if (err.status !== 401) toast(err.message, "error");
    }
  }

  async function loadCollection(page = state.collection.page, game = state.collection.game) {
    if (!state.user || state.collection.inFlight) return;
    state.collection.inFlight = true;
    const grid = $("#collection-grid");
    renderSkeletons(grid, 8);
    hideEmpty($("#collection-empty"));

    const previousGame = state.collection.game;

    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (game) params.set("game", game);
      const data = await api(`/api/collection?${params}`);
      state.collection = { ...state.collection, game, page, items: data.items, total: data.total, pages: data.pages, inFlight: false };

      if (game !== previousGame) loadCollectionGames(false);
      renderCollectionGrid();
      renderPagination($("#collection-pagination"), data.page, data.pages, (p) => loadCollection(p, state.collection.game));
      loadPortfolio();
    } catch (err) {
      state.collection.inFlight = false;
      if (err.status !== 401) {
        grid.innerHTML = "";
        toast(err.message, "error");
      }
    }
  }

  async function loadCollectionGames(showEmpty = true) {
    if (!state.user) return;
    try {
      const games = await api("/api/collection/games");
      state.collection.games = games;
      renderCollectionFilters();
    } catch (err) {
      if (err.status !== 401) {
        renderCollectionFilters();
        if (showEmpty) toast(err.message, "error");
      }
    }
  }

  function renderCollectionFilters() {
    const container = $("#collection-filters");
    renderFilterPills(container, state.collection.games, state.collection.game, (g) => loadCollection(1, g));
  }

  function renderCollectionGrid() {
    const grid = $("#collection-grid");
    const empty = $("#collection-empty");
    if (state.collection.items.length === 0) {
      grid.innerHTML = "";
      showEmpty(empty);
      $("#collection-pagination").classList.add("hidden");
      return;
    }
    hideEmpty(empty);
    grid.innerHTML = state.collection.items.map(collectionCardHtml).join("");
  }

  /* ---------------- Search ---------------- */

  const debouncedSearch = debounce(() => runSearch(1), 600);

  function onSearchInput() {
    state.search.query = $("#search-input").value.trim();
    debouncedSearch();
  }

  async function runSearch(page = state.search.page) {
    if (!state.user) return;
    const query = state.search.query;
    if (!query && state.search.game === null) {
      $("#search-results").innerHTML = "";
      hideEmpty($("#search-empty"));
      $("#search-pagination").classList.add("hidden");
      $("#search-hint").classList.add("hidden");
      return;
    }
    if (state.search.inFlight) return;
    state.search.inFlight = true;

    $("#search-hint").textContent = t("search_hint");
    $("#search-hint").classList.remove("hidden");
    renderSkeletons($("#search-results"), 8);
    hideEmpty($("#search-empty"));

    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (state.search.game) params.set("game", state.search.game);
      if (query) params.set("q", query);
      const data = await api(`/api/cards/search?${params}`);
      state.search = { ...state.search, page, items: data.items, total: data.total, pages: data.pages, inFlight: false };

      const inCollectionIds = new Set(state.collection.items.map((i) => i.card_id));
      const grid = $("#search-results");
      if (data.items.length === 0) {
        grid.innerHTML = "";
        showEmpty($("#search-empty"));
      } else {
        hideEmpty($("#search-empty"));
        grid.innerHTML = data.items.map((c) => searchCardHtml(c, inCollectionIds.has(c.id))).join("");
      }
      renderPagination($("#search-pagination"), data.page, data.pages, (p) => runSearch(p));
      $("#search-hint").classList.add("hidden");
    } catch (err) {
      state.search.inFlight = false;
      if (err.status !== 401) {
        $("#search-results").innerHTML = "";
        $("#search-hint").classList.add("hidden");
        toast(err.message, "error");
      }
    }
  }

  function renderSearchFilters() {
    const container = $("#search-filters");
    const games = Object.keys(GAME_LABELS);
    renderFilterPills(container, games, state.search.game, (g) => {
      state.search.game = g;
      renderSearchFilters();
      runSearch(1);
    });
  }

  /* ---------------- Auth ---------------- */

  async function checkSession() {
    try {
      state.user = await api("/users/me", { silent401: true });
    } catch {
      state.user = null;
    }
    applyAuthUI();
    if (state.user) {
      await loadPortfolio();
      loadCollectionGames(false);
      if (state.view === "dashboard") loadCollection(1);
    }
  }

  function applyAuthUI() {
    const anon = $("#auth-anon");
    const user = $("#auth-user");
    if (state.user) {
      anon.classList.add("hidden");
      user.classList.remove("hidden");
      user.classList.add("flex");
      $("#user-email").textContent = state.user.email;
    } else {
      anon.classList.remove("hidden");
      user.classList.add("hidden");
      user.classList.remove("flex");
      $("#user-email").textContent = "";
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    clearError("#login-form-error");
    const email = $("#login-email").value.trim();
    const password = $("#login-password").value;
    if (!email || !password) return;

    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = "...";
    try {
      const body = new URLSearchParams({ username: email, password });
      await api("/auth/login", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
      state.user = await api("/users/me");
      applyAuthUI();
      closeModal("modal-login");
      $("#form-login").reset();
      toast(t("toast_login_ok"), "success");
      await loadPortfolio();
      switchView("dashboard");
      loadCollectionGames(false);
      if (state.view === "dashboard") loadCollection(1);
    } catch (err) {
      showError("#login-form-error", err.message || t("toast_error"));
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>${t("login_cta")}</span>`;
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    clearError("#register-form-error");
    const email = $("#register-email").value.trim();
    const password = $("#register-password").value;
    if (!email || !password) return;

    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = "...";
    try {
      await api("/auth/register", { method: "POST", body: { email, password } });
      closeModal("modal-register");
      $("#form-register").reset();
      $("#login-email").value = email;
      openModal("modal-login");
      toast(t("toast_register_ok"), "success");
    } catch (err) {
      showError("#register-form-error", err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>${t("register_cta")}</span>`;
    }
  }

  function handleLogout() {
    openModal("modal-logout");
  }

  async function confirmLogout() {
    const btn = $("#btn-logout-confirm");
    btn.disabled = true;
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      /* noop */
    }
    state.user = null;
    applyAuthUI();
    state.collection = { game: null, page: 1, items: [], total: 0, pages: 0, inFlight: false, games: [] };
    state.search = { query: "", game: null, page: 1, items: [], total: 0, pages: 0, inFlight: false, timer: null };
    $("#collection-grid").innerHTML = "";
    $("#search-results").innerHTML = "";
    $("#portfolio-total").textContent = "$0.00";
    $("#portfolio-cards").textContent = "0";
    $("#portfolio-unique").textContent = "0";
    closeModal("modal-logout");
    toast(t("toast_logout"), "success");
    window.scrollTo(0, 0);
  }

  /* ---------------- Add to collection ---------------- */

  function openAddModal(card) {
    state.addTarget = card;
    $("#add-card-name").textContent = card.name;
    $("#add-card-set").textContent = `${card.set_name}${card.collector_number ? ` · #${card.collector_number}` : ""}`;
    $("#add-card-price").textContent = formatMoney(card.market_price);
    const img = $("#add-card-image");
    if (card.image_url) {
      img.src = card.image_url;
      img.style.display = "";
    } else {
      img.style.display = "none";
    }
    $("#add-quantity").value = "1";
    $("#add-condition").value = "Near Mint";
    $("#add-language").value = "EN";
    $("#add-purchase").value = "";
    $("#add-foil").checked = false;
    clearError("#add-form-error");
    openModal("modal-add");
  }

  async function handleAdd(e) {
    e.preventDefault();
    if (!state.addTarget) return;
    clearError("#add-form-error");
    const body = {
      card_id: state.addTarget.id,
      quantity: parseInt($("#add-quantity").value, 10) || 1,
      condition: $("#add-condition").value,
      language: $("#add-language").value.trim().toUpperCase() || "EN",
      is_foil: $("#add-foil").checked,
    };
    const purchase = parseFloat($("#add-purchase").value);
    if (!Number.isNaN(purchase) && purchase >= 0) body.purchase_price = purchase;

    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = `<span>${t("loading_adding")}</span>`;
    try {
      await api("/api/collection", { method: "POST", body });
      closeModal("modal-add");
      toast(t("toast_added"), "success");
      if (state.view === "dashboard") loadCollection(state.collection.page);
      else loadCollection(1);
    } catch (err) {
      if (err.status !== 401) showError("#add-form-error", err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>${t("add_to_collection")}</span>`;
    }
  }

  /* ---------------- Edit item ---------------- */

  function openEditModal(item) {
    state.editTarget = item;
    $("#edit-quantity").value = item.quantity;
    $("#edit-condition").value = item.condition;
    $("#edit-language").value = item.language;
    $("#edit-purchase").value = item.purchase_price ?? "";
    $("#edit-foil").checked = item.is_foil;
    const splitBtn = $("#btn-edit-split");
    splitBtn.classList.toggle("hidden", item.quantity <= 1);
    splitBtn.disabled = item.quantity <= 1;
    clearError("#edit-form-error");
    openModal("modal-edit");
  }

  async function handleSplit() {
    if (!state.editTarget) return;
    const item = state.editTarget;
    if (item.quantity <= 1) {
      showError("#edit-form-error", t("toast_split_error"));
      return;
    }
    const btn = $("#btn-edit-split");
    btn.disabled = true;
    btn.innerHTML = `<span>${t("loading_adding")}</span>`;
    try {
      await api(`/api/collection/${item.id}/split`, {
        method: "POST",
        body: { quantity: 1, condition: item.condition, is_foil: item.is_foil, language: item.language, purchase_price: item.purchase_price },
      });
      closeModal("modal-edit");
      toast(t("toast_split"), "success");
      loadCollection(state.collection.page);
      loadCollectionGames(false);
    } catch (err) {
      if (err.status !== 401) showError("#edit-form-error", err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>${t("split_btn")}</span>`;
    }
  }

  async function handleEdit(e) {
    e.preventDefault();
    if (!state.editTarget) return;
    clearError("#edit-form-error");
    const body = {
      quantity: parseInt($("#edit-quantity").value, 10) || 1,
      condition: $("#edit-condition").value,
      language: $("#edit-language").value.trim().toUpperCase() || "EN",
      is_foil: $("#edit-foil").checked,
    };
    const purchase = parseFloat($("#edit-purchase").value);
    if (purchase >= 0 && !Number.isNaN(purchase)) body.purchase_price = purchase;
    else body.purchase_price = null;

    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = `<span>${t("loading_adding")}</span>`;
    try {
      await api(`/api/collection/${state.editTarget.id}`, { method: "PATCH", body });
      closeModal("modal-edit");
      toast(t("toast_updated"), "success");
      loadCollection(state.collection.page);
    } catch (err) {
      if (err.status !== 401) showError("#edit-form-error", err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>${t("save")}</span>`;
    }
  }

  /* ---------------- Card details ---------------- */

  function openDetailsModal(item) {
    const card = item.card;
    $("#details-name").textContent = card.name;
    $("#details-set").textContent = `${card.set_name}${card.collector_number ? ` · #${card.collector_number}` : ""}`;
    $("#details-game").textContent = gameLabel(card.game);
    const img = $("#details-image");
    if (card.image_url) {
      img.src = card.image_url;
      img.style.display = "";
      img.onerror = () => (img.style.display = "none");
    } else {
      img.style.display = "none";
    }
    $("#details-quantity").textContent = `×${item.quantity}`;
    $("#details-condition").textContent = item.condition;
    $("#details-language").textContent = item.language;
    $("#details-purchase").textContent = item.purchase_price && parseFloat(item.purchase_price) > 0 ? formatMoney(item.purchase_price) : "—";
    $("#details-market").textContent = formatMoney(card.market_price);
    $("#details-total").textContent = formatMoney(item.total_value);
    const date = formatDate(card.last_updated);
    $("#details-updated").textContent = date ? t("details_updated").replace("{{date}}", date) : "";
    openModal("modal-details");
  }

  /* ---------------- Delete item ---------------- */

  function openDeleteModal(item) {
    state.deleteTarget = item;
    openModal("modal-delete");
  }

  async function confirmDelete() {
    if (!state.deleteTarget) return;
    const id = state.deleteTarget.id;
    const btn = $("#btn-delete-confirm");
    btn.disabled = true;
    try {
      await api(`/api/collection/${id}`, { method: "DELETE" });
      closeModal("modal-delete");
      toast(t("toast_removed"), "success");
      const remaining = state.collection.total - 1;
      const lastPageOnCurrent = state.collection.items.length === 1 && state.collection.page > 1;
      loadCollection(lastPageOnCurrent ? state.collection.page - 1 : state.collection.page);
      if (remaining === 0) {
        $("#portfolio-total").textContent = "$0.00";
        $("#portfolio-cards").textContent = "0";
        $("#portfolio-unique").textContent = "0";
      }
    } catch (err) {
      if (err.status !== 401) toast(err.message, "error");
    } finally {
      state.deleteTarget = null;
      btn.disabled = false;
    }
  }

  /* ---------------- Refresh price ---------------- */

  async function handleRefreshPrice(cardId, priceEl) {
    try {
      const data = await api(`/api/cards/${cardId}/refresh-price`, { method: "POST" });
      const newPrice = parseFloat(data.market_price);
      const oldPrice = parseFloat(priceEl.dataset.value || "0");
      const card = priceEl.closest(".tcg-card");
      priceEl.textContent = formatMoney(data.market_price);
      priceEl.dataset.value = data.market_price;
      card.classList.remove("flash-up", "flash-down");
      if (!Number.isNaN(newPrice) && newPrice > oldPrice && oldPrice > 0) card.classList.add("flash-up");
      else if (!Number.isNaN(newPrice) && newPrice < oldPrice && oldPrice > 0) card.classList.add("flash-down");
      toast(t("toast_price_updated"), "success");
      loadPortfolio();
      loadCollection(state.collection.page);
    } catch (err) {
      if (err.status !== 401) toast(err.message, "error");
    }
  }

  /* ---------------- Global click delegation ---------------- */

  document.addEventListener("click", (e) => {
    const cardEl = e.target.closest(".tcg-card");
    const actionBtn = e.target.closest("[data-action]");
    if (actionBtn && cardEl) {
      const action = actionBtn.dataset.action;
      if (action === "add") {
        const id = parseInt(cardEl.dataset.cardId, 10);
        const card = state.search.items.find((c) => c.id === id);
        if (card) openAddModal(card);
      } else if (action === "refresh") {
        const id = parseInt(cardEl.dataset.itemId, 10);
        const item = state.collection.items.find((i) => i.id === id);
        if (item) handleRefreshPrice(item.card.id, cardEl.querySelector("[data-price]"));
      } else if (action === "edit") {
        const id = parseInt(cardEl.dataset.itemId, 10);
        const item = state.collection.items.find((i) => i.id === id);
        if (item) openEditModal(item);
      } else if (action === "delete") {
        const id = parseInt(cardEl.dataset.itemId, 10);
        const item = state.collection.items.find((i) => i.id === id);
        if (item) openDeleteModal(item);
      }
      return;
    }
    if (cardEl && cardEl.dataset.itemId) {
      const id = parseInt(cardEl.dataset.itemId, 10);
      const item = state.collection.items.find((i) => i.id === id);
      if (item) openDetailsModal(item);
    }
  });

  /* ---------------- i18n apply ---------------- */

  function applyI18n() {
    document.documentElement.lang = state.lang;
    $$("[data-i18n]").forEach((el) => {
      const key = el.dataset.i18n;
      if (key === "search_placeholder") el.placeholder = t(key);
      else el.textContent = t(key);
    });
    $("#lang-label").textContent = state.lang === "es" ? "EN" : "ES";
    $$(".nav-btn").forEach((btn) => (btn.textContent = t(`nav_${btn.dataset.view}`)));
    $$(".filter-pill").forEach((pill) => {
      if (pill.classList.contains("active") && pill.textContent === "") {
        pill.textContent = t("all_games");
      }
    });
  }

  function toggleLang() {
    state.lang = state.lang === "es" ? "en" : "es";
    localStorage.setItem("trackercg_lang", state.lang);
    applyI18n();
    if (state.view === "dashboard" && state.user) {
      renderCollectionFilters();
      renderCollectionGrid();
    }
    if (state.view === "search") renderSearchFilters();
  }

  /* ---------------- Init ---------------- */

  function bindEvents() {
    $("#btn-brand").addEventListener("click", () => switchView("dashboard"));

    $$(".nav-btn").forEach((btn) => {
      btn.addEventListener("click", () => switchView(btn.dataset.view));
    });

    $("#btn-empty-search").addEventListener("click", () => switchView("search"));

    $("#btn-lang").addEventListener("click", toggleLang);
    $("#lang-label").textContent = state.lang === "es" ? "EN" : "ES";

    $("#btn-login").addEventListener("click", () => openModal("modal-login"));
    $("#btn-register").addEventListener("click", () => openModal("modal-register"));
    $("#btn-goto-register").addEventListener("click", () => {
      closeModal("modal-login");
      openModal("modal-register");
    });
    $("#btn-goto-login").addEventListener("click", () => {
      closeModal("modal-register");
      openModal("modal-login");
    });
    $("#btn-logout").addEventListener("click", handleLogout);
    $("#btn-logout-cancel").addEventListener("click", () => closeModal("modal-logout"));
    $("#btn-logout-confirm").addEventListener("click", confirmLogout);

    $("#form-login").addEventListener("submit", handleLogin);
    $("#form-register").addEventListener("submit", handleRegister);
    $("#form-add").addEventListener("submit", handleAdd);
    $("#form-edit").addEventListener("submit", handleEdit);
    $("#btn-edit-split").addEventListener("click", handleSplit);

    $("#btn-delete-cancel").addEventListener("click", () => closeModal("modal-delete"));
    $("#btn-delete-confirm").addEventListener("click", confirmDelete);

    $("#btn-details-close").addEventListener("click", () => closeModal("modal-details"));

    $("#search-input").addEventListener("input", onSearchInput);
    $("#search-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        clearTimeout(state.search.timer);
        runSearch(1);
      }
    });

    $$('[id^="modal-"]').forEach((modal) => {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal(modal.id);
      });
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeAllModals();
    });
  }

  function init() {
    bindEvents();
    applyI18n();
    switchView("dashboard");
    renderSearchFilters();
    checkSession();
  }

  init();
})();
