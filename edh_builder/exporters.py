from __future__ import annotations

from collections import defaultdict

from .models import Deck


def to_plain_text(deck: Deck) -> str:
    lines = [f"Commander", f"1 {deck.commander.name}", "", "Deck"]
    for entry in sorted(deck.cards, key=lambda item: (item.role, item.card.name)):
        lines.append(f"1 {entry.card.name}")
    return "\n".join(lines)


def to_grouped_markdown(deck: Deck, validation_errors: list[str], plan: dict) -> str:
    groups: dict[str, list[str]] = defaultdict(list)
    for entry in deck.cards:
        groups[entry.role].append(entry.card.name)
    lines = [
        f"# {deck.commander.name} EDH Deck",
        "",
        f"Strategy: {plan.get('strategy', '')}",
        "",
        "## Commander",
        f"- 1 {deck.commander.name}",
        "",
    ]
    for role, names in sorted(groups.items()):
        lines.append(f"## {role} ({len(names)})")
        lines.extend(f"- 1 {name}" for name in sorted(names))
        lines.append("")
    lines.append("## Validation")
    if validation_errors:
        lines.extend(f"- ERROR: {error}" for error in validation_errors)
    else:
        lines.append("- Pass")
    return "\n".join(lines)
