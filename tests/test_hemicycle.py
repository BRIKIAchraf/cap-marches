import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import storage
from services.hemicycle import (
    fetch_organizations,
    fetch_upcoming_projects,
    query_dataset,
)


class FakeResponse:
    def __init__(self, rows=None):
        self.status_code = 200
        self.rows = rows if rows is not None else [{"code": "P1", "libelle": "Logiciel RH"}]

    def raise_for_status(self):
        return None

    def json(self):
        return {"resultats": self.rows}


class FakeSession:
    def __init__(self):
        self.last = None
        self.calls = []

    def post(self, url, **kwargs):
        self.last = (url, kwargs)
        self.calls.append((url, kwargs))
        filtres = kwargs.get("json", {}).get("filtres", [])
        siren_val = next((f["valeur"] for f in filtres if f.get("colonne") == "siren"), None)
        if siren_val:
            return FakeResponse([{"siren": siren_val, "denomination": f"Ville {siren_val}"}])
        return FakeResponse()


class HemicycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database = Path(self.temp.name) / "test_hemi.db"
        storage.configure_database(f"sqlite:///{database.as_posix()}")

    def tearDown(self):
        storage.engine.dispose()
        self.temp.cleanup()
    @patch.dict(os.environ, {"HEMICYCLE_API_KEY": "test-key"}, clear=False)
    def test_uses_official_post_endpoint(self):
        session = FakeSession()
        rows = fetch_upcoming_projects(
            "logiciel RH",
            department="75",
            category="Services",
            limit=25,
            session=session,
        )
        self.assertEqual(rows[0]["code"], "P1")
        url, kwargs = session.last
        self.assertEqual(url, "https://api.hemicycle.ai/v1/jeux/interroger")
        self.assertEqual(kwargs["json"]["jeu"], "projets_achats_publics")
        self.assertEqual(kwargs["json"]["recherche"], "logiciel RH")
        self.assertEqual(kwargs["json"]["limite"], 25)
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Bearer "))

    @patch.dict(os.environ, {"HEMICYCLE_API_KEY": "test-key"}, clear=False)
    def test_queries_sirene_identifiers_with_supported_eq_filter(self):
        session = FakeSession()
        fetch_organizations(
            ["990000001", "990000002"],
            identifier_type="siren",
            session=session,
        )
        self.assertEqual(len(session.calls), 2)
        filters = session.calls[0][1]["json"]["filtres"]
        self.assertEqual(filters[0]["colonne"], "siren")
        self.assertEqual(filters[0]["op"], "eq")
        self.assertEqual(filters[1]["colonne"], "siege")
        self.assertEqual(session.calls[0][1]["json"]["tri"], "siret")

    @patch.dict(os.environ, {"HEMICYCLE_API_KEY": "test-key"}, clear=False)
    def test_extracts_nested_rows(self):
        session = FakeSession()
        rows = query_dataset("marches_publics", session=session)
        self.assertEqual(rows, [{"code": "P1", "libelle": "Logiciel RH"}])

    @patch.dict(os.environ, {"HEMICYCLE_API_KEY": "test-key"}, clear=False)
    def test_uses_local_cache_for_subsequent_calls(self):
        session = FakeSession()
        # Premier appel : interroge l'API
        first_res = fetch_organizations(
            ["880000001"],
            identifier_type="siren",
            session=session,
        )
        self.assertEqual(len(session.calls), 1)

        # Deuxième appel pour le même SIREN : résolu via le cache, 0 nouvel appel API
        session2 = FakeSession()
        second_res = fetch_organizations(
            ["880000001"],
            identifier_type="siren",
            session=session2,
        )
        self.assertEqual(len(session2.calls), 0)
        self.assertEqual(len(second_res), 1)


if __name__ == "__main__":
    unittest.main()

