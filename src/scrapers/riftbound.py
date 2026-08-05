from __future__ import annotations

from src.models import Game
from src.scrapers.tcggo import TcggoScraper


class RiftboundScraper(TcggoScraper):
    game: Game = Game.RIFTBOUND
    game_slug: str = "riftbound"
