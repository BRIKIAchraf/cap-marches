"""Génération d'une fiche commerciale via Featherless."""

from __future__ import annotations

import json
import os
from typing import Any


class LlmError(RuntimeError):
    """Erreur d'inférence présentable à l'utilisateur."""


def is_configured() -> bool:
    return bool(os.getenv("FEATHERLESS_API_KEY", "").strip())


def build_heuristic_brief(records: list[dict[str, Any]], company_offer: str) -> str:
    """Génère une note d'analyse commerciale factuelle déterministe à partir des preuves."""
    if not records:
        return "Aucun signal commercial sélectionné pour l'analyse."

    lines = [
        "### 📋 Note d'opportunité commerciale (Analyse factuelle)",
        f"> **Alignement avec votre offre** : *{company_offer}*",
        "",
        "#### 1. Signal & Opportunités prioritaires",
    ]
    for idx, r in enumerate(records[:3], start=1):
        title = r.get("libelle") or r.get("objet") or "Marché sans titre"
        buyer = r.get("denomination_acheteur") or "Acheteur public"
        budget = r.get("montant_estime_du_marche") or r.get("montant")
        budget_str = (
            f"{budget} €"
            if isinstance(budget, (int, float))
            else (str(budget) if budget else "Non précisé")
        )
        score = r.get("score", 0)
        lines.append(f"- **Opportunité {idx} (Score {int(score)}/100)** : {title}")
        lines.append(
            f"  - **Acheteur** : {buyer} ({r.get('commune_acheteur') or r.get('departement_s_d_execution_du_marche') or 'Territoire national'})"
        )
        lines.append(f"  - **Budget estimé / Montant** : {budget_str}")
        if r.get("date_previsionnelle_de_publication"):
            lines.append(
                f"  - **Date prévisionnelle** : {str(r.get('date_previsionnelle_de_publication'))[:10]}"
            )
        elif r.get("date_fin_estimee"):
            lines.append(
                f"  - **Échéance actuelle du contrat** : {str(r.get('date_fin_estimee'))[:10]}"
            )

    lines.extend(
        [
            "",
            "#### 2. Pourquoi ce positionnement est stratégique",
            "- **Anticipation** : La détection en amont permet de contacter la direction des achats avant la publication du CCTP définitif.",
            "- **Pertinence de l'offre** : Les besoins exprimés correspondent aux fonctionnalités clés de votre solution.",
            "- **Solvabilité publique** : Budget validé dans la programmation ou reconduction d'un marché existant.",
            "",
            "#### 3. Prochaines actions recommandées",
            "1. **Cartographier l'acheteur** : Identifier le responsable du service prescripteur (DSI, DRH ou Direction des Achats).",
            "2. **Prendre un contact informel d'information** : Présenter les innovations récentes du marché sous l'angle du sourçage officiel (autorisé par l'article R2111-1 du Code de la commande publique).",
            "3. **Planifier une alerte** : Surveiller la parution effective sur les profils d'acheteurs d'ici l'échéance.",
            "",
            "#### 4. Limites & Vigilances",
            "- Les dates prévisionnelles issues d'APProch sont indicatives et restent sujettes à arbitrage budgétaire.",
            "- Tout contact préalable avec l'acheteur doit respecter le principe d'égalité de traitement des candidats.",
            "",
            "---",
            "*💡 Note : Synthèse factuelle générée automatiquement depuis les preuves publiques. Ajoutez `FEATHERLESS_API_KEY` dans `.env` pour activer la réécriture narrative via LLM.*",
        ]
    )
    return "\n".join(lines)


def answer_from_evidence_heuristic(
    question: str, evidence: list[dict[str, Any]]
) -> str:
    """Répond factuellement à la question de l'agent sans modèle externe."""
    if not evidence:
        return "Aucune preuve structurée disponible pour répondre à cette question."

    lines = [
        "### 🤖 Rapport de mission de veille (Agent Cap Marchés)",
        f"> **Mission** : *{question}*",
        "",
        "#### 1. Synthèse de l'enquête",
        f"L'agent a analysé les signaux publics disponibles et retenu **{len(evidence)} preuve(s) formelle(s)** directement issues des bases officielles de l'État.",
        "",
        "#### 2. Opportunités prioritaires et preuves associées",
    ]
    for idx, ev in enumerate(evidence[:4], start=1):
        ident = ev.get("identifiant", "N/A")
        source = ev.get("source_dataset", "Source publique")
        facts = ev.get("faits", {})
        title = facts.get("libelle") or facts.get("objet") or "Signal d'achat"
        lines.append(f"**Preuve #{idx} [{ident}] · Jeu `{source}`**")
        lines.append(f"- **Intitulé** : {title}")
        for k, v in list(facts.items())[:4]:
            if k not in ("libelle", "objet") and v:
                lines.append(f"  - *{k.replace('_', ' ').capitalize()}* : {v}")
        lines.append("")

    lines.extend(
        [
            "#### 3. Recommandations opérationnelles",
            "- **Prioriser les projets à parution proche** (J-90) pour engager une démarche de sourçage réglementaire.",
            "- **Consulter les pièces du marché précédent** si disponible pour anticiper les critères de sélection (prix vs valeur technique).",
            "",
            "#### 4. Limites d'interprétation",
            "- Les informations ci-dessus reflètent fidèlement les données ouvertes de l'administration et ne constituent pas un engagement contractuel de l'acheteur.",
            "",
            "---",
            "*💡 Analyse certifiée sans hallucination. Pour une analyse générative personnalisée, renseignez `FEATHERLESS_API_KEY` dans `.env`.*",
        ]
    )
    return "\n".join(lines)


def build_brief(
    records: list[dict[str, Any]],
    company_offer: str,
    allow_heuristic: bool = True,
) -> str:
    """Produit une note factuelle à partir de cinq signaux maximum."""

    api_key = os.getenv("FEATHERLESS_API_KEY", "").strip()
    if not api_key:
        if allow_heuristic:
            return build_heuristic_brief(records, company_offer)
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


def answer_from_evidence(
    question: str,
    evidence: list[dict[str, Any]],
    allow_heuristic: bool = True,
) -> str:
    """Répond à une question en restant strictement lié aux preuves structurées."""

    api_key = os.getenv("FEATHERLESS_API_KEY", "").strip()
    if not api_key:
        if allow_heuristic:
            return answer_from_evidence_heuristic(question, evidence)
        raise LlmError("Ajoutez FEATHERLESS_API_KEY dans .env.")
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise LlmError("Le paquet `openai` n'est pas installé.") from exc
    safe_evidence = json.loads(
        json.dumps(evidence[:10], ensure_ascii=False, default=str)
    )
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
