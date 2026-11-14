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

PROJECT_DISPLAY_COLUMNS = [
    "libelle",
    "denomination_acheteur",
    "categorie_d_achat",
    "montant_estime_du_marche",
    "date_previsionnelle_de_publication",
    "date_cible_de_remise_des_offres",
    "departement_s_d_execution_du_marche",
    "lien_vers_la_consultation",
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


def publication_points(publication_date: Any, today: date | None = None) -> int:
    """Favorise les projets dont la publication est proche mais pas dépassée."""

    if pd.isna(publication_date):
        return 0
    now = pd.Timestamp(today or date.today()).normalize()
    target = pd.Timestamp(publication_date).normalize()
    days = (target - now).days
    if 0 <= days <= 90:
        return 30
    if 91 <= days <= 180:
        return 25
    if 181 <= days <= 365:
        return 15
    if days > 365:
        return 5
    if -30 <= days < 0:
        return 5
    return 0


def parse_amount_range(value: Any) -> tuple[float | None, float | None]:
    """Convertit les tranches APProch (`100k - 500k`, `1M - 5M`, `+100M`)."""

    if value is None or pd.isna(value):
        return None, None
    text = str(value).lower().replace("\u202f", "").replace(" ", "")
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*([km]?)", text)
    if not matches:
        return None, None

    def convert(number: str, unit: str) -> float:
        multiplier = {"": 1.0, "k": 1_000.0, "m": 1_000_000.0}[unit]
        return float(number.replace(",", ".")) * multiplier

    numbers = [convert(number, unit) for number, unit in matches]
    if len(numbers) == 1:
        return (
            (numbers[0], float("inf"))
            if text.startswith("+")
            else (
                numbers[0],
                numbers[0],
            )
        )
    return min(numbers[0], numbers[1]), max(numbers[0], numbers[1])


def estimated_amount_points(value: Any, minimum: float, maximum: float) -> int:
    low, high = parse_amount_range(value)
    if low is None or high is None:
        return 0
    if low <= maximum and high >= minimum:
        return 20
    tolerance = max((maximum - minimum) * 0.5, 10_000)
    if low <= maximum + tolerance and high >= max(0, minimum - tolerance):
        return 10
    return 0


def score_projects(
    records: Iterable[dict[str, Any]],
    *,
    keyword: str,
    location: str = "",
    minimum: float = 0,
    maximum: float = 1_000_000,
    today: date | None = None,
    semantic_scores: Iterable[float] | None = None,
) -> pd.DataFrame:
    """Normalise et classe les projets d'achats futurs d'APProch."""

    frame = pd.DataFrame(list(records))
    if frame.empty:
        return pd.DataFrame(columns=PROJECT_DISPLAY_COLUMNS)
    for column in (
        "code",
        "libelle",
        "description",
        "statut",
        "siren_de_l_entite_acheteuse",
        "categorie_d_achat",
        "code_s_cpv",
        "date_previsionnelle_de_publication",
        "date_cible_de_remise_des_offres",
        "lien_vers_la_consultation",
        "montant_estime_du_marche",
        "duree_previsionnelle_du_marche",
        "departement_s_d_execution_du_marche",
    ):
        if column not in frame:
            frame[column] = None

    frame["date_previsionnelle_de_publication"] = pd.to_datetime(
        frame["date_previsionnelle_de_publication"], errors="coerce"
    )
    frame["date_cible_de_remise_des_offres"] = pd.to_datetime(
        frame["date_cible_de_remise_des_offres"], errors="coerce"
    )
    combined_text = (
        frame["libelle"].fillna("").astype(str)
        + " "
        + frame["description"].fillna("").astype(str)
    )
    frame["score_mots"] = combined_text.map(
        lambda value: keyword_points(value, keyword)
    )
    frame["score_territoire"] = frame["departement_s_d_execution_du_marche"].map(
        lambda value: location_points(value, location)
    )
    frame["score_montant"] = frame["montant_estime_du_marche"].map(
        lambda value: estimated_amount_points(value, minimum, maximum)
    )
    frame["score_calendrier"] = frame["date_previsionnelle_de_publication"].map(
        lambda value: publication_points(value, today)
    )
    if semantic_scores is None:
        frame["score_semantique"] = 0
        frame["score"] = frame[
            ["score_mots", "score_territoire", "score_montant", "score_calendrier"]
        ].sum(axis=1)
    else:
        values = list(semantic_scores)
        if len(values) != len(frame):
            raise ValueError(
                "Le nombre de scores sémantiques doit correspondre aux lignes."
            )
        frame["score_semantique"] = [
            round(max(0.0, min(1.0, value)) * 35) for value in values
        ]
        # Score hybride sur 100 : sens 35, mots 15, territoire 15,
        # montant 15, calendrier 20. Les composantes brutes restent visibles.
        frame["score"] = (
            (
                frame["score_semantique"]
                + (frame["score_mots"] * 0.5).round()
                + (frame["score_territoire"] * 0.75).round()
                + (frame["score_montant"] * 0.75).round()
                + (frame["score_calendrier"] * (2 / 3)).round()
            )
            .clip(0, 100)
            .astype(int)
        )
    return frame.sort_values(
        ["score", "date_previsionnelle_de_publication"],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)


def score_contracts(
    records: Iterable[dict[str, Any]],
    *,
    keyword: str,
    location: str = "",
    minimum: float = 0,
    maximum: float = 1_000_000,
    today: date | None = None,
    semantic_scores: Iterable[float] | None = None,
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
    if semantic_scores is None:
        frame["score_semantique"] = 0
        frame["score"] = frame[
            [
                "score_mots",
                "score_territoire",
                "score_montant",
                "score_renouvellement",
            ]
        ].sum(axis=1)
    else:
        values = list(semantic_scores)
        if len(values) != len(frame):
            raise ValueError(
                "Le nombre de scores sémantiques doit correspondre aux lignes."
            )
        frame["score_semantique"] = [
            round(max(0.0, min(1.0, value)) * 35) for value in values
        ]
        frame["score"] = (
            (
                frame["score_semantique"]
                + (frame["score_mots"] * 0.5).round()
                + (frame["score_territoire"] * 0.75).round()
                + (frame["score_montant"] * 0.75).round()
                + (frame["score_renouvellement"] * (2 / 3)).round()
            )
            .clip(0, 100)
            .astype(int)
        )
    return frame.sort_values(
        ["score", "montant"], ascending=[False, False], na_position="last"
    ).reset_index(drop=True)
