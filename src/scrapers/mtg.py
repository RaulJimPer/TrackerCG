from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.models import Game
from src.scrapers.base import CardData, ScraperBase, random_sleep

SCRYFALL_SEARCH = "https://api.scryfall.com/cards/search"
SCRYFALL_NAMED = "https://api.scryfall.com/cards/named"


class MtgScraper(ScraperBase):
    game: Game = Game.MTG

    async def search(self, query: str) -> list[CardData]:
        await random_sleep(0.5, 1.5)
        results: list[CardData] = []
        url = f"{SCRYFALL_SEARCH}?q={query}&order=relevance&unique=prints"

        resp = await self._client.get(url)
        if resp.status_code == 404:
            return results
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()

        for card in body.get("data", []):
            results.append(self._parse_card(card))

        return results

    async def get_price(self, card_id: str) -> float | None:
        await random_sleep(0.3, 1.0)
        url = f"https://api.scryfall.com/cards/{card_id}"
        resp = await self._client.get(url)
        if resp.status_code != 200:
            return None
        body: dict[str, Any] = resp.json()
        prices: dict[str, str | None] = body.get("prices", {})
        usd = prices.get("usd")
        if usd:
            return float(usd)
        usd_foil = prices.get("usd_foil")
        if usd_foil:
            return float(usd_foil)
        return None

    @staticmethod
    def _parse_card(card: dict[str, Any]) -> CardData:
        prices: dict[str, str | None] = card.get("prices", {})
        usd = prices.get("usd") or prices.get("usd_foil") or "0"
        return CardData(
            game=Game.MTG,
            name=card.get("name", "Unknown"),
            set_name=card.get("set_name", ""),
            set_code=card.get("set", "").upper(),
            collector_number=card.get("collector_number", ""),
            rarity=card.get("rarity", "common").capitalize(),
            image_url=(
                card.get("image_uris", {}).get("normal", "")
                or card.get("card_faces", [{}])[0].get("image_uris", {}).get("normal", "")
            ),
            market_price=float(usd) if usd else 0.0,
            last_updated=datetime.now(timezone.utc).replace(tzinfo=None),
            game_metadata={
                "oracle_id": card.get("oracle_id"),
                "mana_cost": card.get("mana_cost", ""),
                "cmc": card.get("cmc"),
                "type_line": card.get("type_line", ""),
                "oracle_text": card.get("oracle_text", ""),
                "power": card.get("power"),
                "toughness": card.get("toughness"),
                "legalities": card.get("legalities"),
            },
        )
