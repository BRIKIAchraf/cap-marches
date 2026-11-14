"""Correspondance sémantique avec repli local et chargement paresseux."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Iterable

import numpy as np


class SemanticError(RuntimeError):
    """Erreur non bloquante du moteur sémantique."""


@lru_cache(maxsize=2)
def _sentence_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SemanticError(
            "Installez `requirements-ai.txt` pour activer les embeddings."
        ) from exc
    return SentenceTransformer(model_name)


def _sentence_transformer_scores(
    query: str, documents: list[str], model_name: str
) -> np.ndarray:
    model = _sentence_model(model_name)
    embeddings = model.encode(
        [query, *documents],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.clip(np.asarray(embeddings[1:]) @ np.asarray(embeddings[0]), 0, 1)


def _tfidf_scores(query: str, documents: list[str]) -> np.ndarray:
    from sklearn.feature_extraction.text import TfidfVectorizer

    word_vectorizer = TfidfVectorizer(
        strip_accents="unicode",
        lowercase=True,
        ngram_range=(1, 2),
        analyzer="word",
        sublinear_tf=True,
    )
    char_vectorizer = TfidfVectorizer(
        strip_accents="unicode",
        lowercase=True,
        ngram_range=(3, 5),
        analyzer="char_wb",
        sublinear_tf=True,
    )

    def expand(text: str) -> str:
        value = re.sub(r"\brh\b", "ressources humaines", text, flags=re.IGNORECASE)
        value = re.sub(
            r"\bsaas\b", "logiciel service cloud", value, flags=re.IGNORECASE
        )
        return value

    corpus = [expand(query), *(expand(document) for document in documents)]
    word_matrix = word_vectorizer.fit_transform(corpus)
    char_matrix = char_vectorizer.fit_transform(corpus)
    word_scores = np.asarray((word_matrix[1:] @ word_matrix[0].T).toarray()).ravel()
    char_scores = np.asarray((char_matrix[1:] @ char_matrix[0].T).toarray()).ravel()
    return np.clip((word_scores * 0.7) + (char_scores * 0.3), 0, 1)


def semantic_scores(
    query: str,
    documents: Iterable[str],
    *,
    provider: str | None = None,
    model_name: str | None = None,
) -> list[float]:
    """Retourne une similarité bornée entre 0 et 1 pour chaque document."""

    docs = [str(document or "").strip() for document in documents]
    if not docs:
        return []
    if not query.strip():
        return [0.0] * len(docs)

    selected = (provider or os.getenv("SEMANTIC_PROVIDER", "tfidf")).strip().lower()
    model = model_name or os.getenv(
        "SEMANTIC_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    try:
        if selected == "sentence-transformers":
            values = _sentence_transformer_scores(query, docs, model)
        elif selected == "tfidf":
            values = _tfidf_scores(query, docs)
        else:
            raise SemanticError(f"Fournisseur sémantique inconnu : {selected}")
    except ValueError:
        return [0.0] * len(docs)
    return [round(float(np.clip(value, 0, 1)), 6) for value in values]


def semantic_points(scores: Iterable[float], maximum: int = 35) -> list[int]:
    return [round(maximum * max(0.0, min(1.0, float(score)))) for score in scores]
