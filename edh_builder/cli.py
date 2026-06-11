from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .combo_importer import import_public_combo_export, import_spellbook_variants, sync_local_combos, sync_spellbook_variants
from .db import init_db
from .deck_builder import EdhDeckBuilder
from .exporters import to_grouped_markdown, to_plain_text
from .models import BuildRequest
from .repository import CardRepository
from .repository import ComboRepository
from .scryfall import import_oracle_cards, sync_oracle_cards


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="edh-builder")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db")
    sub.add_parser("sync-scryfall")
    import_scryfall = sub.add_parser("import-scryfall-file")
    import_scryfall.add_argument("path")
    sub.add_parser("sync-combos")
    sync_spellbook = sub.add_parser("sync-spellbook")
    sync_spellbook.add_argument("--path", default=None)
    import_spellbook = sub.add_parser("import-spellbook-file")
    import_spellbook.add_argument("path")

    import_combos = sub.add_parser("import-combos")
    import_combos.add_argument("path")

    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=20)
    combo_search = sub.add_parser("search-combos")
    combo_search.add_argument("--identity", default="")
    combo_search.add_argument("--theme", default="")
    combo_search.add_argument("--limit", type=int, default=10)
    estimate = sub.add_parser("estimate-deck")
    estimate.add_argument("path")

    build = sub.add_parser("build")
    build.add_argument("--commander", required=True)
    build.add_argument("--theme", default="")
    build.add_argument("--budget", type=float)
    build.add_argument("--power-level", type=int, default=6)
    build.add_argument("--no-infinite", action="store_true")
    build.add_argument("--must-include", action="append", default=[])
    build.add_argument("--avoid", action="append", default=[])
    build.add_argument("--format", choices=["markdown", "decklist"], default="markdown")

    args = parser.parse_args()
    if args.command == "init-db":
        init_db()
        print("Initialized database.")
    elif args.command == "sync-scryfall":
        print(f"Imported {sync_oracle_cards()} Scryfall oracle cards.")
    elif args.command == "import-scryfall-file":
        print(f"Imported {import_oracle_cards(Path(args.path))} Scryfall oracle cards.")
    elif args.command == "sync-combos":
        print(f"Imported {sync_local_combos()} local combos.")
    elif args.command == "sync-spellbook":
        path = Path(args.path) if args.path else None
        print(f"Imported {sync_spellbook_variants(path)} Commander Spellbook combos.")
    elif args.command == "import-spellbook-file":
        print(f"Imported {import_spellbook_variants(Path(args.path))} Commander Spellbook combos.")
    elif args.command == "import-combos":
        print(f"Imported {import_public_combo_export(Path(args.path))} combos.")
    elif args.command == "search":
        for card in CardRepository().search(args.query, args.limit):
            status = "commander" if card.can_be_commander else "card"
            legality = "legal" if card.legal_commander else "not legal"
            print(f"{card.name} [{status}, {legality}] {card.type_line}")
    elif args.command == "search-combos":
        combos = ComboRepository().relevant_for(set(args.identity), args.theme, args.limit)
        for combo in combos:
            print(combo.name)
            print("  Cards: " + ", ".join(combo.cards))
            print("  Result: " + combo.result)
            print("  Tags: " + ", ".join(combo.tags[:8]))
    elif args.command == "estimate-deck":
        repo = CardRepository()
        total = 0.0
        missing = []
        for line in Path(args.path).read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            _, name = line.split(" ", 1)
            card = repo.get_by_name(name.strip())
            if card and card.price_usd is not None:
                total += card.price_usd
            else:
                missing.append(name.strip())
        print(f"Known USD total: {total:.2f}")
        if missing:
            print("Missing prices:")
            for name in missing:
                print(f"- {name}")
    elif args.command == "build":
        request = BuildRequest(
            commander=args.commander,
            theme=args.theme,
            budget=args.budget,
            power_level=args.power_level,
            allow_infinite=not args.no_infinite,
            must_include=args.must_include,
            avoid=args.avoid,
        )
        deck, errors, plan = EdhDeckBuilder().build(request)
        print(to_plain_text(deck) if args.format == "decklist" else to_grouped_markdown(deck, errors, plan))


if __name__ == "__main__":
    main()
