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

