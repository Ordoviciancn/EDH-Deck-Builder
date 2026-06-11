from __future__ import annotations

import json
import sqlite3

from .db import connect
from .models import Card, Combo


def _set(value: str | None) -> set[str]:
    return set(value or "")


def row_to_card(row: sqlite3.Row) -> Card:
    return Card(
        oracle_id=row["oracle_id"],
        name=row["name"],
        mana_cost=row["mana_cost"] or "",
        cmc=float(row["cmc"] or 0),
        colors=_set(row["colors"]),
        color_identity=_set(row["color_identity"]),
        type_line=row["type_line"] or "",
        oracle_text=row["oracle_text"] or "",
        legal_commander=bool(row["legal_commander"]),
        banned_commander=bool(row["banned_commander"]),
        can_be_commander=bool(row["can_be_commander"]),
        price_usd=row["price_usd"],
        scryfall_uri=row["scryfall_uri"] or "",
        image_uri=row["image_uri"] or "",
    )


class CardRepository:
    def get_by_name(self, name: str) -> Card | None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM cards WHERE lower(name) = lower(?) LIMIT 1", (name,)
            ).fetchone()
            return row_to_card(row) if row else None

    def search(self, query: str, limit: int = 20) -> list[Card]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT * FROM cards WHERE name LIKE ? ORDER BY name LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            return [row_to_card(row) for row in rows]

    def legal_pool(self, color_identity: set[str], budget: float | None = None) -> list[Card]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM cards
                WHERE legal_commander = 1
                  AND banned_commander = 0
                  AND type_line NOT LIKE '%Token%'
                  AND type_line NOT LIKE '%Plane%'
                  AND type_line NOT LIKE '%Scheme%'
                """
            ).fetchall()
        cards = [row_to_card(row) for row in rows]
        pool = [
            card
            for card in cards
            if card.color_identity.issubset(color_identity)
            and (budget is None or card.price_usd is None or card.price_usd <= max(budget, 1))
        ]
        return pool

    def upsert_cards(self, rows: list[dict]) -> int:
        payload = []
        for card in rows:
            legalities = card.get("legalities") or {}
            commander_status = legalities.get("commander", "not_legal")
            image_uris = card.get("image_uris") or {}
            if not image_uris and card.get("card_faces"):
                image_uris = card["card_faces"][0].get("image_uris") or {}
            payload.append(
                (
                    card["oracle_id"],
                    card["name"],
                    card.get("mana_cost", ""),
                    card.get("cmc", 0),
                    "".join(card.get("colors") or []),
                    "".join(card.get("color_identity") or []),
                    card.get("type_line", ""),
                    card.get("oracle_text") or _faces_text(card),
                    1 if commander_status == "legal" else 0,
                    1 if commander_status == "banned" else 0,
                    1 if _can_be_commander(card) else 0,
                    _price(card),
                    card.get("scryfall_uri", ""),
                    image_uris.get("normal") or image_uris.get("small") or "",
                    json.dumps(card, ensure_ascii=False),
                )
            )
        with connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO cards (
                  oracle_id, name, mana_cost, cmc, colors, color_identity, type_line,
                  oracle_text, legal_commander, banned_commander, can_be_commander,
                  price_usd, scryfall_uri, image_uri, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
        return len(payload)


class ComboRepository:
    def list_all(self) -> list[Combo]:
        with connect() as conn:
            rows = conn.execute("SELECT * FROM combos ORDER BY name").fetchall()
        return [
            Combo(
                name=row["name"],
                cards=tuple(json.loads(row["cards"])),
                result=row["result"],
                source=row["source"],
                tags=tuple(json.loads(row["tags"] or "[]")),
            )
            for row in rows
        ]

    def relevant_for(self, color_identity: set[str], theme: str = "", limit: int = 300) -> list[Combo]:
        with connect() as conn:
            rows = conn.execute("SELECT * FROM combos ORDER BY source, name").fetchall()
        combos: list[tuple[int, Combo]] = []
        theme_terms = {term for term in theme.lower().replace(",", " ").split() if len(term) >= 4}
        for row in rows:
            tags = tuple(json.loads(row["tags"] or "[]"))
            combo_identity = _identity_from_tags(tags)
            if combo_identity and not combo_identity.issubset(color_identity):
                continue
            combo = Combo(
                name=row["name"],
                cards=tuple(json.loads(row["cards"])),
                result=row["result"],
                source=row["source"],
                tags=tags,
            )
            haystack = " ".join([combo.name, combo.result, " ".join(combo.cards), " ".join(combo.tags)]).lower()
            score = 0
            if row["source"] == "commander-spellbook":
                score += 5
            if "infinite" in haystack:
                score += 10
            score += 4 * sum(1 for term in theme_terms if term in haystack)
            if "mana" in haystack:
                score += 2
            if "storm" in haystack:
                score += 2
            combos.append((score, combo))
        combos.sort(key=lambda item: (-item[0], len(item[1].cards), item[1].name))
        return [combo for _, combo in combos[:limit]]

    def upsert_many(self, combos: list[Combo]) -> int:
        with connect() as conn:
            conn.execute("DELETE FROM combos WHERE source LIKE 'seed/%' OR source = 'custom'")
            conn.executemany(
                "INSERT INTO combos(name, cards, result, source, tags) VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        combo.name,
                        json.dumps(list(combo.cards), ensure_ascii=False),
                        combo.result,
                        combo.source,
                        json.dumps(list(combo.tags), ensure_ascii=False),
                    )
                    for combo in combos
                ],
            )
        return len(combos)

    def replace_source(self, source: str, combos: list[Combo]) -> int:
        with connect() as conn:
            conn.execute("DELETE FROM combos WHERE source = ?", (source,))
            conn.executemany(
                "INSERT INTO combos(name, cards, result, source, tags) VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        combo.name,
                        json.dumps(list(combo.cards), ensure_ascii=False),
                        combo.result,
                        combo.source,
                        json.dumps(list(combo.tags), ensure_ascii=False),
                    )
                    for combo in combos
                ],
            )
        return len(combos)


def _faces_text(card: dict) -> str:
    return "\n".join(face.get("oracle_text", "") for face in card.get("card_faces") or [])


def _can_be_commander(card: dict) -> bool:
    type_line = card.get("type_line", "")
    text = (card.get("oracle_text") or _faces_text(card)).lower()
    return (
        ("Legendary" in type_line and "Creature" in type_line)
        or "can be your commander" in text
        or "choose a background" in text
    )


def _price(card: dict) -> float | None:
    usd = (card.get("prices") or {}).get("usd")
    try:
        return float(usd) if usd else None
    except ValueError:
        return None


def _identity_from_tags(tags: tuple[str, ...]) -> set[str]:
    for tag in tags:
        if tag.startswith("identity:"):
            return set(tag.split(":", 1)[1])
    return set()
