import unittest

from services.agent import build_plan, run_agent


class AgentTests(unittest.TestCase):
    profile = {
        "offer": "Logiciel RH SaaS",
        "keywords": "gestion ressources humaines",
        "departments": "75",
        "minimum": 50_000,
        "maximum": 500_000,
    }

    def test_plan_uses_company_memory(self):
        plan = build_plan(self.profile, "marchés à venir")
        self.assertIn("Logiciel RH", plan.query)
        self.assertEqual(plan.department, "75")

    def test_agent_returns_evidence_without_network(self):
        project = {
            "code": "P1",
            "libelle": "Plateforme de gestion RH",
            "description": "Solution SaaS",
            "siren_de_l_entite_acheteuse": "123456789",
            "date_previsionnelle_de_publication": "2027-01-15",
            "montant_estime_du_marche": "100k - 500k",
            "departement_s_d_execution_du_marche": "75",
        }
        contract = {
            "id": "M1",
            "objet": "Logiciel RH",
            "montant": 100_000,
            "datenotification": "2024-01-01",
            "dureemois": 36,
            "lieuexecution_code": "75",
            "acheteur_id": "12345678900001",
        }
        result = run_agent(
            self.profile,
            project_fetcher=lambda *a, **k: [project],
            contract_fetcher=lambda *a, **k: [contract],
            organization_fetcher=lambda *a, **k: [],
        )
        self.assertEqual(result["projects"][0]["code"], "P1")
        self.assertEqual(
            result["evidence"][0]["source_dataset"], "projets_achats_publics"
        )


if __name__ == "__main__":
    unittest.main()
