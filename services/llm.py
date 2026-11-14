"""Génération d'une fiche commerciale via Featherless."""

from __future__ import annotations

import json
import os
from typing import Any


class LlmError(RuntimeError):
    """Erreur d'inférence présentable à l'utilisateur."""


def is_configured() -> bool:
    return bool(os.getenv("FEATHERLESS_API_KEY", "").strip())


def build_brief(records: list[dict[str, Any]], company_offer: str) -> str:
    """Produit une note factuelle à partir de cinq signaux maximum."""

    api_key = os.getenv("FEATHERLESS_API_KEY", "").strip()
    if not api_key:
        raise LlmError("Ajoutez FEATHERLESS_API_KEY dans .env.")

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        raise LlmError("Le paquet `openai` n'est pas installé.") from exc

    compact = []
    allowed = {
        "libelle",
        "description",
        "denomination_acheteur",
        "categorie_d_achat",
        "montant_estime_du_marche",
        "date_previsionnelle_de_publication",
        "date_cible_de_remise_des_offres",
        "departement_s_d_execution_du_marche",
        "lien_vers_la_consultation",
        "objet",
        "montant",
        "datenotification",
        "dureemois",
        "date_fin_estimee",
        "lieuexecution_code",
        "acheteur_id",
        "commune_acheteur",
        "score",
    }
    for record in records[:5]:
        compact.append({key: record.get(key) for key in allowed if key in record})

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.featherless.ai/v1",
    )
    model = os.getenv("FEATHERLESS_MODEL", "zai-org/GLM-5.2")
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=500,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un analyste commercial prudent. Utilise uniquement "
                        "les données fournies. N'invente ni nom d'organisation, ni "
                        "contact, ni date. Distingue clairement fait et estimation. "
                        "Réponds en français avec quatre rubriques courtes : Signal, "
                        "Pourquoi, Prochaine action, Limites."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"offre_entreprise": company_offer, "marches": compact},
                        ensure_ascii=False,
                        default=str,
                    ),
                },
            ],
        )
    except Exception as exc:  # SDK : plusieurs familles d'erreurs possibles
        raise LlmError(f"Featherless n'a pas répondu : {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise LlmError("Featherless a renvoyé une réponse vide.")
    return content


def answer_from_evidence(question: str, evidence: list[dict[str, Any]]) -> str:
    """Répond à une question en restant strictement lié aux preuves structurées."""

    api_key = os.getenv("FEATHERLESS_API_KEY", "").strip()
    if not api_key:
        raise LlmError("Ajoutez FEATHERLESS_API_KEY dans .env.")
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise LlmError("Le paquet `openai` n'est pas installé.") from exc
    safe_evidence = json.loads(json.dumps(evidence[:10], ensure_ascii=False, default=str))
    client = OpenAI(api_key=api_key, base_url="https://api.featherless.ai/v1")
    try:
        response = client.chat.completions.create(
            model=os.getenv("FEATHERLESS_MODEL", "zai-org/GLM-5.2"),
            temperature=0.1,
            max_tokens=700,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es l'agent Cap Marchés. Réponds uniquement à partir des "
                        "preuves JSON. Cite l'identifiant et le jeu source pour chaque "
                        "affirmation importante. Si une information manque, dis-le. "
                        "Structure : Réponse, Opportunités prioritaires, Actions, Limites."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"question": question, "preuves": safe_evidence},
                        ensure_ascii=False,
                    ),
                },
            ],
        )
    except Exception as exc:
        raise LlmError(f"Featherless n'a pas répondu : {exc}") from exc
    content = response.choices[0].message.content
    if not content:
        raise LlmError("Featherless a renvoyé une réponse vide.")
    return content

