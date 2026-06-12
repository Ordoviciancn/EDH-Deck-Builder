import unittest

from edh_builder.deck_builder import EdhDeckBuilder
from edh_builder.models import BuildRequest, Card, ComboPackage, Deck, DeckCard
from edh_builder.exporters import to_grouped_markdown


def card(name: str, text: str = "", type_line: str = "Instant", identity: set[str] | None = None) -> Card:
    return Card(
        oracle_id=name,
        name=name,
        mana_cost="",
        cmc=2,
        colors=identity or set(),
        color_identity=identity or set(),
        type_line=type_line,
        oracle_text=text,
        legal_commander=True,
        banned_commander=False,
        can_be_commander=False,
    )


class TestExplainableBuilder(unittest.TestCase):
    def test_export_includes_audit_and_card_reasons(self) -> None:
        commander = card("Atraxa, Praetors' Voice", type_line="Legendary Creature", identity={"W", "U", "B", "G"})
        deck = Deck(commander, [DeckCard(card("Counterspell", "Counter target spell.", identity={"U"}), "removal", 1, "测试理由。")])
        markdown = to_grouped_markdown(
            deck,
            [],
            {
                "strategy": "test",
                "role_targets": {"removal": 1},
                "deck_stats": {"role_counts": {"removal": 1}, "known_price_usd": 0},
                "color_wheel": [{"color": "U", "name": "Blue", "primary_roles": ["draw"], "deckbuilding_note": "test"}],
            },
        )

        self.assertIn("## 构筑审计", markdown)
        self.assertIn("## 单卡投入理由", markdown)
        self.assertIn("Counterspell [removal]: 测试理由。", markdown)

    def test_combo_package_dict_exposes_source_and_rules_logic(self) -> None:
        package = ComboPackage(
            name="Synthesized rules combo: A + B",
            components=("A", "B"),
            result="Infinite mana",
            source="synthesized/rules-pattern",
            rules_logic=("untap-nonland-permanents",),
        )

        payload = EdhDeckBuilder._combo_package_dict(package)

        self.assertEqual(payload["source"], "synthesized/rules-pattern")
        self.assertEqual(payload["rules_logic"], ["untap-nonland-permanents"])

    def test_role_targets_raise_interaction_for_high_power_combo_meta(self) -> None:
        targets = EdhDeckBuilder()._role_targets(
            BuildRequest(
                commander="Atraxa, Praetors' Voice",
                power_level=8,
                combo_preference="balanced",
                meta_notes="桌上combo",
            )
        )

        self.assertLessEqual(targets["lands"], 35)
        self.assertGreaterEqual(targets["removal"], 11)
        self.assertGreaterEqual(targets["ramp"], 13)


if __name__ == "__main__":
    unittest.main()
