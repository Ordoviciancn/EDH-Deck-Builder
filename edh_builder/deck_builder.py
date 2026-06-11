from __future__ import annotations

from collections import Counter

from .llm_agent import propose_plan
from .models import BuildRequest, Card, Deck, DeckCard
from .repository import CardRepository, ComboRepository
from .rules import BASIC_LAND_NAMES, validate_deck
from .tagger import load_tag_rules, tag_card


ROLE_TARGETS = {
    "lands": 37,
    "ramp": 11,
    "draw": 11,
    "removal": 9,
    "wipe": 3,
    "protection": 3,
    "tutor": 2,
    "combo_piece": 4,
    "wincon": 5,
    "synergy": 14,
    "flex": 0,
}


class DeckBuildError(RuntimeError):
    pass


class EdhDeckBuilder:
    def __init__(self) -> None:
        self.cards = CardRepository()
        self.combos = ComboRepository()
        self.tag_rules = load_tag_rules()

    def build(self, request: BuildRequest) -> tuple[Deck, list[str], dict]:
        commander = self.cards.get_by_name(request.commander)
        if not commander:
            raise DeckBuildError(f"Commander not found: {request.commander}. Run sync-scryfall first.")
        pool = self.cards.legal_pool(commander.color_identity, request.budget)
        if not pool:
            raise DeckBuildError("Legal card pool is empty. Run sync-scryfall first.")

        combos = self.combos.list_all()
        plan = propose_plan(request, commander, combos)
        desired_tags = set(plan.get("desired_tags") or [])
        avoid_cards = {name.lower() for name in plan.get("avoid_cards", [])}
        must_include = list(dict.fromkeys(request.must_include + plan.get("combo_cards", [])))

        selected: list[DeckCard] = []
        selected_names = {commander.name}

        for name in must_include:
            card = self.cards.get_by_name(name)
            if card and self._can_add(card, commander, selected_names, avoid_cards):
                selected.append(DeckCard(card=card, role="combo_piece", score=100, reason="Must include or combo plan."))
                selected_names.add(card.name)

        for role, target in ROLE_TARGETS.items():
            while self._role_count(selected, role) < target and len(selected) < 99:
                card = self._best_candidate(pool, commander, selected, selected_names, role, desired_tags, avoid_cards)
                if not card:
                    break
                selected.append(
                    DeckCard(
                        card=card,
                        role=role,
                        score=self._score(card, commander, selected, role, desired_tags),
                        reason=f"Selected for {role}.",
                    )
                )
                selected_names.add(card.name)

        while len(selected) < 99:
            card = self._best_candidate(pool, commander, selected, selected_names, "synergy", desired_tags, avoid_cards)
            if not card:
                break
            selected.append(DeckCard(card=card, role="flex", score=0, reason="Fills remaining deck slot."))
            selected_names.add(card.name)

        deck = Deck(commander=commander, cards=selected[:99])
        return deck, validate_deck(deck), plan

    def _best_candidate(
        self,
        pool: list[Card],
        commander: Card,
        selected: list[DeckCard],
        selected_names: set[str],
        role: str,
        desired_tags: set[str],
        avoid_cards: set[str],
    ) -> Card | None:
        candidates = [
            card for card in pool if self._can_add(card, commander, selected_names, avoid_cards)
        ]
        if role == "lands":
            candidates = [card for card in candidates if card.is_land]
        else:
            candidates = [card for card in candidates if not card.is_land]
        if not candidates:
            return None
        return max(candidates, key=lambda card: self._score(card, commander, selected, role, desired_tags))

    def _can_add(
        self,
        card: Card,
        commander: Card,
        selected_names: set[str],
        avoid_cards: set[str],
    ) -> bool:
        if card.name.lower() in avoid_cards:
            return False
        if not card.color_identity.issubset(commander.color_identity):
            return False
        if card.banned_commander or not card.legal_commander:
            return False
        if card.name in selected_names and card.name not in BASIC_LAND_NAMES:
            return False
        return True

    def _score(
        self,
        card: Card,
        commander: Card,
        selected: list[DeckCard],
        role: str,
        desired_tags: set[str],
    ) -> float:
        tags = tag_card(card, self.tag_rules)
        commander_text = commander.oracle_text.lower()
        card_text = f"{card.name} {card.type_line} {card.oracle_text}".lower()
        score = 0.0
        if role in tags:
            score += 35
        score += 12 * len(tags & desired_tags)
        for token in desired_tags:
            if token.replace("_", " ") in card_text:
                score += 8
        for word in commander_text.split():
            if len(word) > 5 and word in card_text:
                score += 0.4
        if card.price_usd is not None:
            score -= min(card.price_usd, 50) * 0.03
        if card.cmc <= 3:
            score += 4
        elif card.cmc >= 6:
            score -= 3
        current_roles = Counter(entry.role for entry in selected)
        score -= current_roles[role] * 0.15
        return score

    @staticmethod
    def _role_count(selected: list[DeckCard], role: str) -> int:
        return sum(1 for entry in selected if entry.role == role)
