from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from src.models import Game
from src.scrapers.base import CardData, ScraperBase, random_sleep, to_decimal

logger = logging.getLogger(__name__)

SCRYDEX_RIFTBOUND_API = "https://api.scrydex.com/riftbound/v1/cards"


class RiftboundScraper(ScraperBase):
    game: Game = Game.RIFTBOUND

    def __init__(self) -> None:
        super().__init__()
        from src.config import settings

        self._api_key, self._team_id = settings.scrydex_api_key, settings.scrydex_team_id
        if not self._api_key or not self._team_id:
            logger.warning(
                "SCRYDEX_API_KEY / SCRYDEX_TEAM_ID are not set; Riftbound "
                "searches will be limited. Set both in the .env file."
            )
            return
        self._client.headers.update(
            {"X-Api-Key": self._api_key, "X-Team-ID": self._team_id}
        )

    async def search(self, query: str) -> list[CardData]:
        await random_sleep(0.5, 1.5)
        results: list[CardData] = []

        resp = await self._client.get(
            SCRYDEX_RIFTBOUND_API,
            params={"q": f"name:{query}", "page_size": 20, "include": "prices"},
        )
        if resp.status_code != 200:
            logger.error(
                "Scrydex Riftbound search failed (HTTP %s)", resp.status_code
            )
            return results
        body: dict[str, Any] = resp.json()

        for card in body.get("data", []):
            parsed = self._parse_card(card)
            if parsed is not None:
                results.append(parsed)

        return results

    async def get_price(self, external_id: str) -> Decimal | None:
        await random_sleep(0.3, 1.0)
        resp = await self._client.get(
            f"{SCRYDEX_RIFTBOUND_API}/{external_id}",
            params={"include": "prices"},
        )
        if resp.status_code != 200:
            return None
        body: dict[str, Any] = resp.json()
        card = body.get("data") or {}
        parsed = self._parse_card(card)
        if parsed is None:
            return None
        return parsed.market_price or None

    @staticmethod
    def _parse_card(card: dict[str, Any]) -> CardData | None:
        card_id = card.get("id")
        name = card.get("name")
        if not card_id or not name:
            return None

        expansion = card.get("expansion") or {}
        images = card.get("images") or []
        image_url = ""
        for img in images:
            if img.get("type") == "front" and img.get("large"):
                image_url = img["large"]
                break

        variants = card.get("variants") or []
        price: Decimal = Decimal("0")
        if variants:
            prices = (variants[0].get("prices") or [{}])[0]
            price = to_decimal(prices.get("market") or prices.get("low") or 0)

        return CardData(
            game=Game.RIFTBOUND,
            name=name,
            set_name=expansion.get("name", ""),
            set_code=expansion.get("code", ""),
            collector_number=str(card.get("number", "")),
            external_id=card_id,
            rarity=card.get("rarity", "Common"),
            image_url=image_url,
            market_price=price,
            last_updated=datetime.now(timezone.utc),
            game_metadata={
                "id": card_id,
                "domain": card.get("domain"),
                "card_type": card.get("type"),
                "artist": card.get("artist"),
                "language": card.get("language"),
            },
        )
