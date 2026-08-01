from __future__ import annotations

import asyncio
import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncIterator
from urllib.parse import urlencode

from bs4 import BeautifulSoup, Tag
from playwright.async_api import Browser, Page, Playwright, async_playwright

from src.models import Game
from src.scrapers.base import CardData, ScraperBase, random_sleep, to_decimal

logger = logging.getLogger(__name__)

TCGPLAYER_SEARCH = "https://www.tcgplayer.com/search/yugioh/product"
TCGPLAYER_PRODUCT = "https://www.tcgplayer.com/product"

_pw: Playwright | None = None
_browser: Browser | None = None
_pw_loop_id: int = 0
_pw_lock: asyncio.Lock | None = None


async def _get_pw_lock() -> asyncio.Lock:
    global _pw_lock, _pw_loop_id
    loop_id = id(asyncio.get_running_loop())
    if _pw_lock is None or _pw_loop_id != loop_id:
        _pw_lock = asyncio.Lock()
        _pw_loop_id = loop_id
    return _pw_lock


async def _get_browser() -> Browser:
    global _pw, _browser, _pw_loop_id
    loop_id = id(asyncio.get_running_loop())
    if _browser is None or _pw_loop_id != loop_id:
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(headless=True)
        _pw_loop_id = loop_id
    return _browser


@asynccontextmanager
async def _page() -> AsyncIterator[Page]:
    lock = await _get_pw_lock()
    async with lock:
        browser = await _get_browser()
        page = await browser.new_page()
        try:
            yield page
        finally:
            await page.close()


async def close_playwright() -> None:
    global _pw, _browser
    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    if _pw is not None:
        try:
            await _pw.stop()
        except Exception:
            pass
        _pw = None


class YugiohScraper(ScraperBase):
    game: Game = Game.YUGIOH

    async def search(self, query: str) -> list[CardData]:
        await random_sleep(1.0, 2.5)
        results: list[CardData] = []

        async with _page() as page:
            params = urlencode(
                {
                    "q": query,
                    "ProductLineName": "Yu-Gi-Oh",
                    "ProductTypeName": "Cards",
                }
            )
            url = f"{TCGPLAYER_SEARCH}?{params}"
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await random_sleep(1.0, 2.0)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            for product in soup.select(".search-result__product")[:20]:
                try:
                    card = self._parse_card(product)
                except Exception:
                    logger.warning("Skipping malformed Yu-Gi-Oh product card", exc_info=True)
                    card = None
                if card is not None:
                    results.append(card)

        return results

    async def get_price(self, external_id: str) -> Decimal | None:
        await random_sleep(1.0, 2.0)

        async with _page() as page:
            url = f"{TCGPLAYER_PRODUCT}/{external_id}"
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await random_sleep(1.0, 1.5)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            price_el = soup.select_one('[class*="market-price--value"]') or soup.select_one('[class*="price"]')
            if price_el is None:
                return None
            text = price_el.get_text(strip=True)
            match = re.search(r"\$?(\d+\.?\d*)", text)
            if match:
                return to_decimal(match.group(1))
            return None

    async def close(self) -> None:
        await close_playwright()

    @staticmethod
    def _parse_card(product: Tag) -> CardData | None:
        name_el = product.select_one(".product-card__title")
        if name_el is None:
            return None
        name = name_el.get_text(strip=True)

        link_el = product.select_one("a")
        link = link_el.get("href", "") if link_el and isinstance(link_el.get("href"), str) else ""
        tcgplayer_id = ""
        if link:
            match = re.search(r"/product/(\d+)", link)
            if match:
                tcgplayer_id = match.group(1)
        if not tcgplayer_id:
            return None

        set_name_el = product.select_one(".product-card__set-name__variant")
        set_name = set_name_el.get_text(strip=True) if set_name_el else ""

        rarity_el = product.select_one(".product-card__rarity__variant")
        rarity = "Common"
        collector_number = ""
        if rarity_el is not None:
            spans = rarity_el.select("span")
            if len(spans) >= 1:
                rarity = spans[0].get_text(strip=True).rstrip(",")
            if len(spans) >= 2:
                collector_number = spans[1].get_text(strip=True).lstrip("#")

        price_el = product.select_one(".product-card__market-price--value")
        price: Decimal = Decimal("0")
        if price_el is not None:
            text = price_el.get_text(strip=True)
            match = re.search(r"\$?(\d+\.?\d*)", text)
            if match:
                price = to_decimal(match.group(1))

        img_el = product.select_one("img")
        image_url = ""
        if img_el is not None:
            src = img_el.get("src") or ""
            if not src.startswith("data:"):
                image_url = src
            else:
                ds = img_el.get("data-src") or ""
                image_url = ds

        return CardData(
            game=Game.YUGIOH,
            name=name,
            set_name=set_name,
            set_code="",
            collector_number=collector_number,
            external_id=tcgplayer_id,
            rarity=rarity,
            image_url=image_url,
            market_price=price,
            last_updated=datetime.now(timezone.utc),
            game_metadata={"tcgplayer_id": tcgplayer_id, "tcgplayer_url": link},
        )
