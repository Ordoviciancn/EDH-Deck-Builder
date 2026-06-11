from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from .models import BuildRequest, Card, Combo
from .rules_knowledge import rules_context_for


def propose_plan(request: BuildRequest, commander: Card, combos: list[Combo]) -> dict:
    if not OPENAI_API_KEY:
        return fallback_plan(request, commander, combos)

    combo_lines = [
        {"name": combo.name, "cards": list(combo.cards), "result": combo.result, "tags": list(combo.tags)}
        for combo in combos[:30]
    ]
    prompt = {
        "task": "Create an EDH deck construction plan. Return strict JSON.",
        "rules_context": rules_context_for(request, commander),
        "commander": commander.name,
        "commander_text": commander.oracle_text,
        "theme": request.theme,
        "budget": request.budget,
        "power_level": request.power_level,
        "allow_infinite": request.allow_infinite,
        "combo_preference": request.combo_preference,
        "meta_profile": request.meta_profile,
        "meta_notes": request.meta_notes,
        "must_include": request.must_include,
        "avoid": request.avoid,
        "available_combo_context": combo_lines,
        "json_schema": {
            "strategy": "string",
            "desired_tags": ["string"],
            "combo_cards": ["string"],
            "avoid_cards": ["string"],
            "role_weights": {"ramp": 1.0, "draw": 1.0}
        },
    }
    body = json.dumps(
        {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert Magic: The Gathering Commander deckbuilding agent. "
                        "Use the supplied rules_context as authoritative planning guidance. "
                        "Do not invent rules, do not include off-color or banned cards, and output only valid JSON."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "temperature": 0.3,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request_obj = urllib.request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except (urllib.error.URLError, KeyError, json.JSONDecodeError):
        return fallback_plan(request, commander, combos)


def fallback_plan(request: BuildRequest, commander: Card, combos: list[Combo]) -> dict:
    text = f"{request.theme} {commander.oracle_text}".lower()
    desired_tags: list[str] = []
    for tag in [
        "graveyard",
        "sacrifice",
        "tokens",
        "aristocrats",
        "blink",
        "spell_slinger",
        "combo_piece",
        "wincon",
    ]:
        normalized = tag.replace("_", " ")
        if tag in text or normalized in text:
            desired_tags.append(tag)
    if not desired_tags:
        desired_tags = ["synergy", "draw", "ramp"]

    combo_cards: list[str] = []
    if request.allow_infinite:
        for combo in combos:
            if any(tag in desired_tags for tag in combo.tags) or any(card == commander.name for card in combo.cards):
                combo_cards.extend(combo.cards)
                if len(combo_cards) >= 8:
                    break

    return {
        "strategy": request.theme or f"Synergy plan around {commander.name}",
        "desired_tags": desired_tags,
        "combo_cards": list(dict.fromkeys(combo_cards)),
        "avoid_cards": request.avoid,
        "role_weights": {},
    }
