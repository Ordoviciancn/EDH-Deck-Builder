from __future__ import annotations

import json
from pathlib import Path
import urllib.request

from .config import DATA_DIR
from .db import init_db
from .models import Combo
from .repository import ComboRepository


SPELLBOOK_VARIANTS_URL = "https://json.commanderspellbook.com/variants.json"
SPELLBOOK_SOURCE = "commander-spellbook"


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


def download_spellbook_variants(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        SPELLBOOK_VARIANTS_URL,
        headers={"User-Agent": "edh-builder-agent/0.1", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=900) as response, path.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    return path


def import_spellbook_variants(path: Path, commander_only: bool = True, status: str = "OK") -> int:
    init_db()
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    variants = payload.get("variants", [])
    combos: list[Combo] = []
    for variant in variants:
        if status and variant.get("status") != status:
            continue
        if commander_only and not (variant.get("legalities") or {}).get("commander"):
            continue
        cards = tuple(
            use.get("card", {}).get("name", "")
            for use in variant.get("uses", [])
            if use.get("card", {}).get("name")
        )
        if not cards:
            continue
        produces = [
            item.get("feature", {}).get("name", "")
            for item in variant.get("produces", [])
            if item.get("feature", {}).get("name")
        ]
        identity = variant.get("identity") or ""
        tags = [tag for tag in produces if tag]
        if identity:
            tags.append(f"identity:{identity}")
        bracket = variant.get("bracketTag")
        if bracket:
            tags.append(f"bracket:{bracket}")
        result = "; ".join(produces) or variant.get("description", "")
        combo_id = variant.get("id", "unknown")
        name = f"Spellbook {combo_id}: " + " + ".join(cards)
        combos.append(
            Combo(
                name=name,
                cards=cards,
                result=result,
                source=SPELLBOOK_SOURCE,
                tags=tuple(tags),
            )
        )
    return ComboRepository().replace_source(SPELLBOOK_SOURCE, combos)


def sync_spellbook_variants(path: Path | None = None) -> int:
    target = path or DATA_DIR.parent / ".cache" / "spellbook-variants.json"
    if not target.exists():
        download_spellbook_variants(target)
    return import_spellbook_variants(target)
