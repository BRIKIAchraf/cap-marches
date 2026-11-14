import unittest

from services.semantic import semantic_points, semantic_scores


class SemanticTests(unittest.TestCase):
    def test_tfidf_ranks_related_document_first(self):
        values = semantic_scores(
            "logiciel ressources humaines",
            ["solution SaaS de gestion RH", "réfection de chaussée"],
            provider="tfidf",
        )
        self.assertEqual(len(values), 2)
        self.assertGreater(values[0], values[1])

    def test_points_are_bounded(self):
        self.assertEqual(semantic_points([-1, 0.5, 2]), [0, 18, 35])


if __name__ == "__main__":
    unittest.main()
