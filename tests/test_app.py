import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AppSmokeTests(unittest.TestCase):
    def test_offline_demo_flow(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path), default_timeout=15)
        app.run()

        self.assertEqual(app.title[0].value, "🎯 Cap Marchés")
        app.selectbox[0].set_value("Démonstration hors ligne")
        app.button[0].click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertGreaterEqual(len(app.metric), 4)
        self.assertTrue(any("marchés analysés" in item.value for item in app.success))


if __name__ == "__main__":
    unittest.main()

