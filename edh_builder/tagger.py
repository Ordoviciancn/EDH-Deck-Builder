from __future__ import annotations

import json

from .config import DATA_DIR
from .models import Card


def load_tag_rules() -> dict[str, list[str]]:
    path = DATA_DIR / "tag_rules.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_staples() -> dict[str, list[str]]:
    path = DATA_DIR / "edh_staples.json"
    return json.loads(path.read_text(encoding="utf-8"))


def tag_card(card: Card, rules: dict[str, list[str]] | None = None) -> set[str]:
    rules = rules or load_tag_rules()
    haystack = f"{card.name}\n{card.type_line}\n{card.oracle_text}".lower()
    tags = {tag for tag, needles in rules.items() if any(needle.lower() in haystack for needle in needles)}
    if card.is_land:
        tags.add("lands")
    return tags
