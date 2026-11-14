"""Suivi des labels réels et activation prudente du modèle supervisé."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import learning
import storage


ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="Apprentissage · Cap Marchés", page_icon="📈", layout="wide")
st.title("📈 Boucle d'apprentissage")
st.caption("Le projet apprend uniquement de vos décisions réelles, jamais de faux labels synthétiques.")

status = learning.readiness()
counts = storage.feedback_counts()
one, two, three = st.columns(3)
one.metric("Retours collectés", status["labels"])
two.metric("Minimum avant entraînement", status["minimum"])
three.metric("Classes observées", status["classes"])
st.json(counts)

progress = min(status["labels"] / status["minimum"], 1.0)
st.progress(progress, text=f"{status['labels']} / {status['minimum']} labels")
if not status["ready"]:
    st.info("Continuez à qualifier les opportunités. Il faut au moins 100 retours et des exemples positifs et négatifs.")
else:
    st.warning("L'entraînement remplace une règle métier par un modèle statistique : vérifiez les métriques avant activation.")
    if st.button("Entraîner une version candidate"):
        try:
            metadata = learning.train_model(ROOT / "models" / "ranker.joblib")
            st.success("Modèle candidat entraîné. Il n'est pas activé automatiquement.")
            st.json(metadata)
        except ValueError as exc:
            st.error(str(exc))
