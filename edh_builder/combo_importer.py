from __future__ import annotations

import json
from pathlib import Path

from .config import DATA_DIR
from .db import init_db
from .models import Combo
from .repository import ComboRepository


def load_jsonl(path: Path) -> list[Combo]:
    combos: list[Combo] = []
    if not path.exists():
        return combos
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        combos.append(
            Combo(
                name=item["name"],
                cards=tuple(item["cards"]),
                result=item.get("result", ""),
                source=item.get("source", "custom"),
                tags=tuple(item.get("tags", [])),
            )
        )
    return combos


def sync_local_combos(path: Path | None = None) -> int:
    init_db()
    combos = load_jsonl(path or DATA_DIR / "custom_combos.jsonl")
    return ComboRepository().upsert_many(combos)


def import_public_combo_export(path: Path) -> int:
    """Import a normalized public combo JSONL export.

    Commander Spellbook is the intended public source, but their API/export
    shape can change. Keep this boundary normalized so a later connector only
    has to write JSONL records with name/cards/result/source/tags.
    """
    init_db()
    combos = load_jsonl(path)
    return ComboRepository().upsert_many(combos)
