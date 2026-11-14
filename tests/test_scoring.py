from datetime import date
import unittest

import pandas as pd

from scoring import (
    amount_points,
    estimated_amount_points,
    keyword_points,
    parse_amount_range,
    publication_points,
    renewal_points,
    score_contracts,
    score_projects,
)


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

    def test_approch_amount_ranges(self):
        self.assertEqual(parse_amount_range("100k - 500k€"), (100_000, 500_000))
        self.assertEqual(parse_amount_range("1M - 5M€"), (1_000_000, 5_000_000))
        self.assertEqual(estimated_amount_points("100k - 500k€", 50_000, 200_000), 20)

    def test_project_scoring(self):
        records = [
            {
                "libelle": "Logiciel RH en SaaS",
                "description": "Gestion des ressources humaines",
                "siren_de_l_entite_acheteuse": "990000001",
                "categorie_d_achat": "Services",
                "date_previsionnelle_de_publication": "2026-12-01",
                "montant_estime_du_marche": "100k - 500k€",
                "departement_s_d_execution_du_marche": "75",
            },
            {
                "libelle": "Travaux de voirie",
                "date_previsionnelle_de_publication": "2029-01-01",
                "montant_estime_du_marche": "1M - 5M€",
                "departement_s_d_execution_du_marche": "33",
            },
        ]
        result = score_projects(
            records,
            keyword="logiciel RH",
            location="75",
            minimum=50_000,
            maximum=500_000,
            today=date(2026, 11, 14),
        )
        self.assertEqual(result.iloc[0]["siren_de_l_entite_acheteuse"], "990000001")
        self.assertEqual(
            publication_points(pd.Timestamp("2026-12-01"), date(2026, 11, 14)), 30
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

