"""Persistance des profils, recherches et labels d'apprentissage."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, MetaData, String, Table
from sqlalchemy import create_engine, delete, func, insert, select


ROOT = Path(__file__).resolve().parent
DEFAULT_DB = f"sqlite:///{(ROOT / 'data' / 'cap_marches.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=CONNECT_ARGS, pool_pre_ping=True)
metadata = MetaData()

profiles = Table(
    "profiles",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("company_name", String(200), nullable=False),
    Column("offer", String(2000), nullable=False),
    Column("keywords", String(1000), default=""),
    Column("cpv_codes", String(1000), default=""),
    Column("departments", String(500), default=""),
    Column("minimum", Float, default=0),
    Column("maximum", Float, default=1_000_000),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

feedback = Table(
    "feedback",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("opportunity_key", String(300), nullable=False, index=True),
    Column("label", String(50), nullable=False, index=True),
    Column("source_dataset", String(100), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

saved_searches = Table(
    "saved_searches",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(200), nullable=False),
    Column("query", JSON, nullable=False),
    Column("alerts_enabled", Boolean, default=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

sirene_cache = Table(
    "sirene_cache",
    metadata,
    Column("identifier", String(50), primary_key=True),
    Column("identifier_type", String(20), nullable=False, index=True),
    Column("denomination", String(300)),
    Column("commune", String(100)),
    Column("activite_principale", String(100)),
    Column("payload", JSON, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

seen_opportunities = Table(
    "seen_opportunities",
    metadata,
    Column("opportunity_key", String(300), primary_key=True),
    Column("source_dataset", String(100), nullable=False),
    Column("title", String(500), default=""),
    Column("first_seen_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
)

alerts_history = Table(
    "alerts_history",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("search_name", String(200), nullable=False),
    Column("new_count", Integer, default=0),
    Column("channel", String(50), nullable=False),
    Column("status", String(50), nullable=False),
    Column("details", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


def configure_database(url: str) -> None:
    """Reconfigure la base, notamment pour les tests et les workers."""

    global engine, DATABASE_URL
    DATABASE_URL = url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine.dispose()
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def init_db() -> None:
    metadata.create_all(engine)


def load_profile() -> dict[str, Any] | None:
    init_db()
    with engine.begin() as connection:
        row = connection.execute(select(profiles).where(profiles.c.id == 1)).mappings().first()
    return dict(row) if row else None


def save_profile(profile: dict[str, Any]) -> None:
    init_db()
    values = {
        "id": 1,
        "company_name": str(profile.get("company_name", "")).strip(),
        "offer": str(profile.get("offer", "")).strip(),
        "keywords": str(profile.get("keywords", "")).strip(),
        "cpv_codes": str(profile.get("cpv_codes", "")).strip(),
        "departments": str(profile.get("departments", "")).strip(),
        "minimum": float(profile.get("minimum", 0)),
        "maximum": float(profile.get("maximum", 1_000_000)),
        "updated_at": datetime.now(timezone.utc),
    }
    if not values["company_name"] or not values["offer"]:
        raise ValueError("Le nom de l'entreprise et son offre sont obligatoires.")
    with engine.begin() as connection:
        connection.execute(delete(profiles).where(profiles.c.id == 1))
        connection.execute(insert(profiles).values(**values))


def record_feedback(
    opportunity_key: str,
    label: str,
    source_dataset: str,
    payload: dict[str, Any],
) -> None:
    allowed = {"pertinent", "non_pertinent", "a_contacter", "contacte", "gagne", "perdu"}
    if label not in allowed:
        raise ValueError(f"Label non autorisé : {label}")
    init_db()
    safe_payload = json.loads(json.dumps(payload, ensure_ascii=False, default=str))
    with engine.begin() as connection:
        connection.execute(
            insert(feedback).values(
                opportunity_key=opportunity_key,
                label=label,
                source_dataset=source_dataset,
                payload=safe_payload,
                created_at=datetime.now(timezone.utc),
            )
        )


def feedback_counts() -> dict[str, int]:
    init_db()
    with engine.begin() as connection:
        rows = connection.execute(
            select(feedback.c.label, func.count()).group_by(feedback.c.label)
        ).all()
    return {str(label): int(count) for label, count in rows}


def save_search(name: str, query: dict[str, Any], alerts_enabled: bool = False) -> None:
    if not name.strip():
        raise ValueError("Le nom de la recherche est obligatoire.")
    init_db()
    with engine.begin() as connection:
        connection.execute(
            insert(saved_searches).values(
                name=name.strip(),
                query=json.loads(json.dumps(query, default=str)),
                alerts_enabled=bool(alerts_enabled),
                created_at=datetime.now(timezone.utc),
            )
        )


def list_saved_searches() -> list[dict[str, Any]]:
    init_db()
    with engine.begin() as connection:
        rows = connection.execute(
            select(saved_searches).order_by(saved_searches.c.created_at.desc())
        ).mappings()
        return [dict(row) for row in rows]


def get_cached_organizations(
    identifiers: Iterable[str], identifier_type: str
) -> dict[str, dict[str, Any]]:
    """Récupère les organisations déjà mises en cache local."""
    init_db()
    type_col = identifier_type.lower().strip()
    clean_ids = [str(i).strip() for i in identifiers if str(i).strip()]
    if not clean_ids:
        return {}
    with engine.begin() as connection:
        query = select(sirene_cache).where(
            sirene_cache.c.identifier_type == type_col,
            sirene_cache.c.identifier.in_(clean_ids),
        )
        rows = connection.execute(query).mappings().all()
    cached = {}
    for row in rows:
        cached[row["identifier"]] = {
            row["identifier_type"]: row["identifier"],
            "denomination": row["denomination"],
            "commune": row["commune"],
            "activite_principale": row["activite_principale"],
            **(row["payload"] or {}),
        }
    return cached


def cache_organizations(
    organizations: Iterable[dict[str, Any]], identifier_type: str
) -> None:
    """Enregistre ou actualise les informations d'organisations en cache."""
    init_db()
    type_col = identifier_type.lower().strip()
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        for org in organizations:
            identifier = str(org.get(type_col, "")).strip()
            if not identifier:
                continue
            denomination = str(org.get("denomination", "") or org.get("denomination_acheteur", "")).strip()
            commune = str(org.get("commune", "") or org.get("commune_acheteur", "")).strip()
            activite = str(org.get("activite_principale", "") or org.get("activite_acheteur", "")).strip()
            payload = json.loads(json.dumps(org, ensure_ascii=False, default=str))

            connection.execute(
                delete(sirene_cache).where(
                    sirene_cache.c.identifier == identifier,
                    sirene_cache.c.identifier_type == type_col,
                )
            )
            connection.execute(
                insert(sirene_cache).values(
                    identifier=identifier,
                    identifier_type=type_col,
                    denomination=denomination or None,
                    commune=commune or None,
                    activite_principale=activite or None,
                    payload=payload,
                    updated_at=now,
                )
            )


