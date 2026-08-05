from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from src.models import Game
from src.scrapers.base import CardData, ScraperBase, random_sleep, to_decimal

YGOPRODECK_API = "https://db.ygoprodeck.com/api/v7/cardinfo.php"


class YugiohScraper(ScraperBase):
    game: Game = Game.YUGIOH

    async def search(self, query: str) -> list[CardData]:
        await random_sleep(0.5, 1.5)
        results: list[CardData] = []

        resp = await self._client.get(
            YGOPRODECK_API,
            params={"fname": query, "num": 20, "offset": 0},
        )
        # YGOPRODeck answers 400 when no card matches the fuzzy name.
        if resp.status_code == 400:
            return results
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()

        for card in body.get("data", []):
            results.append(self._parse_card(card))

        return results

    async def get_price(self, external_id: str) -> Decimal | None:
        await random_sleep(0.3, 1.0)
        resp = await self._client.get(YGOPRODECK_API, params={"id": external_id})
        if resp.status_code != 200:
            return None
        body: dict[str, Any] = resp.json()
        data = body.get("data") or []
        if not data:
            return None
        prices = (data[0].get("card_prices") or [{}])[0]
        tcgplayer_price = prices.get("tcgplayer_price")
        if tcgplayer_price:
            return to_decimal(tcgplayer_price)
        cardmarket_price = prices.get("cardmarket_price")
        if cardmarket_price:
            return to_decimal(cardmarket_price)
        return None

    @staticmethod
    def _parse_card(card: dict[str, Any]) -> CardData:
        prices = (card.get("card_prices") or [{}])[0]
        price = (
            prices.get("tcgplayer_price")
            or prices.get("cardmarket_price")
            or 0
        )

        sets = card.get("card_sets") or []
        if sets:
            set_name = sets[0].get("set_name", "")
            set_code = sets[0].get("set_code", "")
            collector_number = sets[0].get("set_code", "")
        else:
            set_name = ""
            set_code = ""
            collector_number = ""

        images = (card.get("card_images") or [{}])[0]

        return CardData(
            game=Game.YUGIOH,
            name=card.get("name", "Unknown"),
            set_name=set_name,
            set_code=set_code,
            collector_number=collector_number,
            external_id=str(card.get("id", "")),
            rarity=card.get("rarity", "Common"),
            image_url=images.get("image_url", ""),
            market_price=to_decimal(price),
            last_updated=datetime.now(timezone.utc),
            game_metadata={
                "id": card.get("id"),
                "type": card.get("type"),
                "frame_type": card.get("frameType"),
                "attribute": card.get("attribute"),
                "race": card.get("race"),
                "atk": card.get("atk"),
                "def": card.get("def"),
                "level": card.get("level"),
                "archetype": card.get("archetype"),
                "banlist_info": card.get("banlist_info"),
            },
        )
