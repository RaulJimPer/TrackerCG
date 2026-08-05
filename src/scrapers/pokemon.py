from __future__ import annotations

from src.models import Game
from src.scrapers.tcggo import TcggoScraper


class PokemonScraper(TcggoScraper):
    game: Game = Game.POKEMON
    game_slug: str = "pokemon"
