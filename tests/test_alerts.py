import os
import unittest
from unittest.mock import patch

import storage
from services.alerts import format_digest_markdown, run_single_search


class AlertTests(unittest.TestCase):
    def test_format_digest_markdown(self):
        records = [
            {
                "libelle": "Logiciel SIRH et GTA",
                "denomination_acheteur": "Région Île-de-France",
                "montant_estime_du_marche": "150k - 250k €",
                "score": 88,
                "date_previsionnelle_de_publication": "2027-02-01",
            }
        ]
        digest = format_digest_markdown("Veille RH", records, "future")
        self.assertIn("Alerte Cap Marchés · Veille RH", digest)
        self.assertIn("Logiciel SIRH et GTA", digest)
        self.assertIn("Région Île-de-France", digest)
        self.assertIn("88/100", digest)

    def test_run_single_search_empty(self):
        res = run_single_search({"name": "Test", "query": {"keyword": "test-rh"}})
        self.assertIn("total_found", res)
        self.assertIn("new_count", res)
        self.assertIn(res["status"], ("completed", "sent", "no_results_from_source"))


if __name__ == "__main__":
    unittest.main()
