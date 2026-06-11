from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .combo_importer import import_public_combo_export, sync_local_combos
from .db import init_db
from .deck_builder import EdhDeckBuilder
from .exporters import to_grouped_markdown, to_plain_text
from .models import BuildRequest
from .repository import CardRepository
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

    import_combos = sub.add_parser("import-combos")
    import_combos.add_argument("path")

    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=20)

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
    elif args.command == "import-combos":
        print(f"Imported {import_public_combo_export(Path(args.path))} combos.")
    elif args.command == "search":
        for card in CardRepository().search(args.query, args.limit):
            status = "commander" if card.can_be_commander else "card"
            legality = "legal" if card.legal_commander else "not legal"
            print(f"{card.name} [{status}, {legality}] {card.type_line}")
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
