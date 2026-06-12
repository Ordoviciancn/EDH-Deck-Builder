from __future__ import annotations

from dataclasses import dataclass, field


WUBRG = ("W", "U", "B", "R", "G")


@dataclass(frozen=True)
class Card:
    oracle_id: str
    name: str
    mana_cost: str
    cmc: float
    colors: set[str]
    color_identity: set[str]
    type_line: str
    oracle_text: str
    legal_commander: bool
    banned_commander: bool
    can_be_commander: bool
    price_usd: float | None = None
    scryfall_uri: str = ""
    image_uri: str = ""
    edhrec_rank: int | None = None
    games: tuple[str, ...] = ()
    set_code: str = ""
    set_name: str = ""
    layout: str = ""
    border_color: str = ""
    digital: bool = False

    @property
    def is_basic_land(self) -> bool:
        return "Basic" in self.type_line and "Land" in self.type_line

    @property
    def is_land(self) -> bool:
        return "Land" in self.type_line


@dataclass(frozen=True)
class Combo:
    name: str
    cards: tuple[str, ...]
    result: str
    source: str
    tags: tuple[str, ...] = ()


@dataclass
class BuildRequest:
    commander: str
    theme: str = ""
    budget: float | None = None
    power_level: int = 6
    allow_infinite: bool = True
    combo_preference: str = "balanced"
    meta_profile: str = "balanced"
    meta_notes: str = ""
    allow_universes_beyond: bool = False
    must_include: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)


@dataclass
class DeckCard:
    card: Card
    role: str
    score: float
    reason: str = ""


@dataclass
class Deck:
    commander: Card
    cards: list[DeckCard]

    def names(self) -> list[str]:
        return [self.commander.name] + [entry.card.name for entry in self.cards]


@dataclass(frozen=True)
class ComboPackage:
    name: str
    components: tuple[str, ...]
    result: str
    tutors: tuple[str, ...] = ()
    protection: tuple[str, ...] = ()
    payoffs: tuple[str, ...] = ()
    notes: str = ""
    source: str = "public"
    rules_logic: tuple[str, ...] = ()
