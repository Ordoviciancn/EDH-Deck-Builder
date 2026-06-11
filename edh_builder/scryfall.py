from __future__ import annotations

import json
import tempfile
from pathlib import Path
import urllib.request

from .config import SCRYFALL_BULK_URL
from .db import init_db
from .repository import CardRepository


HEADERS = {"User-Agent": "edh-builder-agent/0.1", "Accept": "application/json"}


def fetch_oracle_bulk_uri() -> str:
    request = urllib.request.Request(SCRYFALL_BULK_URL, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))["download_uri"]


def sync_oracle_cards(cache_path: Path | None = None) -> int:
    init_db()
    download_uri = fetch_oracle_bulk_uri()
    target = cache_path or Path(tempfile.gettempdir()) / "scryfall-oracle-cards.json"
    request = urllib.request.Request(download_uri, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    with target.open("r", encoding="utf-8") as handle:
        cards = json.load(handle)
    return CardRepository().upsert_cards(cards)


def import_oracle_cards(path: Path) -> int:
    init_db()
    with path.open("r", encoding="utf-8") as handle:
        cards = json.load(handle)
    return CardRepository().upsert_cards(cards)
