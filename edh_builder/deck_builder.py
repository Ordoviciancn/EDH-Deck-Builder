from __future__ import annotations

from collections import Counter
import math

from .llm_agent import propose_plan
from .models import BuildRequest, Card, Deck, DeckCard
from .repository import CardRepository, ComboRepository
from .rules import BASIC_LAND_NAMES, validate_deck
from .tagger import load_staples, load_tag_rules, tag_card


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
        self.staples = load_staples()
        self.active_budget: float | None = None

    def build(self, request: BuildRequest) -> tuple[Deck, list[str], dict]:
        self.active_budget = request.budget
        commander = self.cards.get_by_name(request.commander)
        if not commander:
            raise DeckBuildError(f"Commander not found: {request.commander}. Run sync-scryfall first.")
        pool = self.cards.legal_pool(commander.color_identity, request.budget)
        if not pool:
            raise DeckBuildError("Legal card pool is empty. Run sync-scryfall first.")

        combos = self.combos.relevant_for(commander.color_identity, request.theme)
        plan = propose_plan(request, commander, combos)
        desired_tags = set(plan.get("desired_tags") or [])
        avoid_cards = {name.lower() for name in plan.get("avoid_cards", [])}
        public_combo_cards = self._best_public_combo_cards(combos, commander, request)
        must_include = list(dict.fromkeys(request.must_include + plan.get("combo_cards", []) + public_combo_cards))

        selected: list[DeckCard] = []
        selected_names = {commander.name}

        for name in must_include:
            card = self.cards.get_by_name(name)
            if card and self._budget_card_allowed(card, request.budget) and self._can_add(card, commander, selected_names, avoid_cards):
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
        candidates = self._preselect_candidates(candidates, commander, selected, role, desired_tags)
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
        if not self._is_playable_card(card):
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
        card_text = f"{card.name} {card.type_line} {card.oracle_text}".lower()
        score = 0.0
        score += self._edh_quality_score(card)
        score += self._role_fit_score(card, role, tags)
        score += self._staple_score(card, role)
        score += self._theme_score(card, desired_tags, tags)
        score += self._commander_synergy_score(card, commander)
        if role == "lands":
            score += self._land_score(card, commander)
            if card.name in BASIC_LAND_NAMES:
                same_basic_count = sum(1 for entry in selected if entry.card.name == card.name)
                score -= same_basic_count * 4

        if card.price_usd is not None:
            score -= min(card.price_usd, 80) * 0.08
            spent = sum(entry.card.price_usd or 0 for entry in selected)
            if self.active_budget and self.active_budget <= 150:
                score -= card.price_usd * 1.4
                if card.price_usd > self.active_budget * 0.1:
                    score -= 18
                slots_left = max(1, 99 - len(selected))
                per_slot_remaining = max(0.25, (self.active_budget - spent) / slots_left)
                if card.price_usd > per_slot_remaining * 5:
                    score -= 20
            else:
                average_spend = spent / max(1, len(selected))
                if average_spend > 1.0:
                    score -= card.price_usd * min(2.5, average_spend / 8)
        elif self.active_budget and self.active_budget <= 150 and not card.is_basic_land:
            score -= 6
        if role in {"ramp", "removal", "protection", "tutor"}:
            score += max(0, 5 - card.cmc) * 2
        elif role in {"wincon", "synergy"} and "cascade" in f"{commander.oracle_text} {card.oracle_text}".lower():
            score += min(card.cmc, 8) * 1.4
        elif card.cmc <= 3:
            score += 2

        current_roles = Counter(entry.role for entry in selected)
        score -= current_roles[role] * 0.25
        return score

    @staticmethod
    def _role_count(selected: list[DeckCard], role: str) -> int:
        return sum(1 for entry in selected if entry.role == role)

    def _preselect_candidates(
        self,
        candidates: list[Card],
        commander: Card,
        selected: list[DeckCard],
        role: str,
        desired_tags: set[str],
    ) -> list[Card]:
        if role == "lands":
            return [card for card in candidates if card.is_land]
        tagged = []
        for card in candidates:
            tags = tag_card(card, self.tag_rules)
            if role in tags or card.name in self.staples.get(role, []) or tags & desired_tags:
                tagged.append(card)
        if not tagged:
            tagged = candidates
        return sorted(
            tagged,
            key=lambda card: self._score(card, commander, selected, role, desired_tags),
            reverse=True,
        )[:900]

    def _is_playable_card(self, card: Card) -> bool:
        if card.digital or "paper" not in card.games:
            return False
        if card.border_color not in {"", "black", "borderless"}:
            return False
        if card.layout in {"art_series", "token", "double_faced_token", "planar", "scheme", "vanguard"}:
            return False
        if "Sticker" in card.type_line or "Attraction" in card.type_line:
            return False
        return True

    def _edh_quality_score(self, card: Card) -> float:
        if card.edhrec_rank is None:
            return -18
        rank = card.edhrec_rank
        if rank <= 100:
            return 42
        if rank <= 500:
            return 34
        if rank <= 1500:
            return 26
        if rank <= 4000:
            return 17
        if rank <= 8000:
            return 9
        if rank <= 14000:
            return 2
        return -10

    def _role_fit_score(self, card: Card, role: str, tags: set[str]) -> float:
        text = f"{card.name} {card.type_line} {card.oracle_text}".lower()
        score = 0.0
        if role in tags:
            score += 20
        if role == "ramp":
            if card.name in self.staples["ramp"]:
                score += 18
            if "search your library" in text and "land card" in text and "battlefield" in text:
                score += 15
            if "{t}: add" in text or "add one mana" in text or "add {c}{c}" in text:
                score += 10
            if "sacrifice" in text and "add one mana" in text:
                score -= 12
        elif role == "draw":
            if "draw a card" in text or "draw cards" in text:
                score += 12
            if card.cmc >= 5 and "draw a card" in text and "enters" in text:
                score -= 5
        elif role == "removal":
            if any(phrase in text for phrase in ["destroy target", "exile target", "counter target", "return target"]):
                score += 15
            if card.cmc <= 3:
                score += 8
        elif role == "wipe":
            if any(phrase in text for phrase in ["destroy all", "exile all", "return all", "each creature"]):
                score += 18
        elif role == "protection":
            if any(phrase in text for phrase in ["hexproof", "indestructible", "phase out", "can't be countered", "counter target"]):
                score += 13
        elif role == "tutor":
            if "search your library" in text:
                score += 16
            if "transmute" in text:
                score += 12
        elif role == "combo_piece":
            if card.name in self.staples["combo_piece"]:
                score += 25
            if any(phrase in text for phrase in ["untap", "copy", "storm", "magecraft"]):
                score += 8
        elif role == "wincon":
            if card.name in self.staples["wincon"]:
                score += 20
            if any(phrase in text for phrase in ["you win the game", "each opponent loses", "storm", "cascade"]):
                score += 14
        return score

    def _staple_score(self, card: Card, role: str) -> float:
        score = 0.0
        for staple_role, names in self.staples.items():
            if card.name in names:
                score += 25 if staple_role == role else 7
        return score

    def _theme_score(self, card: Card, desired_tags: set[str], tags: set[str]) -> float:
        text = f"{card.name} {card.type_line} {card.oracle_text}".lower()
        score = 10 * len(tags & desired_tags)
        for token in desired_tags:
            if token.replace("_", " ") in text:
                score += 8
        return score

    def _commander_synergy_score(self, card: Card, commander: Card) -> float:
        commander_text = commander.oracle_text.lower()
        card_text = f"{card.type_line} {card.oracle_text}".lower()
        score = 0.0
        if "cascade" in commander_text:
            if "cascade" in card_text:
                score += 24
            if "instant" in card.type_line or "sorcery" in card.type_line:
                score += 4
                if card.cmc >= 5:
                    score += 10
            if "delve" in card_text:
                score += 16
            if "storm" in card_text:
                score += 12
        for word in commander_text.split():
            if len(word) > 6 and word in card_text:
                score += 0.5
        return score

    def _land_score(self, card: Card, commander: Card) -> float:
        text = card.oracle_text.lower()
        score = 0.0
        if card.name in self.staples["lands"]:
            score += 30
        if card.name in BASIC_LAND_NAMES:
            score += 18
        if "add one mana of any color" in text:
            score += 16
        if len(card.color_identity & commander.color_identity) >= 2:
            score += 10
        if "enters tapped" in text:
            score -= 4
        if not card.color_identity and card.name not in {"Command Tower", "Exotic Orchard", "Reliquary Tower", "Myriad Landscape"}:
            score -= 8
        return score

    def _best_public_combo_cards(self, combos: list, commander: Card, request: BuildRequest) -> list[str]:
        if not request.allow_infinite:
            return []
        theme = request.theme.lower()
        if not any(term in theme for term in ["combo", "storm", "infinite", "mana"]):
            return []
        for combo in combos[:50]:
            if len(combo.cards) > 3:
                continue
            cards = [self.cards.get_by_name(name) for name in combo.cards]
            known_price = sum(card.price_usd or 0 for card in cards if card is not None)
            if request.budget and known_price > request.budget * 0.35:
                continue
            if all(
                card
                and self._budget_card_allowed(card, request.budget)
                and self._can_add(card, commander, set(), set())
                for card in cards
            ):
                return [card.name for card in cards if card is not None]
        return []

    @staticmethod
    def _budget_card_allowed(card: Card, budget: float | None) -> bool:
        if budget is None or card.price_usd is None:
            return True
        if budget <= 60:
            return card.price_usd <= max(5.0, budget * 0.12)
        if budget <= 150:
            return card.price_usd <= max(10.0, budget * 0.18)
        if budget <= 500:
            return card.price_usd <= budget * 0.22
        return card.price_usd <= budget
