from datetime import date
import unittest

import pandas as pd

from scoring import amount_points, keyword_points, renewal_points, score_contracts


class ScoringTests(unittest.TestCase):
    def test_keyword_score_is_bounded(self):
        self.assertEqual(keyword_points("Logiciel de gestion RH", "logiciel RH"), 30)
        self.assertEqual(keyword_points("Formation professionnelle", "logiciel RH"), 0)

    def test_amount_score(self):
        self.assertEqual(amount_points(100_000, 50_000, 200_000), 20)
        self.assertEqual(amount_points(None, 50_000, 200_000), 0)

    def test_renewal_score(self):
        self.assertEqual(
            renewal_points(pd.Timestamp("2027-05-01"), date(2026, 11, 14)), 30
        )
        self.assertEqual(
            renewal_points(pd.Timestamp("2031-05-01"), date(2026, 11, 14)), 0
        )

    def test_full_scoring(self):
        records = [
            {
                "objet": "Logiciel RH",
                "montant": 100_000,
                "datenotification": "2024-05-01",
                "dureemois": 36,
                "lieuexecution_code": "75",
                "acheteur_id": "A",
            },
            {
                "objet": "Achat de mobilier",
                "montant": 2_000,
                "datenotification": "2024-05-01",
                "dureemois": 12,
                "lieuexecution_code": "33",
                "acheteur_id": "B",
            },
        ]
        result = score_contracts(
            records,
            keyword="logiciel RH",
            location="75",
            minimum=50_000,
            maximum=200_000,
            today=date(2026, 11, 14),
        )
        self.assertEqual(result.iloc[0]["acheteur_id"], "A")
        self.assertGreater(result.iloc[0]["score"], result.iloc[1]["score"])


if __name__ == "__main__":
    unittest.main()

