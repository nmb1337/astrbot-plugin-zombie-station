import unittest
from pathlib import Path


class DashboardPageTests(unittest.TestCase):
    def test_import_avoids_native_confirmation_dialog(self):
        app = (Path(__file__).resolve().parents[1] / "pages" / "dashboard" / "app.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('bridge.upload("cards/import", file)', app)
        self.assertNotIn("window.confirm(", app)


if __name__ == "__main__":
    unittest.main()
