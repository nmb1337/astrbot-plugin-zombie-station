import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game import DECK_SIZE, GameError, ParcelGame, initial_state


class ParcelGameTests(unittest.TestCase):
    def setUp(self):
        self.state = initial_state()
        self.game = ParcelGame(10, random.Random(7))
        self.game.start(self.state, "group", "host", "主持人")

    def test_draw_is_without_replacement_and_costs_stamina(self):
        first = self.game.draw(self.state, "group", "player", "玩家", 5)
        second = self.game.draw(self.state, "group", "player", "玩家", 5)
        first_ids = {card["id"] for card in first.cards}
        second_ids = {card["id"] for card in second.cards}
        self.assertEqual(len(first_ids), 5)
        self.assertFalse(first_ids & second_ids)
        self.assertEqual(second.stamina_left, 0)
        self.assertEqual(second.remaining, DECK_SIZE - 10)

    def test_day_refresh_requires_host(self):
        self.game.draw(self.state, "group", "player", "玩家", 4)
        with self.assertRaises(GameError):
            self.game.next_day(self.state, "group", "other")
        group = self.game.next_day(self.state, "group", "host")
        self.assertEqual(group["day"], 2)
        self.assertEqual(group["players"]["player"]["stamina"], 10)

    def test_empty_deck_starts_next_round(self):
        self.state["groups"]["group"]["deck"] = [0]
        result = self.game.draw(self.state, "group", "player", "玩家", 1)
        self.assertEqual(result.completed_round, 1)
        self.assertEqual(result.remaining, 0)
        self.assertEqual(self.state["groups"]["group"]["round"], 2)
        self.assertEqual(len(self.state["groups"]["group"]["deck"]), DECK_SIZE)


if __name__ == "__main__":
    unittest.main()
