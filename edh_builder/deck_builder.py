from __future__ import annotations

from collections import Counter

from .llm_agent import propose_plan
from .models import BuildRequest, Card, Combo, ComboPackage, Deck, DeckCard
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
        self.active_meta_profile = "balanced"
        self.active_meta_notes = ""

    def build(self, request: BuildRequest) -> tuple[Deck, list[str], dict]:
        self.active_budget = request.budget
        self.active_meta_profile = request.meta_profile
        self.active_meta_notes = request.meta_notes
        commander = self.cards.get_by_name(request.commander)
        if not commander:
            raise DeckBuildError(f"Commander not found: {request.commander}. Run sync-scryfall first.")
        pool = self.cards.legal_pool(commander.color_identity, request.budget)
        if not pool:
            raise DeckBuildError("Legal card pool is empty. Run sync-scryfall first.")

        context_theme = " ".join([request.theme, request.meta_profile, request.meta_notes, request.combo_preference])
        combos = self.combos.relevant_for(commander.color_identity, context_theme)
        plan = propose_plan(request, commander, combos)
        combo_package = self._build_combo_package(combos, commander, request)
        plan["combo_package"] = self._combo_package_dict(combo_package) if combo_package else None
        plan["meta_profile"] = request.meta_profile
        plan["meta_notes"] = request.meta_notes
        desired_tags = set(plan.get("desired_tags") or []) | self._meta_desired_tags(request)
        avoid_cards = {name.lower() for name in plan.get("avoid_cards", [])}
        package_cards = self._combo_package_cards(combo_package, request) if combo_package else []
        must_include = list(dict.fromkeys(request.must_include + plan.get("combo_cards", []) + package_cards))

        selected: list[DeckCard] = []
        selected_names = {commander.name}

        for name in must_include:
            card = self.cards.get_by_name(name)
            if card and self._budget_card_allowed(card, request.budget) and self._can_add(card, commander, selected_names, avoid_cards):
                selected.append(DeckCard(card=card, role="combo_piece", score=100, reason="Must include or combo plan."))
                selected_names.add(card.name)

        for role, target in self._role_targets(request).items():
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
        score += self._meta_score(card, self.active_meta_profile, self.active_meta_notes)
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

    def _role_targets(self, request: BuildRequest) -> dict[str, int]:
        targets = dict(ROLE_TARGETS)
        if request.combo_preference == "none" or not request.allow_infinite:
            targets["combo_piece"] = 0
            targets["protection"] += 1
            targets["synergy"] += 3
        elif request.combo_preference == "light":
            targets["combo_piece"] = 2
            targets["tutor"] = max(targets["tutor"], 2)
        elif request.combo_preference == "focused":
            targets["combo_piece"] = 7
            targets["tutor"] = max(targets["tutor"], 4)
            targets["protection"] += 1

        profile = request.meta_profile
        notes = request.meta_notes.lower()
        if profile == "creature" or "快攻" in notes or "生物" in notes:
            targets["wipe"] += 1
            targets["removal"] += 1
        if profile == "combo" or "combo" in notes or "组合技" in notes:
            targets["removal"] += 1
            targets["protection"] += 1
        if profile == "control" or "蓝控" in notes or "反击" in notes:
            targets["draw"] += 1
            targets["protection"] += 1
        if profile == "graveyard" or "坟场" in notes or "墓地" in notes:
            targets["removal"] += 1
            targets["synergy"] += 1
        if profile == "artifact" or "神器" in notes or "结界" in notes:
            targets["removal"] += 2
        if profile == "stax" or "锁" in notes or "stax" in notes:
            targets["removal"] += 1
            targets["ramp"] += 1

        non_land_total = sum(value for key, value in targets.items() if key != "lands")
        overflow = max(0, targets["lands"] + non_land_total - 99)
        for role in ["synergy", "draw", "wincon", "ramp"]:
            if overflow <= 0:
                break
            cut = min(overflow, max(0, targets[role] - 1))
            targets[role] -= cut
            overflow -= cut
        return targets

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
            if (
                (role in tags and role not in {"draw", "wipe", "tutor", "protection"})
                or card.name in self.staples.get(role, [])
                or self._role_fit_score(card, role, tags) >= 10
                or (role in {"synergy", "combo_piece", "wincon"} and tags & desired_tags)
            ):
                tagged.append(card)
        if not tagged and role in {"synergy", "flex"}:
            tagged = candidates
        if not tagged:
            return []
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
        if role in tags and role not in {"draw", "wipe", "tutor", "protection"}:
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
            if "draw cards" in text or "draw two cards" in text or "draw three cards" in text:
                score += 14
            if "whenever" in text and "draw" in text:
                score += 12
            if card.name in {"Consider", "Preordain", "Ponder", "Brainstorm", "Frantic Search", "Fact or Fiction"}:
                score += 12
            if "draw a card" in text:
                score += 4
            if any(term in text for term in ["exile target card from a graveyard", "exile all graveyards", "graveyard"]):
                score -= 10
            if card.cmc >= 5 and "draw a card" in text and "enters" in text:
                score -= 8
        elif role == "removal":
            if any(phrase in text for phrase in ["destroy target", "exile target", "counter target", "return target"]):
                score += 15
            if card.cmc <= 3:
                score += 8
        elif role == "wipe":
            if "graveyard" in text and not any(term in text for term in ["creature", "permanent", "artifact", "enchantment"]):
                score -= 30
            elif "those creatures" in text or "creatures you control" in text:
                score -= 30
            elif any(phrase in text for phrase in ["destroy all", "exile all creatures", "exile all nonland", "return all creatures", "return each creature"]):
                score += 18
            elif any(phrase in text for phrase in ["each creature gets -", "each creature deals", "damage to each creature", "-x/-x until end of turn"]):
                score += 14
            else:
                score -= 30
        elif role == "protection":
            if any(phrase in text for phrase in ["hexproof", "indestructible", "phase out", "can't be countered", "counter target"]):
                score += 13
        elif role == "tutor":
            if "named " in text:
                score -= 18
            if "search your library" in text and not any(term in text for term in ["basic land", "land card", "desert card", "forest card", "island card"]):
                score += 16
            if "transmute" in text:
                score += 12
            if any(term in text for term in ["basic land", "land card", "desert card", "forest card", "island card"]):
                score -= 16
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
        if "{t}: add {u}" in text or "{t}: add {g}" in text or "{t}: add one mana" in text:
            score += 8
        if len(card.color_identity & commander.color_identity) >= 2:
            score += 10
        if "enters tapped" in text:
            score -= 4
        if not card.color_identity and card.name not in {"Command Tower", "Exotic Orchard", "Reliquary Tower", "Myriad Landscape"}:
            score -= 8
        if not any(phrase in text for phrase in ["add {u}", "add {g}", "mana of any color", "add one mana"]) and card.name not in self.staples["lands"]:
            score -= 18
        return score

    def _meta_desired_tags(self, request: BuildRequest) -> set[str]:
        tags: set[str] = set()
        text = f"{request.meta_profile} {request.meta_notes}".lower()
        if any(term in text for term in ["creature", "生物", "快攻"]):
            tags |= {"removal", "wipe"}
        if any(term in text for term in ["combo", "组合技", "storm"]):
            tags |= {"removal", "protection", "tutor"}
        if any(term in text for term in ["control", "蓝控", "反击"]):
            tags |= {"draw", "protection"}
        if any(term in text for term in ["graveyard", "坟场", "墓地"]):
            tags |= {"removal", "graveyard"}
        if any(term in text for term in ["artifact", "神器", "enchantment", "结界"]):
            tags |= {"removal"}
        return tags

    def _meta_score(self, card: Card, profile: str, notes: str) -> float:
        text = f"{card.name} {card.type_line} {card.oracle_text}".lower()
        meta = f"{profile} {notes}".lower()
        score = 0.0
        if any(term in meta for term in ["creature", "生物", "快攻"]):
            if any(term in text for term in ["destroy all creatures", "return all creatures", "each creature", "prevent all combat damage"]):
                score += 12
            if any(term in text for term in ["destroy target creature", "exile target creature"]):
                score += 8
        if any(term in meta for term in ["combo", "组合技", "storm"]):
            if "counter target" in text or "can't be countered" in text:
                score += 10
            if "search your library" in text or "transmute" in text:
                score += 8
        if any(term in meta for term in ["control", "蓝控", "反击"]):
            if "can't be countered" in text or "flash" in text:
                score += 8
            if "draw" in text and card.cmc <= 4:
                score += 5
        if any(term in meta for term in ["graveyard", "坟场", "墓地"]):
            if "exile" in text and "graveyard" in text:
                score += 14
            if "shuffle" in text and "graveyard" in text:
                score += 8
        if any(term in meta for term in ["artifact", "神器", "enchantment", "结界"]):
            if "destroy target artifact" in text or "destroy target enchantment" in text:
                score += 12
            if "artifact or enchantment" in text:
                score += 10
        if any(term in meta for term in ["stax", "锁"]):
            if "destroy target artifact" in text or "destroy target enchantment" in text:
                score += 8
            if card.cmc <= 2 and ("add" in text or "search your library" in text):
                score += 6
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

    def _build_combo_package(
        self,
        combos: list[Combo],
        commander: Card,
        request: BuildRequest,
    ) -> ComboPackage | None:
        if not request.allow_infinite or request.combo_preference == "none":
            return None
        theme = f"{request.theme} {request.combo_preference}".lower()
        best: tuple[float, Combo] | None = None
        for combo in combos[:300]:
            if len(combo.cards) > 3:
                continue
            cards = [self.cards.get_by_name(name) for name in combo.cards]
            if not all(card and self._budget_card_allowed(card, request.budget) and self._can_add(card, commander, set(), set()) for card in cards):
                continue
            price = sum(card.price_usd or 0 for card in cards if card is not None)
            if request.budget and price > request.budget * 0.35:
                continue
            haystack = " ".join([combo.name, combo.result, " ".join(combo.tags)]).lower()
            score = 100 - len(combo.cards) * 12 - price
            if "infinite" in haystack:
                score += 18
            if "mana" in haystack:
                score += 12
            if "storm" in haystack:
                score += 12
            if "untap" in haystack:
                score += 8
            if "cascade" in theme and ("storm" in haystack or "mana" in haystack):
                score += 10
            if request.combo_preference == "focused":
                score += 10
            if best is None or score > best[0]:
                best = (score, combo)
        if best is None:
            return None
        combo = best[1]
        support = self._combo_support_cards(combo, commander, request)
        return ComboPackage(
            name=combo.name,
            components=combo.cards,
            result=combo.result,
            tutors=tuple(support["tutors"]),
            protection=tuple(support["protection"]),
            payoffs=tuple(support["payoffs"]),
            notes="Selected from Commander Spellbook/custom combo data and expanded with budget-aware support.",
        )

    def _combo_support_cards(self, combo: Combo, commander: Card, request: BuildRequest) -> dict[str, list[str]]:
        component_text = " ".join(combo.cards).lower()
        result_text = combo.result.lower()
        tutor_candidates = ["Muddle the Mixture", "Fabricate", "Solve the Equation", "Long-Term Plans", "Tribute Mage"]
        protection_candidates = ["Counterspell", "Arcane Denial", "Swan Song", "An Offer You Can't Refuse", "Tamiyo's Safekeeping"]
        payoff_candidates = ["Brain Freeze", "Laboratory Maniac", "Aetherflux Reservoir", "Overwhelming Stampede"]
        if "artifact" in component_text or "scepter" in component_text:
            tutor_candidates = ["Fabricate", "Muddle the Mixture", "Tribute Mage"] + tutor_candidates
        if "storm" in result_text:
            payoff_candidates = ["Brain Freeze", "Aetherflux Reservoir"] + payoff_candidates
        if "mana" in result_text:
            payoff_candidates = ["Finale of Devastation", "Blue Sun's Zenith", "Walking Ballista", "Brain Freeze"] + payoff_candidates
        return {
            "tutors": self._available_support(tutor_candidates, commander, request, 2 if request.combo_preference == "focused" else 1),
            "protection": self._available_support(protection_candidates, commander, request, 2 if request.combo_preference == "focused" else 1),
            "payoffs": self._available_support(payoff_candidates, commander, request, 1),
        }

    def _available_support(
        self,
        names: list[str],
        commander: Card,
        request: BuildRequest,
        limit: int,
    ) -> list[str]:
        picked: list[str] = []
        seen: set[str] = set()
        for name in names:
            if name in seen:
                continue
            seen.add(name)
            card = self.cards.get_by_name(name)
            if card and self._budget_card_allowed(card, request.budget) and self._can_add(card, commander, set(), {avoid.lower() for avoid in request.avoid}):
                picked.append(card.name)
            if len(picked) >= limit:
                break
        return picked

    @staticmethod
    def _combo_package_cards(package: ComboPackage | None, request: BuildRequest) -> list[str]:
        if package is None:
            return []
        cards = list(package.components)
        if request.combo_preference in {"balanced", "focused"}:
            cards.extend(package.tutors)
            cards.extend(package.protection)
            cards.extend(package.payoffs)
        elif request.combo_preference == "light":
            cards.extend(package.payoffs[:1])
        return cards

    @staticmethod
    def _combo_package_dict(package: ComboPackage) -> dict:
        return {
            "name": package.name,
            "components": list(package.components),
            "result": package.result,
            "tutors": list(package.tutors),
            "protection": list(package.protection),
            "payoffs": list(package.payoffs),
            "notes": package.notes,
        }

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
