from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

DECK_SIZE = 1200
MAX_DRAW_PER_COMMAND = 10
HISTORY_LIMIT = 50


class GameError(ValueError):
    pass


@dataclass
class DrawResult:
    cards: list[dict[str, str]]
    stamina_left: int
    remaining: int
    round_number: int
    day: int
    completed_round: int | None = None


def built_in_cards() -> list[dict[str, str]]:
    return [
        {
            "id": f"P-{number:04d}",
            "title": f"未登记包裹 {number:04d}",
            "text": "请在 WebUI 导入你的卡牌表后开始正式副本。",
        }
        for number in range(1, DECK_SIZE + 1)
    ]


def initial_state() -> dict[str, Any]:
    return {"cards": built_in_cards(), "cards_source": "内置占位卡池", "groups": {}}


class ParcelGame:
    def __init__(self, daily_stamina: int, rng: random.Random | None = None):
        if daily_stamina < 1:
            raise ValueError("daily_stamina must be positive")
        self.daily_stamina = daily_stamina
        self.rng = rng or random.SystemRandom()

    @staticmethod
    def _new_group(host_id: str, host_name: str, deck_size: int, round_number: int = 1) -> dict[str, Any]:
        if deck_size < 1:
            raise GameError("卡池为空，请先在 WebUI 导入至少一张卡牌。")
        return {
            "host_id": host_id,
            "host_name": host_name,
            "round": round_number,
            "day": 1,
            "deck": list(range(deck_size)),
            "players": {},
            "stamina_limits": {},
            "history": [],
        }

    def start(self, state: dict[str, Any], group_id: str, host_id: str, host_name: str) -> dict[str, Any]:
        if group_id in state["groups"]:
            raise GameError("本群已有进行中的驿站副本。")
        state["groups"][group_id] = self._new_group(host_id, host_name, len(state["cards"]))
        return state["groups"][group_id]

    @staticmethod
    def get_group(state: dict[str, Any], group_id: str) -> dict[str, Any]:
        group = state["groups"].get(group_id)
        if group is None:
            raise GameError("本群尚未开局，请由主持人先发送“驿站 开局”。")
        return group

    def draw(self, state: dict[str, Any], group_id: str, player_id: str, player_name: str, amount: int) -> DrawResult:
        if not 1 <= amount <= MAX_DRAW_PER_COMMAND:
            raise GameError(f"每次只能开 1 到 {MAX_DRAW_PER_COMMAND} 个包裹。")
        group = self.get_group(state, group_id)
        stamina_limit = group.setdefault("stamina_limits", {}).get(player_id, self.daily_stamina)
        player = group["players"].setdefault(
            player_id,
            {
                "name": player_name,
                "daily_stamina": stamina_limit,
                "stamina": stamina_limit,
                "opened_today": 0,
                "total_opened": 0,
            },
        )
        player.setdefault("daily_stamina", stamina_limit)
        player["name"] = player_name or player["name"]
        if player["stamina"] < 1:
            raise GameError("你的体力已耗尽，请等待主持人更新到新的一天。")

        actual_amount = min(amount, player["stamina"], len(group["deck"]))
        chosen_indexes = self.rng.sample(group["deck"], actual_amount)
        chosen_set = set(chosen_indexes)
        cards = [state["cards"][index] for index in chosen_indexes]
        group["deck"] = [index for index in group["deck"] if index not in chosen_set]
        player["stamina"] -= actual_amount
        player["opened_today"] += actual_amount
        player["total_opened"] += actual_amount
        group["history"].extend(
            {
                "player_id": player_id,
                "player_name": player["name"],
                "round": group["round"],
                "day": group["day"],
                "card_id": card["id"],
                "title": card["title"],
                "text": card["text"],
            }
            for card in cards
        )
        group["history"] = group["history"][-HISTORY_LIMIT:]

        round_number, day, remaining = group["round"], group["day"], len(group["deck"])
        completed_round = None
        if remaining == 0:
            completed_round = round_number
            state["groups"][group_id] = self._new_group(
                group["host_id"], group["host_name"], len(state["cards"]), round_number + 1
            )
        return DrawResult(cards, player["stamina"], remaining, round_number, day, completed_round)

    def next_day(self, state: dict[str, Any], group_id: str, operator_id: str) -> dict[str, Any]:
        group = self.get_group(state, group_id)
        if group["host_id"] != operator_id:
            raise GameError("只有本局主持人可以更新到新的一天。")
        group["day"] += 1
        for player_id, player in group["players"].items():
            stamina_limit = group.setdefault("stamina_limits", {}).get(
                player_id, player.get("daily_stamina", self.daily_stamina)
            )
            player["daily_stamina"] = stamina_limit
            player["stamina"] = stamina_limit
            player["opened_today"] = 0
        return group

    def set_player_stamina(
        self,
        state: dict[str, Any],
        group_id: str,
        operator_id: str,
        player_id: str,
        daily_stamina: int,
        force: bool = False,
    ) -> dict[str, Any]:
        if daily_stamina < 1:
            raise GameError("每日体力必须至少为 1。")
        group = self.get_group(state, group_id)
        if not force and group["host_id"] != operator_id:
            raise GameError("只有本局主持人可以设置玩家体力。")
        group.setdefault("stamina_limits", {})[player_id] = daily_stamina
        player = group["players"].setdefault(
            player_id,
            {
                "name": player_id,
                "daily_stamina": daily_stamina,
                "stamina": daily_stamina,
                "opened_today": 0,
                "total_opened": 0,
            },
        )
        player["daily_stamina"] = daily_stamina
        player["stamina"] = daily_stamina
        player["opened_today"] = 0
        return player

    def reset(self, state: dict[str, Any], group_id: str, host_id: str, host_name: str) -> dict[str, Any]:
        previous = state["groups"].get(group_id)
        round_number = previous["round"] + 1 if previous else 1
        state["groups"][group_id] = self._new_group(host_id, host_name, len(state["cards"]), round_number)
        return state["groups"][group_id]

    def snapshot(self, state: dict[str, Any], group_id: str | None = None) -> dict[str, Any]:
        groups = []
        for current_group_id, group in state["groups"].items():
            if group_id and current_group_id != group_id:
                continue
            limits = group.get("stamina_limits", {})
            players = sorted(
                (
                    {
                        **player,
                        "player_id": player_id,
                        "daily_stamina": limits.get(
                            player_id, player.get("daily_stamina", self.daily_stamina)
                        ),
                    }
                    for player_id, player in group["players"].items()
                ),
                key=lambda player: player["total_opened"],
                reverse=True,
            )
            groups.append(
                {
                    "group_id": current_group_id,
                    "host_name": group["host_name"],
                    "round": group["round"],
                    "day": group["day"],
                    "remaining": len(group["deck"]),
                    "drawn": len(state["cards"]) - len(group["deck"]),
                    "player_count": len(players),
                    "players": players,
                    "history": group["history"],
                }
            )
        return {
            "deck_size": len(state["cards"]),
            "cards_source": state.get("cards_source", "未知"),
            "groups": sorted(groups, key=lambda group: group["group_id"]),
        }
