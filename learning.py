"""Préparation et entraînement prudent d'un modèle de ranking supervisé."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select

import storage


POSITIVE_LABELS = {"pertinent", "a_contacter", "contacte", "gagne"}
MINIMUM_LABELS = 100


def feedback_frame() -> pd.DataFrame:
    storage.init_db()
    with storage.engine.begin() as connection:
        rows = connection.execute(select(storage.feedback)).mappings().all()
    prepared: list[dict[str, Any]] = []
    for row in rows:
        payload = row["payload"] or {}
        prepared.append(
            {
                "score": float(payload.get("score", 0) or 0),
                "score_semantique": float(payload.get("score_semantique", 0) or 0),
                "score_mots": float(payload.get("score_mots", 0) or 0),
                "score_territoire": float(payload.get("score_territoire", 0) or 0),
                "score_montant": float(payload.get("score_montant", 0) or 0),
                "score_temps": float(payload.get("score_calendrier", payload.get("score_renouvellement", 0)) or 0),
                "target": int(row["label"] in POSITIVE_LABELS),
            }
        )
    return pd.DataFrame(prepared)


def readiness() -> dict[str, Any]:
    frame = feedback_frame()
    classes = int(frame["target"].nunique()) if not frame.empty else 0
    return {
        "labels": len(frame),
        "classes": classes,
        "minimum": MINIMUM_LABELS,
        "ready": len(frame) >= MINIMUM_LABELS and classes == 2,
    }


def train_model(output_path: str | Path = "models/ranker.joblib") -> dict[str, Any]:
    """Entraîne seulement si les données réelles sont suffisantes et diversifiées."""

    status = readiness()
    if not status["ready"]:
        raise ValueError(
            f"Apprentissage refusé : {status['labels']}/{MINIMUM_LABELS} labels "
            "et deux classes sont nécessaires."
        )
    from joblib import dump
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split

    frame = feedback_frame()
    features = frame.drop(columns=["target"])
    target = frame["target"]
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=0.25, random_state=42, stratify=target
    )
    model = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, random_state=42)
    model.fit(x_train, y_train)
    auc = float(roc_auc_score(y_test, model.predict_proba(x_test)[:, 1]))
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    dump({"model": model, "features": list(features.columns)}, destination)
    metadata = {"labels": len(frame), "roc_auc": round(auc, 4), "path": str(destination)}
    destination.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata
