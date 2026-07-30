from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup
from httpx import AsyncClient

from src.models import Game

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Edge/126.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
]


@dataclass
class CardData:
    game: Game
    name: str
    set_name: str
    set_code: str
    collector_number: str
    rarity: str = "Common"
    image_url: str = ""
    market_price: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    game_metadata: dict[str, Any] = field(default_factory=dict)


def random_headers() -> dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/json,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }


async def random_sleep(min_s: float = 1.0, max_s: float = 3.0) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


class ScraperBase(ABC):
    game: Game

    def __init__(self) -> None:
        self._client = AsyncClient(headers=random_headers(), timeout=30.0)

    @abstractmethod
    async def search(self, query: str) -> list[CardData]:
        ...

    @abstractmethod
    async def get_price(self, card_id: str) -> float | None:
        ...

    async def close(self) -> None:
        await self._client.aclose()

    async def _soup(self, url: str) -> BeautifulSoup:
        resp = await self._client.get(url)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
