"""Offline unit tests for the TCGGO HTML scraper parsers (no network)."""
from __future__ import annotations

from decimal import Decimal

from bs4 import BeautifulSoup

from src.models import Game
from src.scrapers.pokemon import PokemonScraper
from src.scrapers.riftbound import RiftboundScraper
from src.scrapers.tcggo import (
    TcggoScraper,
    parse_eur_price,
    parse_set_code_and_number,
)


def test_parse_eur_price() -> None:
    assert parse_eur_price("100,00 €") == Decimal("100.00")
    assert parse_eur_price("0,10 €") == Decimal("0.10")
    assert parse_eur_price("340 €") == Decimal("340")
    assert parse_eur_price("10.729 €") == Decimal("10729")
    assert parse_eur_price("3,45 €") == Decimal("3.45")
    assert parse_eur_price("N/A") is None
    assert parse_eur_price("Stable") is None
    assert parse_eur_price("") is None
    assert parse_eur_price(None) is None


def test_parse_set_code_and_number() -> None:
    assert parse_set_code_and_number("VEN-168/166") == ("VEN", "168")
    assert parse_set_code_and_number("Demolitionist · VEN-168/166") == ("VEN", "168")
    assert parse_set_code_and_number("OGN 202") == ("OGN", "202")
    assert parse_set_code_and_number("OGN 202b") == ("OGN", "202b")
    assert parse_set_code_and_number("OGN-301*/298") == ("OGN", "301*")
    assert parse_set_code_and_number("OGN-030a/298") == ("OGN", "030a")
    assert parse_set_code_and_number("ASC 22") == ("ASC", "22")
    assert parse_set_code_and_number("MEP 023") == ("MEP", "023")
    assert parse_set_code_and_number("CRZ 18") == ("CRZ", "18")
    # Sealed products / unparseable promo numbering -> no card identity.
    assert parse_set_code_and_number("OGN") == ("", "")
    assert parse_set_code_and_number("PROK FND251") == ("", "")
    assert parse_set_code_and_number("") == ("", "")


def test_parse_search_card_riftbound() -> None:
    html = """
    <div class="t1-card group overflow-hidden flex flex-col h-full game-riftbound">
      <div class="relative t1-item-art">
        <span class="t1-chip absolute bottom-2 left-2 z-10">#VEN-168/166</span>
        <a href="https://www.tcggo.com/riftbound/vendetta/jinx" class="flex">
          <img src="https://images.tcggo.com/tcggo/storage/39019/conversions/jinx-large.webp"/>
        </a>
      </div>
      <div class="p-3.5 flex flex-col mt-auto shrink-0 space-y-1">
        <p class="text-xs text-slate-400 truncate">Vendetta</p>
        <a class="font-semibold text-white" href="https://www.tcggo.com/riftbound/vendetta/jinx">Jinx</a>
        <p class="text-xs text-slate-400 truncate">Demolitionist · VEN-168/166</p>
        <div class="flex items-center justify-between pt-2">
          <span class="font-display text-lg font-bold text-white">100,00 €</span>
          <span class="trend trend-stable">Stable</span>
        </div>
      </div>
    </div>
    """
    block = BeautifulSoup(html, "html.parser").select_one(".t1-card")
    card = RiftboundScraper()._parse_search_card(block)
    assert card is not None
    assert card.game == Game.RIFTBOUND
    assert card.name == "Jinx"
    assert card.set_name == "Vendetta"
    assert card.set_code == "VEN"
    assert card.collector_number == "168"
    assert card.external_id == "riftbound/vendetta/jinx"
    assert card.image_url.startswith("https://images.tcggo.com/")
    assert card.market_price == Decimal("100.00")
    assert card.game_metadata["card_type"] == "Demolitionist"
    assert card.game_metadata["tcggo_url"] == "https://www.tcggo.com/riftbound/vendetta/jinx"


def test_parse_search_card_pokemon() -> None:
    html = """
    <div class="t1-card group overflow-hidden flex flex-col h-full game-pokemon">
      <span class="t1-chip">#54</span>
      <img src="https://images.tcggo.com/tcggo/storage/2072/conversions/charizard-large.webp"/>
      <p class="text-xs text-slate-400 truncate">Paldean Fates</p>
      <a class="font-semibold text-white" href="https://www.tcggo.com/pokemon/paldean-fates/charizard-ex-54">Charizard ex</a>
      <p class="text-xs text-slate-400 truncate">PAF 54</p>
      <span class="font-display text-lg font-bold text-white">2,00 €</span>
    </div>
    """
    block = BeautifulSoup(html, "html.parser").select_one(".t1-card")
    card = PokemonScraper()._parse_search_card(block)
    assert card is not None
    assert card.game == Game.POKEMON
    assert card.name == "Charizard ex"
    assert card.set_name == "Paldean Fates"
    assert card.set_code == "PAF"
    assert card.collector_number == "54"
    assert card.external_id == "pokemon/paldean-fates/charizard-ex-54"
    assert card.market_price == Decimal("2.00")


def test_parse_search_card_filters_sealed_products() -> None:
    html = """
    <div class="t1-card group overflow-hidden flex flex-col h-full game-pokemon">
      <span class="t1-chip">PAF</span>
      <img src="https://images.tcggo.com/tcggo/storage/20838/conversions/tin-large.webp"/>
      <p class="text-xs text-slate-400 truncate">Paldean Fates</p>
      <a class="font-semibold text-white" href="https://www.tcggo.com/pokemon/paldean-fates/tin">Tera Charizard ex Tin</a>
      <span class="font-display text-lg font-bold text-white">100,00 €</span>
    </div>
    """
    block = BeautifulSoup(html, "html.parser").select_one(".t1-card")
    assert TcggoScraper()._parse_search_card(block) is None


def test_detail_price_us_market_preferred() -> None:
    html = """
    <div class="t1-card !transform-none p-3.5">
      <div class="meta-label">EU Low</div>
      <div class="font-display text-2xl font-bold text-white mt-1">2,00 €</div>
      <div class="meta-label">US Market</div>
      <div class="font-display text-2xl font-bold text-white mt-1">3,45 €</div>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    assert TcggoScraper._parse_detail_price(soup) == Decimal("3.45")


def test_detail_price_eu_low_fallback() -> None:
    html = """
    <div class="t1-card !transform-none p-3.5">
      <div class="meta-label">EU Low</div>
      <div class="font-display text-2xl font-bold text-white mt-1">100,00 €</div>
      <div class="meta-label">US Market</div>
      <div class="font-display text-2xl font-bold text-white mt-1">N/A</div>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    assert TcggoScraper._parse_detail_price(soup) == Decimal("100.00")


def test_detail_price_missing_returns_none() -> None:
    html = """
    <div class="t1-card !transform-none p-3.5">
      <div class="meta-label">US Market</div>
      <div class="font-display text-2xl font-bold text-white mt-1">N/A</div>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    assert TcggoScraper._parse_detail_price(soup) is None
