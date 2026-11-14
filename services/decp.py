"""Client minimal pour l'API Explore des DECP.

Le connecteur interroge le jeu de données officiel des marchés publics
valides. Il ne dépend d'aucune clé et limite volontairement le volume.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from services.http import resilient_session


BASE_URL = (
    "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "decp-2022-marches-valides/records"
)


class DecpError(RuntimeError):
    """Erreur lisible par l'interface lors de l'appel DECP."""


def _escape_query(value: str) -> str:
    """Neutralise les apostrophes utilisées par la clause `search`."""

    return value.strip().replace("'", "''")


def fetch_contracts(
    keyword: str,
    *,
    limit: int = 100,
    timeout: float = 15.0,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Retourne les marchés récents correspondant à un mot-clé."""

    keyword = keyword.strip()
    if not keyword:
        raise ValueError("Saisissez au moins un mot-clé.")
    limit = max(1, min(int(limit), 100))
    params = {
        "where": f"search(objet, '{_escape_query(keyword)}')",
        "order_by": "datenotification desc",
        "limit": limit,
    }
    client = session or resilient_session()
    contact = os.getenv("APP_CONTACT", "").strip() or "contact-non-renseigne"
    try:
        response = client.get(
            BASE_URL,
            params=params,
            timeout=timeout,
            headers={
                "User-Agent": f"CapMarchesHackathon/1.0 (contact: {contact})"
            },
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise DecpError(f"L'API DECP est indisponible : {exc}") from exc

    results = payload.get("results", [])
    if not isinstance(results, list):
        raise DecpError("Réponse DECP inattendue : champ `results` absent.")
    return results

