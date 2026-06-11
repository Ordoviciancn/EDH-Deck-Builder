import unittest

from edh_builder.models import Card, Deck, DeckCard
from edh_builder.rules import validate_deck


def card(name: str, identity: set[str] | None = None, legal: bool = True, commander: bool = False) -> Card:
    return Card(
        oracle_id=name,
        name=name,
        mana_cost="",
        cmc=1,
        colors=identity or set(),
        color_identity=identity or set(),
        type_line="Legendary Creature" if commander else "Creature",
        oracle_text="",
        legal_commander=legal,
        banned_commander=not legal,
        can_be_commander=commander,
    )


class TestRules(unittest.TestCase):
    def test_rejects_off_color_card(self) -> None:
        commander = card("Mono Blue Legend", {"U"}, commander=True)
        entries = [DeckCard(card(f"Blue {i}", {"U"}), "synergy", 1) for i in range(98)]
        entries.append(DeckCard(card("Red Card", {"R"}), "synergy", 1))
        errors = validate_deck(Deck(commander, entries))
        self.assertTrue(any("color identity" in error for error in errors))

    def test_rejects_non_singleton(self) -> None:
        commander = card("Mono Blue Legend", {"U"}, commander=True)
        entries = [DeckCard(card(f"Blue {i}", {"U"}), "synergy", 1) for i in range(97)]
        duplicate = card("Duplicate", {"U"})
        entries.extend([DeckCard(duplicate, "synergy", 1), DeckCard(duplicate, "synergy", 1)])
        errors = validate_deck(Deck(commander, entries))
        self.assertTrue(any("singleton" in error for error in errors))
