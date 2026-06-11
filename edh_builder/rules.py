from __future__ import annotations

from collections import Counter

from .models import Card, Deck


BASIC_LAND_NAMES = {
    "Plains",
    "Island",
    "Swamp",
    "Mountain",
    "Forest",
    "Wastes",
}


def is_color_identity_legal(card: Card, commander_identity: set[str]) -> bool:
    return card.color_identity.issubset(commander_identity)


def validate_deck(deck: Deck) -> list[str]:
    errors: list[str] = []
    all_cards = [deck.commander] + [entry.card for entry in deck.cards]
    if len(all_cards) != 100:
        errors.append(f"Deck must contain exactly 100 cards including commander; got {len(all_cards)}.")
    if not deck.commander.can_be_commander:
        errors.append(f"{deck.commander.name} is not marked as a legal commander candidate.")
    if deck.commander.banned_commander or not deck.commander.legal_commander:
        errors.append(f"{deck.commander.name} is not legal in Commander.")

    counts = Counter(card.name for card in all_cards)
    for name, count in counts.items():
        if count > 1 and name not in BASIC_LAND_NAMES:
            errors.append(f"{name} appears {count} times; EDH is singleton except basic lands.")

    commander_identity = deck.commander.color_identity
    for card in all_cards:
        if card.banned_commander or not card.legal_commander:
            errors.append(f"{card.name} is not legal in Commander.")
        if not is_color_identity_legal(card, commander_identity):
            errors.append(
                f"{card.name} color identity {sorted(card.color_identity)} exceeds commander identity {sorted(commander_identity)}."
            )
    return errors
