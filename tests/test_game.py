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

    def test_host_sets_individual_daily_stamina(self):
        self.game.set_player_stamina(self.state, "group", "host", "small", 6)
        self.game.set_player_stamina(self.state, "group", "host", "large", 14)
        self.game.draw(self.state, "group", "small", "小体型", 4)
        self.game.draw(self.state, "group", "large", "大体型", 10)

        group = self.game.next_day(self.state, "group", "host")
        self.assertEqual(group["players"]["small"]["daily_stamina"], 6)
        self.assertEqual(group["players"]["small"]["stamina"], 6)
        self.assertEqual(group["players"]["large"]["daily_stamina"], 14)
        self.assertEqual(group["players"]["large"]["stamina"], 14)

    def test_non_host_cannot_set_daily_stamina(self):
        with self.assertRaises(GameError):
            self.game.set_player_stamina(self.state, "group", "other", "player", 8)

    def test_empty_deck_starts_next_round(self):
        self.state["groups"]["group"]["deck"] = [0]
        result = self.game.draw(self.state, "group", "player", "玩家", 1)
        self.assertEqual(result.completed_round, 1)
        self.assertEqual(result.remaining, 0)
        self.assertEqual(self.state["groups"]["group"]["round"], 2)
        self.assertEqual(len(self.state["groups"]["group"]["deck"]), DECK_SIZE)

    def test_custom_size_deck_resets_to_its_imported_size(self):
        self.state["cards"] = self.state["cards"][:3]
        self.state["groups"] = {}
        self.game.start(self.state, "group", "host", "主持人")

        result = self.game.draw(self.state, "group", "player", "玩家", 3)

        self.assertEqual(result.remaining, 0)
        self.assertEqual(result.completed_round, 1)
        self.assertEqual(len(self.state["groups"]["group"]["deck"]), 3)
        snapshot = self.game.snapshot(self.state, "group")
        self.assertEqual(snapshot["deck_size"], 3)
        self.assertEqual(snapshot["groups"][0]["drawn"], 0)

if __name__ == "__main__":
    unittest.main()
