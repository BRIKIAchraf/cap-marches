import unittest

from services.decp import fetch_contracts


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"results": [{"objet": "Logiciel RH"}]}


class FakeSession:
    def __init__(self):
        self.last = None

    def get(self, url, **kwargs):
        self.last = (url, kwargs)
        return FakeResponse()


class DecpTests(unittest.TestCase):
    def test_builds_safe_request(self):
        session = FakeSession()
        result = fetch_contracts("l'outil RH", session=session)
        self.assertEqual(result[0]["objet"], "Logiciel RH")
        where = session.last[1]["params"]["where"]
        self.assertIn("l''outil RH", where)
        self.assertEqual(session.last[1]["params"]["limit"], 100)


if __name__ == "__main__":
    unittest.main()
