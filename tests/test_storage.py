import tempfile
import unittest
from pathlib import Path

import storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database = Path(self.temp.name) / "test.db"
        storage.configure_database(f"sqlite:///{database.as_posix()}")

    def tearDown(self):
        storage.engine.dispose()
        self.temp.cleanup()

    def test_profile_feedback_and_search(self):
        storage.save_profile(
            {
                "company_name": "Demo",
                "offer": "Logiciel RH",
                "keywords": "SaaS",
                "minimum": 10_000,
                "maximum": 200_000,
            }
        )
        self.assertEqual(storage.load_profile()["company_name"], "Demo")
        storage.record_feedback("P-1", "pertinent", "projets_achats_publics", {"score": 80})
        self.assertEqual(storage.feedback_counts(), {"pertinent": 1})
        storage.save_search("RH", {"keyword": "RH"}, True)
        self.assertEqual(storage.list_saved_searches()[0]["name"], "RH")


if __name__ == "__main__":
    unittest.main()
