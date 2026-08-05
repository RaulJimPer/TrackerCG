from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup, Tag

from src.models import Game
from src.scrapers.base import CardData, ScraperBase, random_sleep

logger = logging.getLogger(__name__)

TCGGO_BASE = "https://www.tcggo.com"
TCGGO_SEARCH = f"{TCGGO_BASE}/search"

# Set code + collector number, anywhere in a line: "VEN-168/166", "OGN 202b",
# "Demolitionist · VEN-168/166", "ASC 22", "MEP 023".
_SET_CODE_NUMBER_RE = re.compile(r"([A-Z]{2,6})[\s-]+(\d+[A-Za-z*]*)(?:/\d+)?")

# TCGGO EUR amounts: "100,00 €", "340 €", "10.729 €" ("," = decimals, "." = thousands).
_EUR_PRICE_RE = re.compile(r"([\d.,]+)\s*€")


def parse_eur_price(text: str) -> Decimal | None:
    """Parse a TCGGO EUR price like '100,00 €'; N/A and garbage return None."""
    if not text:
        return None
    match = _EUR_PRICE_RE.search(text)
    if match is None:
        return None
    normalized = match.group(1).replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except Exception:
        return None


def parse_set_code_and_number(text: str) -> tuple[str, str]:
    """Best-effort split of 'VEN-168/166' or 'Demolitionist · ASC 22'."""
    if not text:
        return "", ""
    match = _SET_CODE_NUMBER_RE.search(text)
    if match is None:
        return "", ""
    return match.group(1), match.group(2)


class TcggoScraper(ScraperBase):
    """HTML scraper for tcggo.com public card pages (no API key required).

    Subclasses set ``game`` and ``game_slug`` (e.g. ``"riftbound"`` or
    ``"pokemon"``); the search page and per-card pages are server-rendered and
    public, so price data is scraped with httpx + BeautifulSoup.
    """

    game: Game
    game_slug: str = ""

    async def search(self, query: str) -> list[CardData]:
        await random_sleep(0.5, 1.5)
        results: list[CardData] = []

        try:
            resp = await self._client.get(TCGGO_SEARCH, params={"q": query})
        except httpx.HTTPError:
            logger.warning("TCGGO search request failed for %r", query, exc_info=True)
            return results
        if resp.status_code != 200:
            logger.warning("TCGGO search failed (HTTP %s)", resp.status_code)
            return results

        soup = BeautifulSoup(resp.text, "html.parser")
        for block in soup.select(f"div.t1-card.game-{self.game_slug}")[:20]:
            try:
                parsed = self._parse_search_card(block)
            except Exception:
                logger.warning("Skipping malformed TCGGO search result", exc_info=True)
                parsed = None
            if parsed is not None:
                results.append(parsed)

        return results

    def _parse_search_card(self, block: Tag) -> CardData | None:
        link = block.select_one("a.font-semibold")
        if link is None:
            return None
        href = link.get("href", "")
        name = link.get_text(strip=True)
        if not name or not isinstance(href, str) or not href.startswith(TCGGO_BASE):
            return None

        paragraphs = block.select("p.text-xs.text-slate-400")
        set_name = paragraphs[0].get_text(strip=True) if paragraphs else ""
        code_line = paragraphs[1].get_text(strip=True) if len(paragraphs) > 1 else ""
        set_code, collector_number = parse_set_code_and_number(code_line)
        # Sealed products (tins, decks, boxes) carry no collector number.
        if not collector_number:
            return None

        img = block.select_one("img")
        image_url = img.get("src", "") if img else ""

        price_el = block.select_one(".font-display")
        price = parse_eur_price(price_el.get_text(strip=True)) if price_el else None

        card_type = ""
        if " · " in code_line:
            card_type = code_line.split(" · ", 1)[0].strip()

        return CardData(
            game=self.game,
            name=name,
            set_name=set_name,
            set_code=set_code,
            collector_number=collector_number,
            external_id=href.removeprefix(f"{TCGGO_BASE}/"),
            rarity="",
            image_url=image_url,
            market_price=price if price is not None else Decimal("0"),
            last_updated=datetime.now(timezone.utc),
            game_metadata={
                "tcggo_url": href,
                "card_type": card_type,
            },
        )

    async def get_price(self, external_id: str) -> Decimal | None:
        await random_sleep(0.3, 1.0)
        url = f"{TCGGO_BASE}/{external_id}"
        try:
            resp = await self._client.get(url)
        except httpx.HTTPError:
            logger.warning(
                "TCGGO price request failed for %s", external_id, exc_info=True
            )
            return None
        if resp.status_code != 200:
            logger.warning("TCGGO price fetch failed (HTTP %s)", resp.status_code)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        return self._parse_detail_price(soup)

    @staticmethod
    def _parse_detail_price(soup: BeautifulSoup) -> Decimal | None:
        """US Market (TCGPlayer) first, then EU Low (Cardmarket)."""
        for label in ("US Market", "EU Low"):
            value = TcggoScraper._meta_value(soup, label)
            price = parse_eur_price(value)
            if price is not None:
                return price
        return None

    @staticmethod
    def _meta_value(soup: BeautifulSoup, label: str) -> str:
        """Value next to a ``div.meta-label`` with the given text ('' if absent)."""
        for label_el in soup.select("div.meta-label"):
            if label_el.get_text(strip=True) == label:
                value_el = label_el.find_next_sibling("div")
                if value_el is not None:
                    return value_el.get_text(strip=True)
        return ""
