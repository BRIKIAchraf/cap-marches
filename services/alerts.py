"""Service d'alerte et de veille automatique sur les marchés publics.

Exécute les recherches sauvegardées, identifie les nouvelles opportunités
(diff par rapport aux marchés déjà vus), et diffuse des synthèses d'alerte
par webhook (Slack/Discord/Teams), email SMTP ou log d'audit.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

import storage
from scoring import score_contracts, score_projects
from services import decp, hemicycle
from services.http import resilient_session
from services.semantic import semantic_scores


def format_digest_markdown(
    search_name: str,
    new_opportunities: list[dict[str, Any]],
    analysis: str,
) -> str:
    """Génère un rapport textuel clair et percutant des nouveaux signaux."""
    is_future = analysis == "future"
    lines = [
        f"🎯 **Alerte Cap Marchés · {search_name}**",
        f"📅 Date : {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M UTC')}",
        f"🔔 **{len(new_opportunities)} nouvelle(s) opportunité(s)** détectée(s) :",
        "",
    ]
    for idx, opp in enumerate(new_opportunities[:10], start=1):
        title = opp.get("libelle") if is_future else opp.get("objet")
        buyer = opp.get("denomination_acheteur") or "Acheteur public"
        score = int(opp.get("score", 0))
        budget = (
            opp.get("montant_estime_du_marche") if is_future else opp.get("montant")
        )
        budget_str = f"Budget : {budget}" if budget else "Budget non renseigné"
        lines.append(f"**{idx}. [{score}/100]** {title}")
        lines.append(f"   🏢 {buyer} | 💶 {budget_str}")
        if is_future:
            pub_date = opp.get("date_previsionnelle_de_publication")
            if pub_date:
                lines.append(f"   🗓️ Publication prévue : {str(pub_date)[:10]}")
        else:
            end_date = opp.get("date_fin_estimee")
            if end_date:
                lines.append(f"   ⏳ Fin estimée du marché : {str(end_date)[:10]}")
        lines.append("")
    return "\n".join(lines)


def dispatch_webhook(webhook_url: str, text: str) -> bool:
    """Envoie une notification formatée vers un webhook Discord, Slack ou Teams."""
    if not webhook_url:
        return False
    payload = {"text": text, "content": text}
    session = resilient_session()
    try:
        resp = session.post(webhook_url, json=payload, timeout=10.0)
        return resp.status_code in (200, 204)
    except requests.RequestException:
        return False


def run_single_search(search: dict[str, Any]) -> dict[str, Any]:
    """Exécute une veille unitaire et retourne les nouvelles opportunités."""
    query = search.get("query", {})
    name = search.get("name", "Veille sans nom")
    analysis = query.get("analysis", "future")
    keyword = query.get("keyword", "").strip()
    department = query.get("department", "").strip()
    category = query.get("category", "")
    minimum = float(query.get("minimum", 0) or 0)
    maximum = float(query.get("maximum", 1_000_000) or 1_000_000)
    limit = int(query.get("limit", 50) or 50)

    # 1. Collecte des données
    records: list[dict[str, Any]] = []
    dataset = "projets_achats_publics" if analysis == "future" else "marches_publics"
    if analysis == "future":
        if hemicycle.is_configured():
            try:
                records = hemicycle.fetch_upcoming_projects(
                    keyword, department=department, category=category, limit=limit
                )
            except hemicycle.HemicycleError:
                records = []
        if not records:
            return {
                "search_name": name,
                "total_found": 0,
                "new_count": 0,
                "new_records": [],
                "status": "no_results_from_source",
                "channel": "none",
            }
    else:
        if hemicycle.is_configured():
            try:
                records = hemicycle.fetch_contracts(
                    keyword, department=department, limit=limit
                )
            except hemicycle.HemicycleError:
                records = []
        if not records:
            try:
                records = decp.fetch_contracts(keyword, limit=limit)
            except decp.DecpError:
                records = []
        if not records:
            return {
                "search_name": name,
                "total_found": 0,
                "new_count": 0,
                "new_records": [],
                "status": "no_results_from_source",
                "channel": "none",
            }

    if not records:
        return {
            "search_name": name,
            "total_found": 0,
            "new_count": 0,
            "new_records": [],
            "status": "no_results_from_source",
            "channel": "none",
        }

    # 2. Scoring
    keys = (
        ("libelle", "description", "code_s_cpv", "categorie_d_achat")
        if analysis == "future"
        else ("objet", "codecpv", "nature")
    )
    docs = [" ".join(str(r.get(k, "") or "") for k in keys) for r in records]
    semantics = semantic_scores(keyword, docs)
    scoring_args = {
        "keyword": keyword,
        "location": department,
        "minimum": minimum,
        "maximum": maximum,
        "semantic_scores": semantics,
    }
    if analysis == "future":
        scored_frame = score_projects(records, **scoring_args)
    else:
        scored_frame = score_contracts(records, **scoring_args)

    scored_records = scored_frame.to_dict(orient="records")

    # 3. Enrichissement Sirene avec le cache local
    id_key = "siren_de_l_entite_acheteuse" if analysis == "future" else "acheteur_id"
    id_type = "siren" if analysis == "future" else "siret"
    buyer_ids = [
        str(r.get(id_key, "")).strip() for r in scored_records if r.get(id_key)
    ]
    if buyer_ids and hemicycle.is_configured():
        try:
            orgs = hemicycle.fetch_organizations(
                buyer_ids[:20], identifier_type=id_type
            )
            org_map = {str(o.get(id_type)): o for o in orgs if o.get(id_type)}
            for r in scored_records:
                match = org_map.get(str(r.get(id_key)))
                if match:
                    r["denomination_acheteur"] = match.get("denomination")
                    r["commune_acheteur"] = match.get("commune")
        except Exception:
            pass

    # 4. Détection du diff : nouveauté par rapport aux marchés déjà vus
    is_new_flags = storage.mark_opportunities_seen(scored_records, dataset)
    new_records = [rec for rec, is_new in zip(scored_records, is_new_flags) if is_new]

    # 5. Diffusion de l'alerte si de nouvelles opportunités sont détectées
    webhook_url = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    status = "completed"
    channel = "internal_log"
    if new_records and webhook_url:
        digest = format_digest_markdown(name, new_records, analysis)
        sent = dispatch_webhook(webhook_url, digest)
        channel = "webhook"
        status = "sent" if sent else "webhook_failed"

    storage.log_alert_run(
        search_name=name,
        new_count=len(new_records),
        channel=channel,
        status=status,
        details={
            "total_analyzed": len(scored_records),
            "new_count": len(new_records),
            "top_opportunity": new_records[0].get("libelle")
            or new_records[0].get("objet")
            if new_records
            else None,
        },
    )

    return {
        "search_name": name,
        "total_found": len(scored_records),
        "new_count": len(new_records),
        "new_records": new_records,
        "status": status,
        "channel": channel,
    }


def run_all_alerts(force_all: bool = False) -> list[dict[str, Any]]:
    """Parcourt l'ensemble des veilles enregistrées avec alertes activées."""
    searches = storage.list_saved_searches()
    targets = [s for s in searches if s.get("alerts_enabled") or force_all]
    results: list[dict[str, Any]] = []
    for s in targets:
        res = run_single_search(s)
        results.append(res)
    return results
