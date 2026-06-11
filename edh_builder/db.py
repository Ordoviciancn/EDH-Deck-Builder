from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    oracle_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    mana_cost TEXT,
    cmc REAL NOT NULL DEFAULT 0,
    colors TEXT NOT NULL DEFAULT '',
    color_identity TEXT NOT NULL DEFAULT '',
    type_line TEXT NOT NULL DEFAULT '',
    oracle_text TEXT NOT NULL DEFAULT '',
    legal_commander INTEGER NOT NULL DEFAULT 0,
    banned_commander INTEGER NOT NULL DEFAULT 0,
    can_be_commander INTEGER NOT NULL DEFAULT 0,
    price_usd REAL,
    scryfall_uri TEXT,
    image_uri TEXT,
    raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name);
CREATE INDEX IF NOT EXISTS idx_cards_commander ON cards(legal_commander, banned_commander);
CREATE INDEX IF NOT EXISTS idx_cards_can_be_commander ON cards(can_be_commander);

CREATE TABLE IF NOT EXISTS combos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cards TEXT NOT NULL,
    result TEXT NOT NULL,
    source TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT ''
);
"""


@contextmanager
def connect(path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: Path = DB_PATH) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)
