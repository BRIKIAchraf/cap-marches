"""Client Hémicycle pour les trois jeux utilisés par Cap Marchés.

Jeux officiels :
- ``projets_achats_publics`` : achats annoncés avant l'appel d'offres ;
- ``marches_publics`` : marchés déjà notifiés ;
- ``sirene_etablissements`` : identité des acheteurs et titulaires.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterable
from typing import Any

import requests

from services.http import resilient_session


API_URL = "https://api.hemicycle.ai/v1/jeux/interroger"
API_VERSION = "2026-10-01"
UPCOMING_DATASET = "projets_achats_publics"
CONTRACTS_DATASET = "marches_publics"
SIRENE_DATASET = "sirene_etablissements"


class HemicycleError(RuntimeError):
    """Erreur lisible par l'interface lors de l'appel Hémicycle."""


def is_configured() -> bool:
    return bool(os.getenv("HEMICYCLE_API_KEY", "").strip())


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    """Accepte les enveloppes courantes sans masquer une réponse invalide."""

    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("lignes", "resultats", "results", "data", "items", "rows"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
            if isinstance(value, dict):
                try:
                    return _extract_rows(value)
                except HemicycleError:
                    pass
        for key in ("resultat", "reponse", "response"):
            value = payload.get(key)
            if isinstance(value, (dict, list)):
                return _extract_rows(value)
    raise HemicycleError(
        "Format de réponse Hémicycle non reconnu. Consultez la réponse dans "
        "la documentation de l'API."
    )


def query_dataset(
    dataset: str,
    *,
    filters: list[dict[str, Any]] | None = None,
    search: str | None = None,
    sort: str | None = None,
    limit: int = 100,
    timeout: float = 20.0,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Interroge un jeu Hémicycle par l'API documentée."""

    api_key = os.getenv("HEMICYCLE_API_KEY", "").strip()
    if not api_key:
        raise HemicycleError("Ajoutez HEMICYCLE_API_KEY dans le fichier .env.")

    body: dict[str, Any] = {
        "jeu": dataset,
        "limite": max(1, min(int(limit), 100)),
    }
    if filters:
        body["filtres"] = filters
    if search and search.strip():
        body["recherche"] = search.strip()
    if sort:
        body["tri"] = sort

    url = os.getenv("HEMICYCLE_API_URL", API_URL).strip() or API_URL
    version = os.getenv("HEMICYCLE_API_VERSION", API_VERSION).strip() or API_VERSION
    contact = os.getenv("APP_CONTACT", "").strip() or "contact-non-renseigne"
    client = session or resilient_session()
    try:
        response = client.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Hemicycle-Version": version,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"CapMarchesHackathon/2.0 (contact: {contact})",
            },
            timeout=timeout,
        )
        if response.status_code == 401:
            raise HemicycleError("Clé Hémicycle absente, expirée ou invalide.")
        if response.status_code == 402:
            raise HemicycleError("Crédits Hémicycle insuffisants.")
        response.raise_for_status()
        payload = response.json()
    except HemicycleError:
        raise
    except (requests.RequestException, ValueError) as exc:
        raise HemicycleError(f"Hémicycle est indisponible : {exc}") from exc
    return _extract_rows(payload)


def fetch_upcoming_projects(
    keyword: str,
    *,
    department: str = "",
    category: str = "",
    limit: int = 100,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Retourne les projets d'achat annoncés avant publication."""

    filters: list[dict[str, Any]] = []
    if department.strip():
        filters.append(
            {
                "colonne": "departement_s_d_execution_du_marche",
                "op": "like",
                "valeur": f"%{department.strip()}%",
            }
        )
    if category.strip():
        filters.append(
            {
                "colonne": "categorie_d_achat",
                "op": "eq",
                "valeur": category.strip(),
            }
        )
    return query_dataset(
        UPCOMING_DATASET,
        filters=filters,
        search=keyword,
        sort="date_previsionnelle_de_publication",
        limit=limit,
        session=session,
    )


def fetch_contracts(
    keyword: str,
    *,
    department: str = "",
    limit: int = 100,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Retourne les marchés déjà notifiés."""

    filters = []
    if department.strip():
        filters.append(
            {
                "colonne": "lieuexecution_code",
                "op": "eq",
                "valeur": department.strip(),
            }
        )
    return query_dataset(
        CONTRACTS_DATASET,
        filters=filters,
        search=keyword,
        sort="datenotification",
        limit=limit,
        session=session,
    )


def fetch_organizations(
    identifiers: Iterable[str],
    *,
    identifier_type: str,
    limit: int = 100,
    session: requests.Session | None = None,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """Enrichit un lot de SIREN ou de SIRET via le répertoire Sirene avec mise en cache local."""

    column = identifier_type.lower().strip()
    if column not in {"siren", "siret"}:
        raise ValueError("identifier_type doit valoir 'siren' ou 'siret'.")

    all_ids = list(
        dict.fromkeys(str(value).strip() for value in identifiers if str(value).strip())
    )
    if not all_ids:
        return []

    # 1. Consulter le cache local persistant
    cached_map: dict[str, dict[str, Any]] = {}
    if use_cache:
        try:
            import storage

            cached_map = storage.get_cached_organizations(all_ids, column)
        except Exception:
            cached_map = {}

    # Identifiants manquants qui doivent être interrogés via l'API
    missing_ids = [val for val in all_ids if val not in cached_map]

    maximum_identifiers = max(1, min(int(os.getenv("MAX_SIRENE_ENRICHMENTS", "5")), 20))
    to_fetch = missing_ids[:maximum_identifiers]

    # Le jeu Sirene accepte uniquement `eq` sur SIREN/SIRET, pas `in`.
    # On borne donc le nombre d'acheteurs et on respecte une requête/seconde.
    rows: list[dict[str, Any]] = []
    last_error: HemicycleError | None = None
    for index, value in enumerate(to_fetch):
        if index and session is None:
            time.sleep(1.05)
        filters: list[dict[str, Any]] = [
            {"colonne": column, "op": "eq", "valeur": value}
        ]
        if column == "siren":
            filters.append({"colonne": "siege", "op": "eq", "valeur": True})
        filters.append({"colonne": "etat_administratif", "op": "eq", "valeur": "A"})
        try:
            new_results = query_dataset(
                SIRENE_DATASET,
                filters=filters,
                sort="siret",
                limit=min(limit, 100),
                session=session,
            )
            rows.extend(new_results)
        except HemicycleError as exc:
            last_error = exc

    # Sauvegarder les nouvelles organisations en cache local
    if rows and use_cache:
        try:
            import storage

            storage.cache_organizations(rows, column)
        except Exception:
            pass

    # Combiner les organisations issues du cache et celles nouvellement récupérées
    combined: list[dict[str, Any]] = list(cached_map.values()) + rows
    if not combined and last_error:
        raise last_error
    return combined[:limit]
