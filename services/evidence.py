"""Construction de dossiers de preuves transmis au LLM et à l'interface."""

from __future__ import annotations

from typing import Any


def project_evidence(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "opportunity_id": record.get("code"),
        "source_dataset": "projets_achats_publics",
        "source_url": record.get("lien_vers_la_consultation"),
        "buyer_id": record.get("siren_de_l_entite_acheteuse"),
        "buyer_name": record.get("denomination_acheteur"),
        "facts": {
            "project": record.get("libelle"),
            "category": record.get("categorie_d_achat"),
            "budget": record.get("montant_estime_du_marche"),
            "publication_date": record.get("date_previsionnelle_de_publication"),
            "deadline": record.get("date_cible_de_remise_des_offres"),
            "departments": record.get("departement_s_d_execution_du_marche"),
        },
        "score": record.get("score"),
        "score_components": {
            "semantic": record.get("score_semantique", 0),
            "keywords": record.get("score_mots", 0),
            "territory": record.get("score_territoire", 0),
            "budget": record.get("score_montant", 0),
            "timing": record.get("score_calendrier", 0),
        },
    }


def contract_evidence(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "opportunity_id": f"{record.get('acheteur_id')}:{record.get('id')}",
        "source_dataset": "marches_publics",
        "buyer_id": record.get("acheteur_id"),
        "buyer_name": record.get("denomination_acheteur"),
        "facts": {
            "object": record.get("objet"),
            "amount": record.get("montant"),
            "notification_date": record.get("datenotification"),
            "duration_months": record.get("dureemois"),
            "estimated_end": record.get("date_fin_estimee"),
            "location": record.get("lieuexecution_code"),
        },
        "score": record.get("score"),
        "score_components": {
            "semantic": record.get("score_semantique", 0),
            "keywords": record.get("score_mots", 0),
            "territory": record.get("score_territoire", 0),
            "budget": record.get("score_montant", 0),
            "renewal": record.get("score_renouvellement", 0),
        },
    }
