"""Normalisation et score transparent des signaux commerciaux."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Iterable

import pandas as pd


DISPLAY_COLUMNS = [
    "objet",
    "montant",
    "datenotification",
    "dureemois",
    "date_fin_estimee",
    "lieuexecution_code",
    "acheteur_id",
    "score",
]


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zà-ÿ0-9]+", str(text).lower())
        if len(token) >= 3
    }


def keyword_points(objet: str, query: str) -> int:
    wanted = _tokens(query)
    if not wanted:
        return 0
    found = _tokens(objet)
    ratio = len(wanted & found) / len(wanted)
    return round(30 * ratio)


def location_points(location: Any, target: str) -> int:
    target = target.strip().lower()
    if not target:
        return 10  # filtre neutre : ne favorise aucun territoire
    value = str(location or "").strip().lower()
    return 20 if value.startswith(target) or target in value else 0


def amount_points(amount: Any, minimum: float, maximum: float) -> int:
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return 0
    if minimum <= value <= maximum:
        return 20
    tolerance = max((maximum - minimum) * 0.5, 10_000)
    if minimum - tolerance <= value <= maximum + tolerance:
        return 10
    return 0


def renewal_points(end_date: Any, today: date | None = None) -> int:
    if pd.isna(end_date):
        return 0
    now = pd.Timestamp(today or date.today())
    months = (pd.Timestamp(end_date).year - now.year) * 12 + (
        pd.Timestamp(end_date).month - now.month
    )
    if 0 <= months <= 12:
        return 30
    if 13 <= months <= 24:
        return 20
    if 25 <= months <= 36:
        return 10
    return 0


def score_contracts(
    records: Iterable[dict[str, Any]],
    *,
    keyword: str,
    location: str = "",
    minimum: float = 0,
    maximum: float = 1_000_000,
    today: date | None = None,
) -> pd.DataFrame:
    """Normalise, enrichit et classe les contrats par score d'intérêt."""

    frame = pd.DataFrame(list(records))
    if frame.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)

    aliases = {
        "dateNotification": "datenotification",
        "dureeMois": "dureemois",
        "lieuExecutionCode": "lieuexecution_code",
        "acheteurId": "acheteur_id",
    }
    frame = frame.rename(columns={k: v for k, v in aliases.items() if k in frame})
    for column in (
        "objet",
        "montant",
        "datenotification",
        "dureemois",
        "lieuexecution_code",
        "acheteur_id",
    ):
        if column not in frame:
            frame[column] = None

    frame["montant"] = pd.to_numeric(frame["montant"], errors="coerce")
    frame["dureemois"] = pd.to_numeric(frame["dureemois"], errors="coerce")
    frame["datenotification"] = pd.to_datetime(
        frame["datenotification"], errors="coerce"
    )
    frame["date_fin_estimee"] = frame.apply(
        lambda row: (
            row["datenotification"] + pd.DateOffset(months=int(row["dureemois"]))
            if pd.notna(row["datenotification"]) and pd.notna(row["dureemois"])
            else pd.NaT
        ),
        axis=1,
    )

    frame["score_mots"] = frame["objet"].map(
        lambda value: keyword_points(str(value or ""), keyword)
    )
    frame["score_territoire"] = frame["lieuexecution_code"].map(
        lambda value: location_points(value, location)
    )
    frame["score_montant"] = frame["montant"].map(
        lambda value: amount_points(value, minimum, maximum)
    )
    frame["score_renouvellement"] = frame["date_fin_estimee"].map(
        lambda value: renewal_points(value, today)
    )
    frame["score"] = frame[
        [
            "score_mots",
            "score_territoire",
            "score_montant",
            "score_renouvellement",
        ]
    ].sum(axis=1)
    return frame.sort_values(
        ["score", "montant"], ascending=[False, False], na_position="last"
    ).reset_index(drop=True)

