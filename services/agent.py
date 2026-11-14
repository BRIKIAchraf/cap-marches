"""Agent déterministe de veille : planifie, appelle les outils et cite ses preuves.

Le LLM ne choisit pas librement les sources. L'orchestrateur exécute un plan
contrôlé, classe les résultats, puis lui confie uniquement une synthèse factuelle.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

from observability import event
from scoring import score_contracts, score_projects
from services import hemicycle
from services.evidence import contract_evidence, project_evidence
from services.semantic import semantic_scores


@dataclass(frozen=True)
class AgentPlan:
    query: str
    department: str
    category: str
    minimum: float
    maximum: float
    include_history: bool = True
    enrich_buyers: bool = True


def build_plan(profile: dict[str, Any], question: str = "") -> AgentPlan:
    query = " ".join(
        part for part in (profile.get("offer", ""), profile.get("keywords", ""), question) if part
    ).strip()
    if not query:
        raise ValueError("Le profil doit décrire une offre ou des mots-clés.")
    return AgentPlan(
        query=query,
        department=str(profile.get("departments", "")).split(",")[0].strip(),
        category=str(profile.get("category", "")).strip(),
        minimum=float(profile.get("minimum", 0) or 0),
        maximum=float(profile.get("maximum", 1_000_000) or 1_000_000),
    )


def _project_text(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(key, "") or "") for key in ("libelle", "description", "code_s_cpv", "categorie_d_achat"))


def _contract_text(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(key, "") or "") for key in ("objet", "codecpv", "nature"))


def run_agent(
    profile: dict[str, Any],
    question: str = "",
    *,
    project_fetcher: Callable[..., list[dict[str, Any]]] = hemicycle.fetch_upcoming_projects,
    contract_fetcher: Callable[..., list[dict[str, Any]]] = hemicycle.fetch_contracts,
    organization_fetcher: Callable[..., list[dict[str, Any]]] = hemicycle.fetch_organizations,
    limit: int | None = None,
) -> dict[str, Any]:
    """Exécute une veille bornée et retourne résultats, preuves et trace du plan."""

    plan = build_plan(profile, question)
    bounded_limit = max(1, min(limit or int(os.getenv("MAX_AGENT_RESULTS", "20")), 100))
    event("agent_started", limit=bounded_limit, include_history=plan.include_history)
    projects = project_fetcher(
        plan.query,
        department=plan.department,
        category=plan.category,
        limit=bounded_limit,
    )
    project_semantics = semantic_scores(plan.query, [_project_text(row) for row in projects])
    project_frame = score_projects(
        projects,
        keyword=plan.query,
        location=plan.department,
        minimum=plan.minimum,
        maximum=plan.maximum,
        semantic_scores=project_semantics,
    )

    contracts: list[dict[str, Any]] = []
    contract_frame = score_contracts([], keyword=plan.query)
    if plan.include_history:
        contracts = contract_fetcher(
            plan.query, department=plan.department, limit=bounded_limit
        )
        contract_semantics = semantic_scores(plan.query, [_contract_text(row) for row in contracts])
        contract_frame = score_contracts(
            contracts,
            keyword=plan.query,
            location=plan.department,
            minimum=plan.minimum,
            maximum=plan.maximum,
            semantic_scores=contract_semantics,
        )

    buyer_ids = []
    if not project_frame.empty:
        buyer_ids.extend(project_frame["siren_de_l_entite_acheteuse"].dropna().astype(str).tolist())
    organizations = (
        organization_fetcher(buyer_ids[:100], identifier_type="siren", limit=100)
        if plan.enrich_buyers and buyer_ids
        else []
    )
    project_records = project_frame.head(bounded_limit).to_dict(orient="records")
    contract_records = contract_frame.head(bounded_limit).to_dict(orient="records")
    organization_by_siren = {
        str(row.get("siren")): row for row in organizations if row.get("siren")
    }
    for row in project_records:
        organization = organization_by_siren.get(
            str(row.get("siren_de_l_entite_acheteuse"))
        )
        if organization:
            row["denomination_acheteur"] = organization.get("denomination")
            row["commune_acheteur"] = organization.get("commune")
            row["activite_acheteur"] = organization.get("activite_principale")
    result = {
        "plan": {
            "query": plan.query,
            "department": plan.department,
            "category": plan.category,
            "amount_range": [plan.minimum, plan.maximum],
            "steps": [
                "Chercher les projets futurs",
                "Comparer l'historique",
                "Identifier les acheteurs",
                "Classer par pertinence hybride",
                "Construire les preuves",
            ],
        },
        "projects": project_records,
        "contracts": contract_records,
        "organizations": organizations,
        "evidence": [project_evidence(row) for row in project_records[:5]]
        + [contract_evidence(row) for row in contract_records[:5]],
    }
    event(
        "agent_completed",
        projects=len(project_records),
        contracts=len(contract_records),
        evidence=len(result["evidence"]),
    )
    return result
