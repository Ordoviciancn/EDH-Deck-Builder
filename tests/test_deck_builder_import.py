import unittest


class TestDeckBuilderImport(unittest.TestCase):
    def test_deck_builder_imports(self) -> None:
        from edh_builder.deck_builder import EdhDeckBuilder

        self.assertIsNotNone(EdhDeckBuilder)
