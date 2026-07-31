from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from src.models import Game
from src.scrapers.base import CardData, ScraperBase, random_sleep, to_decimal

logger = logging.getLogger(__name__)

POKEMON_API = "https://api.pokemontcg.io/v2/cards"


class PokemonScraper(ScraperBase):
    game: Game = Game.POKEMON

    def __init__(self) -> None:
        super().__init__()
        from src.config import settings

        self._api_key = settings.pokemon_tcg_api_key
        if self._api_key:
            self._client.headers.update({"X-Api-Key": self._api_key})
        else:
            logger.warning(
                "POKEMON_TCG_API_KEY is not set; pokemontcg.io requests will be "
                "rate-limited and may fail. Set it in the .env file."
            )

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
        if resp.status_code == 401 or resp.status_code == 403:
            logger.error(
                "pokemontcg.io rejected the request (HTTP %s). Check POKEMON_TCG_API_KEY.",
                resp.status_code,
            )
            return results
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()

        for card in body.get("data", []):
            results.append(self._parse_card(card))

        return results

    async def get_price(self, external_id: str) -> Decimal | None:
        await random_sleep(0.3, 1.0)
        resp = await self._client.get(f"{POKEMON_API}/{external_id}")
        if resp.status_code != 200:
            return None
        body: dict[str, Any] = resp.json()
        card = body.get("data", {})
        prices: dict[str, Any] = card.get("cardmarket", {}).get("prices", {})
        avg_price = prices.get("averageSellPrice")
        if avg_price is not None:
            return to_decimal(avg_price)
        trend_price = prices.get("trendPrice")
        if trend_price is not None:
            return to_decimal(trend_price)
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
            set_code=card.get("set", {}).get("ptcgoCode", "") or card.get("set", {}).get("id", ""),
            collector_number=card.get("number", ""),
            external_id=card.get("id", ""),
            rarity=card.get("rarity", "Common"),
            image_url=images.get("large", images.get("small", "")),
            market_price=to_decimal(price),
            last_updated=datetime.now(timezone.utc),
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
