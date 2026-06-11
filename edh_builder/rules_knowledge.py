from __future__ import annotations

from functools import lru_cache

from .config import DATA_DIR
from .models import BuildRequest, Card


MAX_RULES_CONTEXT_CHARS = 9000


@lru_cache(maxsize=1)
def load_rules_knowledge() -> str:
    path = DATA_DIR / "rules_knowledge.md"
    return path.read_text(encoding="utf-8")


def rules_context_for(request: BuildRequest, commander: Card) -> str:
    """Return a compact rules context for LLM planning.

    The full file is intentionally human-readable. This function trims it to
    sections that matter for the current request so prompts stay manageable.
    """
    text = load_rules_knowledge()
    wanted = {
        "MTG / Commander Rules Knowledge for Deckbuilding Agents",
        "Commander / EDH Deck Construction",
        "Commander Game Context",
        "Casting Spells, Free Casting, and Copies",
        "Combo Validation Principles",
        "Common EDH Interaction Categories",
        "Meta-Aware Deckbuilding",
        "LLM Guardrails",
    }
    haystack = f"{request.theme} {request.combo_preference} {request.meta_profile} {commander.name} {commander.oracle_text}".lower()
    if "cascade" in haystack:
        wanted.add("Cascade")
    if "quandrix, the proof" in commander.name.lower():
        wanted.add("Quandrix, the Proof Notes")

    sections = _split_sections(text)
    selected = [sections[name] for name in sections if name in wanted]
    compact = "\n\n".join(selected)
    if len(compact) > MAX_RULES_CONTEXT_CHARS:
        compact = compact[:MAX_RULES_CONTEXT_CHARS] + "\n\n[Rules context truncated.]"
    return compact


def _split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "MTG / Commander Rules Knowledge for Deckbuilding Agents"
    sections[current] = []
    for line in text.splitlines():
        if line.startswith("# "):
            current = line[2:].strip()
            sections.setdefault(current, [line])
        elif line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [line])
        else:
            sections.setdefault(current, []).append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}
