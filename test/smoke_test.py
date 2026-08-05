"""Playwright E2E smoke test for the TrackerCG SPA.

Verifies the 8 UX fixes from manual testing, pagination, language switching
and a clean browser console, from the perspective of the real UI.

Prerequisites (see test_planning.md):
  - Server running at http://127.0.0.1:8000
  - trackercg.db seeded with test@trackercg.dev / TestPass123 (30 collection
    items for the main user). Reseed with: venv\\Scripts\\python.exe seed_test_data.py

Run:
    venv\\Scripts\\python.exe test\\smoke_test.py

Exit code 0 = all checks passed; non-zero otherwise.
"""
from __future__ import annotations

import re
import sys
import time

from playwright.sync_api import Page, sync_playwright

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "test@trackercg.dev"
PASSWORD = "TestPass123"

failures: list[str] = []
console_errors: list[str] = []


def check(name: str, cond: bool, extra: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    suffix = f" — {extra}" if extra else ""
    print(f"[{status}] {name}{suffix}")
    if not cond:
        failures.append(name)


def open_modal(page: Page, selector: str) -> None:
    page.wait_for_selector(f"{selector}.modal-open", timeout=10000)


def fill_and_submit(page: Page, email_sel: str, password_sel: str, form_sel: str, email: str, password: str) -> None:
    page.fill(email_sel, email)
    page.fill(password_sel, password)
    page.click(f"{form_sel} button[type=submit]")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Pin a deterministic locale so the UI initializes in English and the
        # assertions below are stable on any machine.
        page = browser.new_page(locale="en-US")
        page.set_default_timeout(10000)

        def _on_console(msg) -> None:
            if msg.type != "error":
                return
            text = msg.text
            # Expected network-level failures are ignored:
            #  - the flow intentionally triggers bad logins/registers (400) and
            #    starts unauthenticated (/users/me returns 401)
            #  - card images point at external CDNs (scryfall, ...)
            #    that may be unreachable in a sandboxed network; the browser
            #    logs those as ERR_NAME_NOT_RESOLVED resource failures
            # JS exceptions surface separately via pageerror and always fail.
            if "Failed to load resource" in text:
                return
            console_errors.append(text)

        page.on("console", _on_console)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        page.goto(BASE_URL, wait_until="load")
        check("index loads with login button", page.locator("#btn-login").count() == 1)

        # ---------------- Fix 1: login error inside the box ----------------
        page.click("#btn-login")
        open_modal(page, "#modal-login")
        login_modal = page.query_selector("#modal-login")
        check("a11y: dialog role + aria-modal", login_modal.get_attribute("role") == "dialog" and login_modal.get_attribute("aria-modal") == "true")
        page.wait_for_timeout(300)
        check("a11y: focus moved into modal", page.evaluate("document.activeElement && document.activeElement.id") == "login-email")
        # Tab focus trap: Shift+Tab on the first focusable wraps to the last one.
        page.keyboard.press("Shift+Tab")
        page.wait_for_timeout(100)
        last_id = page.evaluate("document.activeElement && document.activeElement.id")
        check("a11y: focus trap wraps to last element", last_id == "btn-goto-register", str(last_id))
        fill_and_submit(page, "#login-email", "#login-password", "#form-login", EMAIL, "WrongPass123")
        page.wait_for_selector("#login-form-error:not(.hidden)", timeout=5000)
        err_text = (page.text_content("#login-form-error") or "").strip()
        check("fix1: login error shown", bool(err_text), err_text[:80])
        el = page.query_selector("#login-form-error")
        modal = page.query_selector("#modal-login .max-w-md")
        if el and modal:
            eb, mb = el.bounding_box(), modal.bounding_box()
            check(
                "fix1: error does not overflow modal",
                eb is not None and mb is not None and eb["y"] + eb["height"] <= mb["y"] + mb["height"] + 2,
            )

        # ---------------- Fix 2: readable register errors ----------------
        page.click("#btn-goto-register")
        open_modal(page, "#modal-register")
        fill_and_submit(page, "#register-email", "#register-password", "#form-register", EMAIL, PASSWORD)
        page.wait_for_selector("#register-form-error:not(.hidden)", timeout=5000)
        dup = (page.text_content("#register-form-error") or "").strip()
        check("fix2: duplicate email readable", "already exists" in dup.lower(), dup[:80])
        check("fix2: no raw error key", "REGISTER_" not in dup)

        fill_and_submit(page, "#register-email", "#register-password", "#form-register", "weak@trackercg.dev", "abc")
        page.wait_for_selector("#register-form-error:not(.hidden)", timeout=5000)
        weak = (page.text_content("#register-form-error") or "").strip()
        check("fix2: weak password readable", "characters" in weak.lower(), weak[:80])

        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        # ---------------- Login (real) ----------------
        page.click("#btn-login")
        open_modal(page, "#modal-login")
        fill_and_submit(page, "#login-email", "#login-password", "#form-login", EMAIL, PASSWORD)
        page.wait_for_selector("#auth-user:not(.hidden)", timeout=10000)
        # Portfolio + collection load in order after login; the grid is the
        # last step, so once it renders the portfolio value is already set.
        page.wait_for_selector("#collection-grid .tcg-card", timeout=15000)
        check("login works", True)
        check("portfolio loaded", page.text_content("#portfolio-total") != "$0.00")

        # ---------------- Fix 4: stable collection pills ----------------
        # Pills are rendered from GET /api/collection/games; wait until the
        # full sorted set (last in order: Yu-Gi-Oh!) is present.
        page.wait_for_selector("#collection-filters .filter-pill:has-text('Yu-Gi-Oh!')", timeout=10000)
        pills = page.query_selector_all("#collection-filters .filter-pill")
        texts = [p.inner_text() for p in pills]
        check("fix4: pills = All + 4 games", len(pills) == 5 and "Pokémon" in texts and "All" in texts, str(texts))
        page.click("#collection-filters .filter-pill:has-text('Pokémon')")
        page.wait_for_timeout(1200)
        active = page.query_selector("#collection-filters .filter-pill.active")
        check("fix4: Pokémon pill active", active is not None and "Pokémon" in active.inner_text())
        remaining = page.query_selector_all("#collection-filters .filter-pill")
        check("fix4: other pills persist", len(remaining) == 5)
        page.click("#collection-filters .filter-pill:has-text('All')")
        page.wait_for_selector("#collection-grid .tcg-card:nth-child(20)", timeout=10000)
        check("fix4: All restores grid", page.query_selector("#collection-grid .tcg-card") is not None)

        # ---------------- Pagination (before split changes totals) ----------------
        page.wait_for_selector("#collection-pagination:not(.hidden)", timeout=10000)
        page_btns = [b.inner_text() for b in page.query_selector_all("#collection-pagination .page-btn")]
        check("pagination shows page 2", "2" in page_btns, str(page_btns))
        cards_p1 = page.query_selector_all("#collection-grid .tcg-card")
        check("page 1 has 20 cards", len(cards_p1) == 20, f"got {len(cards_p1)}")
        page.click("#collection-pagination .page-btn:has-text('2')")
        page.wait_for_selector("#collection-grid .tcg-card", timeout=10000)
        cards_p2 = page.query_selector_all("#collection-grid .tcg-card")
        check("page 2 has 10 cards", len(cards_p2) == 10, f"got {len(cards_p2)}")
        page.click("#collection-pagination .page-btn:has-text('1')")
        page.wait_for_selector("#collection-grid .tcg-card:nth-child(20)", timeout=10000)
        check("page 1 restored", len(page.query_selector_all("#collection-grid .tcg-card")) == 20)

        # ---------------- Fix 6: details modal ----------------
        first_card = page.query_selector("#collection-grid .tcg-card")
        check("fix6: card present", first_card is not None)
        if first_card:
            first_card.query_selector(".p-4").click()
            open_modal(page, "#modal-details")
            check("fix6: details shows name", bool((page.text_content("#details-name") or "").strip()))
            check("fix6: details shows market price", bool((page.text_content("#details-market") or "").strip()))
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
            check("fix6: Esc closes details", page.query_selector("#modal-details.modal-open") is None)

        # ---------------- Fix 7: split button (qty > 1) ----------------
        cards = page.query_selector_all("#collection-grid .tcg-card")
        target = None
        for c in cards:
            m = re.search(r"×(\d+)", c.inner_text())
            if m and int(m.group(1)) > 1:
                target = c
                break
        check("fix7: found card with qty>1", target is not None)
        if target:
            target.query_selector('[data-action="edit"]').click()
            open_modal(page, "#modal-edit")
            split_btn = page.query_selector("#btn-edit-split")
            check("fix7: split button visible", split_btn is not None and split_btn.is_visible())
            # A separated copy must live in a DIFFERENT variant (unique index
            # forbids a second row with the source variant), so set a new
            # condition in the modal before splitting.
            page.select_option("#edit-condition", "Damaged")
            split_btn.click()
            # Wait for the split toast specifically: a generic .toast selector can
            # match an older toast that is still animating out (login toast), so
            # scope the wait to the message this action produces.
            page.wait_for_selector("#toast-container .toast:has-text('one copy')", timeout=8000)
            toast_text = (page.text_content("#toast-container") or "").lower()
            check("fix7: split toast shown", "separated" in toast_text, toast_text[:80])

        # ---------------- Fix 3: logout confirmation ----------------
        page.click("#btn-logout")
        open_modal(page, "#modal-logout")
        page.click("#btn-logout-cancel")
        page.wait_for_timeout(400)
        check("fix3: cancel keeps session", page.query_selector("#auth-user:not(.hidden)") is not None)
        page.click("#btn-logout")
        open_modal(page, "#modal-logout")
        page.click("#btn-logout-confirm")
        page.wait_for_selector("#auth-anon:not(.hidden)", timeout=10000)
        check("fix3: portfolio reset to $0.00", page.text_content("#portfolio-total") == "$0.00")
        toast_text = (page.text_content("#toast-container") or "").lower()
        check("fix3: logout toast", "signed out" in toast_text, toast_text[:80])

        # ---------------- Login again for search flows ----------------
        page.click("#btn-login")
        open_modal(page, "#modal-login")
        fill_and_submit(page, "#login-email", "#login-password", "#form-login", EMAIL, PASSWORD)
        page.wait_for_selector("#auth-user:not(.hidden)", timeout=10000)

        # ---------------- Fix 5: search pills highlighted ----------------
        page.click("#nav-search")
        page.fill("#search-input", "blue")
        page.wait_for_selector("#search-results .tcg-card", timeout=15000)
        page.click("#search-filters .filter-pill:has-text('Yu-Gi-Oh!')")
        page.wait_for_timeout(1500)
        active = page.query_selector("#search-filters .filter-pill.active")
        check("fix5: search pill highlighted", active is not None and "Yu-Gi-Oh!" in active.inner_text())
        search_pills = page.query_selector_all("#search-filters .filter-pill")
        check("fix5: all 4 enum games offered", len(search_pills) == 5, str(len(search_pills)))

        # ---------------- Fix 8: immediate local search ----------------
        # Clear the active Yu-Gi-Oh! filter from Fix 5 first, otherwise the
        # query runs against YGO only and matches the previous "blue" grid.
        page.click("#search-filters .filter-pill:has-text('All')")
        page.wait_for_timeout(600)
        t0 = time.time()
        page.fill("#search-input", "void")
        # Wait for the specific local card (Void Gate) rather than any
        # .tcg-card — the previous search grid already contains elements.
        page.wait_for_selector("#search-results .tcg-card:has-text('Void Gate')", timeout=8000)
        elapsed = time.time() - t0
        check("fix8: local results immediate", elapsed < 3.0, f"{elapsed:.2f}s")
        names = page.text_content("#search-results") or ""
        check("fix8: Riftbound card found locally", "Void Gate" in names, names[:80])
        # Void Gate is in the collection (page 1), so her search card shows the badge.
        void_card = page.query_selector("#search-results .tcg-card:has-text('Void Gate')")
        check("fix8: in-collection badge shown", void_card is not None and "In collection" in (void_card.inner_text() or ""))

        # ---------------- Language switch keeps pills & modals ----------------
        page.click("#btn-lang")
        page.wait_for_timeout(400)
        check("lang: switch to ES", page.text_content("#nav-search") == "Buscar")
        page.wait_for_selector("#search-filters .filter-pill:has-text('Riftbound')", timeout=5000)
        check("lang: pills still rendered", True)
        page.click("#btn-lang")
        page.wait_for_timeout(400)
        check("lang: switch back to EN", page.text_content("#nav-search") == "Search")

        # ---------------- Console errors ----------------
        page.wait_for_timeout(1000)
        check("no console errors", not console_errors, str(console_errors[:3]))

        browser.close()

    print("\n" + ("=" * 60))
    if failures:
        print(f"SMOKE TEST FAILED: {len(failures)} failed check(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("SMOKE TEST PASSED — all checks OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
