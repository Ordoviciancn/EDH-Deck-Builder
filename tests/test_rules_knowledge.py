import unittest

from edh_builder.models import BuildRequest, Card
from edh_builder.rules_knowledge import rules_context_for


def commander(name: str, text: str) -> Card:
    return Card(
        oracle_id=name,
        name=name,
        mana_cost="",
        cmc=6,
        colors={"G", "U"},
        color_identity={"G", "U"},
        type_line="Legendary Creature",
        oracle_text=text,
        legal_commander=True,
        banned_commander=False,
        can_be_commander=True,
    )


class TestRulesKnowledge(unittest.TestCase):
    def test_includes_cascade_context_for_quandrix(self) -> None:
        context = rules_context_for(
            BuildRequest(commander="Quandrix, the Proof", theme="cascade storm combo"),
            commander("Quandrix, the Proof", "Instant and sorcery spells you cast from your hand have cascade."),
        )
        self.assertIn("Cascade", context)
        self.assertIn("Quandrix, the Proof Notes", context)
        self.assertIn("Color identity", context)


if __name__ == "__main__":
    unittest.main()
