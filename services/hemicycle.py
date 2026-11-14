"""Adaptateur Hémicycle configurable.

Hémicycle publie plusieurs outils. Le hackathon demande d'appeler `guide`
pour obtenir l'outil et la route adaptés. L'URL exacte est donc injectée via
HEMICYCLE_RECORDS_URL au lieu d'être devinée ici.
"""

from __future__ import annotations

import os
from typing import Any

import requests


class HemicycleError(RuntimeError):
    """Erreur lisible par l'interface lors de l'appel Hémicycle."""


def is_configured() -> bool:
    return bool(
        os.getenv("HEMICYCLE_API_KEY", "").strip()
        and os.getenv("HEMICYCLE_RECORDS_URL", "").strip()
    )


def fetch_contracts(
    keyword: str,
    *,
    limit: int = 100,
    timeout: float = 15.0,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Appelle la route Hémicycle fournie par `guide`.

    L'adaptateur accepte les formes courantes `results`, `data` et liste JSON.
    Si la route retournée par `guide` emploie d'autres paramètres, adaptez
    uniquement ce petit fichier.
    """

    api_key = os.getenv("HEMICYCLE_API_KEY", "").strip()
    url = os.getenv("HEMICYCLE_RECORDS_URL", "").strip()
    if not api_key or not url:
        raise HemicycleError(
            "Hémicycle n'est pas configuré. Renseignez HEMICYCLE_API_KEY et "
            "HEMICYCLE_RECORDS_URL dans .env."
        )

    client = session or requests
    try:
        response = client.get(
            url,
            params={"query": keyword.strip(), "limit": max(1, min(limit, 100))},
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "CapMarchesHackathon/1.0",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise HemicycleError(f"Hémicycle est indisponible : {exc}") from exc

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("results", "data", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise HemicycleError("Format de réponse Hémicycle non reconnu.")