def extract_opportunity_key(record: dict[str, Any]) -> str:
    """Extrait une clé unique et pérenne pour un projet ou marché."""
    return str(
        record.get("code")
        or record.get("id")
        or f"{record.get('acheteur_id', '')}:{record.get('objet', '')}"
    ).strip()


def mark_opportunities_seen(
    records: list[dict[str, Any]], source_dataset: str
) -> list[bool]:
    """Marque les opportunités comme vues et retourne pour chacune si elle est NOUVELLE (True) ou déjà vue (False)."""
    init_db()
    if not records:
        return []
    now = datetime.now(timezone.utc)
    results: list[bool] = []
    with engine.begin() as connection:
        for record in records:
            key = extract_opportunity_key(record)
            title = str(record.get("libelle") or record.get("objet") or "Sans titre")[:490]
            row = connection.execute(
                select(seen_opportunities).where(seen_opportunities.c.opportunity_key == key)
            ).mappings().first()
            if row is None:
                connection.execute(
                    insert(seen_opportunities).values(
                        opportunity_key=key,
                        source_dataset=source_dataset,
                        title=title,
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                )
                results.append(True)
            else:
                connection.execute(
                    delete(seen_opportunities).where(seen_opportunities.c.opportunity_key == key)
                )
                connection.execute(
                    insert(seen_opportunities).values(
                        opportunity_key=key,
                        source_dataset=source_dataset,
                        title=title,
                        first_seen_at=row["first_seen_at"],
                        last_seen_at=now,
                    )
                )
                results.append(False)
    return results


def seen_stats() -> dict[str, int]:
    """Statistiques sur les signaux observés."""
    init_db()
    with engine.begin() as connection:
        count = connection.execute(select(func.count()).select_from(seen_opportunities)).scalar() or 0
        cache_count = connection.execute(select(func.count()).select_from(sirene_cache)).scalar() or 0
    return {"seen_total": int(count), "sirene_cached": int(cache_count)}


def log_alert_run(
    search_name: str,
    new_count: int,
    channel: str,
    status: str,
    details: dict[str, Any],
) -> None:
    init_db()
    safe_details = json.loads(json.dumps(details, ensure_ascii=False, default=str))
    with engine.begin() as connection:
        connection.execute(
            insert(alerts_history).values(
                search_name=search_name,
                new_count=new_count,
                channel=channel,
                status=status,
                details=safe_details,
                created_at=datetime.now(timezone.utc),
            )
        )


def list_alert_history(limit: int = 10) -> list[dict[str, Any]]:
    init_db()
    with engine.begin() as connection:
        rows = connection.execute(
            select(alerts_history).order_by(alerts_history.c.created_at.desc()).limit(limit)
        ).mappings().all()
        return [dict(r) for r in rows]


