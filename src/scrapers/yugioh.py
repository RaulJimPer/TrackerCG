from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup, Tag
from playwright.async_api import async_playwright

from src.models import Game
from src.scrapers.base import CardData, ScraperBase, random_sleep

TCGPLAYER_SEARCH = "https://www.tcgplayer.com/search/yugioh/product"
TCGPLAYER_PRODUCT = "https://www.tcgplayer.com/product"


class YugiohScraper(ScraperBase):
    game: Game = Game.YUGIOH

    async def search(self, query: str) -> list[CardData]:
        await random_sleep(1.0, 2.5)
        results: list[CardData] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                url = f"{TCGPLAYER_SEARCH}?q={query}&ProductLineName=Yu-Gi-Oh&ProductTypeName=Cards"
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await random_sleep(1.0, 2.0)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                for product in soup.select(".search-result__product")[:20]:
                    card = self._parse_card(product)
                    if card is not None:
                        results.append(card)
            finally:
                await browser.close()

        return results

    async def get_price(self, card_id: str) -> float | None:
        await random_sleep(1.0, 2.0)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                url = f"{TCGPLAYER_PRODUCT}/{card_id}"
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
                    return float(match.group(1))
                return None
            finally:
                await browser.close()

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

        set_name_el = product.select_one(".product-card__set-name__variant")
        set_name = set_name_el.get_text(strip=True) if set_name_el else ""

        rarity_el = product.select_one(".product-card__rarity__variant")
        rarity = "Common"
        collector_number = ""
        if rarity_el:
            spans = rarity_el.select("span")
            if len(spans) >= 1:
                rarity = spans[0].get_text(strip=True).rstrip(",")
            if len(spans) >= 2:
                collector_number = spans[1].get_text(strip=True).lstrip("#")

        price_el = product.select_one(".product-card__market-price--value")
        price = 0.0
        if price_el is not None:
            text = price_el.get_text(strip=True)
            match = re.search(r"\$?(\d+\.?\d*)", text)
            if match:
                price = float(match.group(1))

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
            rarity=rarity,
            image_url=image_url,
            market_price=price,
            last_updated=datetime.now(timezone.utc).replace(tzinfo=None),
            game_metadata={"tcgplayer_id": tcgplayer_id, "tcgplayer_url": link},
        )
