import asyncio
import importlib.util
import sys
import types
import unittest
from contextlib import asynccontextmanager
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def load_plugin_module():
    astrbot = types.ModuleType("astrbot")
    api = types.ModuleType("astrbot.api")
    event = types.ModuleType("astrbot.api.event")
    star = types.ModuleType("astrbot.api.star")
    web = types.ModuleType("astrbot.api.web")
    path_utils = types.ModuleType("astrbot.core.utils.astrbot_path")

    class CommandGroup:
        def __call__(self, func):
            def command(*_args, **_kwargs):
                return lambda handler: handler

            func.command = command
            return func

    class Filter:
        class EventMessageType:
            GROUP_MESSAGE = object()

        class PermissionType:
            ADMIN = object()

        @staticmethod
        def command_group(*_args, **_kwargs):
            return CommandGroup()

        @staticmethod
        def event_message_type(*_args, **_kwargs):
            return lambda handler: handler

        @staticmethod
        def permission_type(*_args, **_kwargs):
            return lambda handler: handler

    class Star:
        def __init__(self, *_args, **_kwargs):
            pass

    api.logger = types.SimpleNamespace(warning=lambda *_args, **_kwargs: None)
    event.AstrMessageEvent = object
    event.filter = Filter()
    star.Context = object
    star.Star = Star
    star.register = lambda *_args, **_kwargs: lambda cls: cls
    web.PluginUploadFile = object
    web.error_response = lambda *args, **kwargs: args[0] if args else None
    web.json_response = lambda payload: payload
    web.request = types.SimpleNamespace()
    path_utils.get_astrbot_plugin_data_path = lambda *_args, **_kwargs: PLUGIN_ROOT

    saved_modules = {name: sys.modules.get(name) for name in (
        "astrbot",
        "astrbot.api",
        "astrbot.api.event",
        "astrbot.api.star",
        "astrbot.api.web",
        "astrbot.core",
        "astrbot.core.utils",
        "astrbot.core.utils.astrbot_path",
    )}
    sys.modules.update({
        "astrbot": astrbot,
        "astrbot.api": api,
        "astrbot.api.event": event,
        "astrbot.api.star": star,
        "astrbot.api.web": web,
        "astrbot.core": types.ModuleType("astrbot.core"),
        "astrbot.core.utils": types.ModuleType("astrbot.core.utils"),
        "astrbot.core.utils.astrbot_path": path_utils,
    })

    package_name = "zombie_station_test_plugin"
    package = types.ModuleType(package_name)
    package.__path__ = [str(PLUGIN_ROOT)]
    sys.modules[package_name] = package
    module_name = f"{package_name}.main"
    spec = importlib.util.spec_from_file_location(module_name, PLUGIN_ROOT / "main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        for name, saved in saved_modules.items():
            if saved is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved
    return module


class FakeEvent:
    def get_group_id(self):
        return "group"

    def get_session_id(self):
        return "group"

    def get_sender_id(self):
        return "player"

    @staticmethod
    def plain_result(text):
        return text


class StatusCommandTests(unittest.TestCase):
    def test_status_reports_imported_card_pool_size(self):
        module = load_plugin_module()
        plugin = module.ZombieStationPlugin.__new__(module.ZombieStationPlugin)
        plugin.config = {"daily_stamina": 10}

        @asynccontextmanager
        async def lock():
            yield

        async def load_state():
            return {
                "cards": [{"id": 1}, {"id": 2}, {"id": 3}],
                "groups": {
                    "group": {
                        "round": 2,
                        "day": 4,
                        "host_name": "主持人",
                        "deck": [0, 2],
                        "players": {
                            "player": {
                                "stamina": 7,
                                "daily_stamina": 9,
                                "opened_today": 2,
                                "total_opened": 5,
                            }
                        },
                    }
                },
            }

        plugin.lock = lock()
        plugin._load_state = load_state
        plugin.game = types.SimpleNamespace(get_group=lambda state, group_id: state["groups"][group_id])

        async def collect():
            return [message async for message in plugin.game_status(FakeEvent())]

        messages = asyncio.run(collect())
        self.assertEqual(len(messages), 1)
        self.assertIn("包裹剩余：2/3", messages[0])
        self.assertIn("你的体力：7/9", messages[0])


if __name__ == "__main__":
    unittest.main()