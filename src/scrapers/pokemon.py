from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.models import Game
from src.scrapers.base import CardData, ScraperBase, random_sleep

POKEMON_API = "https://api.pokemontcg.io/v2/cards"


class PokemonScraper(ScraperBase):
    game: Game = Game.POKEMON

    def __init__(self) -> None:
        super().__init__()
        from src.config import settings
        self._client.headers.update({"X-Api-Key": settings.pokemon_tcg_api_key})

    async def search(self, query: str) -> list[CardData]:
        await random_sleep(0.5, 1.5)
        results: list[CardData] = []
        params: dict[str, Any] = {
            "q": f"name:{query}*",
            "pageSize": 20,
            "orderBy": "set.releaseDate,-number",
        }

        resp = await self._client.get(POKEMON_API, params=params)
        if resp.status_code == 404:
            return results
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()

        for card in body.get("data", []):
            results.append(self._parse_card(card))

        return results

    async def get_price(self, card_id: str) -> float | None:
        await random_sleep(0.3, 1.0)
        resp = await self._client.get(f"{POKEMON_API}/{card_id}")
        if resp.status_code != 200:
            return None
        body: dict[str, Any] = resp.json()
        card = body.get("data", {})
        prices: dict[str, Any] = card.get("cardmarket", {}).get("prices", {})
        avg_price = prices.get("averageSellPrice")
        if avg_price is not None:
            return float(avg_price)
        trend_price = prices.get("trendPrice")
        if trend_price is not None:
            return float(trend_price)
        return None

    @staticmethod
    def _parse_card(card: dict[str, Any]) -> CardData:
        prices: dict[str, Any] = card.get("cardmarket", {}).get("prices", {})
        price = prices.get("averageSellPrice") or prices.get("trendPrice") or 0

        images = card.get("images", {})
        legalities = card.get("legalities", {})

        return CardData(
            game=Game.POKEMON,
            name=card.get("name", "Unknown"),
            set_name=card.get("set", {}).get("name", ""),
            set_code=card.get("set", {}).get("ptcgoCode", ""),
            collector_number=card.get("number", ""),
            rarity=card.get("rarity", "Common"),
            image_url=images.get("large", images.get("small", "")),
            market_price=float(price),
            last_updated=datetime.now(timezone.utc).replace(tzinfo=None),
            game_metadata={
                "id": card.get("id"),
                "supertype": card.get("supertype"),
                "subtypes": card.get("subtypes"),
                "types": card.get("types"),
                "hp": card.get("hp"),
                "artist": card.get("artist"),
                "legalities": legalities,
            },
        )
