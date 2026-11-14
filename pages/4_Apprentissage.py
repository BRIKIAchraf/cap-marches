"""Suivi des retours et entraînement prudent du ranking."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import learning
import storage
from ui import hero, navigation, section, setup_page


ROOT = Path(__file__).resolve().parents[1]
setup_page("Apprentissage", "📈")
navigation()
status = learning.readiness()
counts = storage.feedback_counts()

hero(
    "Améliorer le classement avec vos décisions",
    "Chaque qualification commerciale devient un signal d'apprentissage. Le modèle candidat reste désactivé jusqu'à disposer d'un volume suffisant et équilibré.",
    "Boucle de progrès",
    [
        (f"{status['labels']} retours collectés", "ok" if status["labels"] else "demo"),
        (f"Objectif {status['minimum']} labels", "demo" if not status["ready"] else "ok"),
        ("Activation manuelle uniquement", "ok"),
    ],
)

one, two, three, four = st.columns(4)
one.metric("Retours collectés", status["labels"])
two.metric("Objectif minimum", status["minimum"])
three.metric("Classes observées", status["classes"])
four.metric("État", "Prêt" if status["ready"] else "Collecte")

section(
    "Progression",
    "Le modèle nécessite au moins deux classes : décisions positives et négatives.",
)
progress = min(status["labels"] / status["minimum"], 1.0)
st.progress(progress, text=f"{status['labels']} / {status['minimum']} décisions")

chart_col, guidance_col = st.columns([1.1, 0.9])
with chart_col:
    if counts:
        chart_data = pd.DataFrame(
            [{"décision": label.replace("_", " "), "volume": count} for label, count in counts.items()]
        )
        figure = px.bar(
            chart_data,
            x="décision",
            y="volume",
            color="volume",
            color_continuous_scale=["#bcd8f8", "#2864dc", "#12315d"],
        )
        figure.update_layout(
            height=330,
            margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
        )
        st.plotly_chart(figure, width="stretch")
    else:
        st.info(
            "Aucun retour pour le moment. Qualifiez une opportunité depuis le Radar."
        )
with guidance_col:
    st.markdown("#### Conditions d'entraînement")
    st.write("✓ Données issues de décisions réelles")
    st.write("✓ Au moins 100 observations")
    st.write("✓ Exemples positifs et négatifs")
    st.write("✓ Modèle produit comme candidat")
    st.write("✓ Validation humaine avant activation")

section("Version candidate", "L'entraînement ne modifie jamais automatiquement le classement en production.")
if not status["ready"]:
    remaining = max(status["minimum"] - status["labels"], 0)
    st.warning(
        f"Collecte en cours : encore {remaining} décision(s) minimum et deux classes sont nécessaires."
    )
    st.button("Entraîner un modèle candidat", disabled=True)
else:
    st.warning(
        "Vérifiez la qualité et la représentativité des labels avant de lancer l'entraînement."
    )
    if st.button("Entraîner un modèle candidat", type="primary"):
        try:
            with st.spinner("Entraînement et évaluation sur un jeu de validation…"):
                metadata = learning.train_model(ROOT / "models" / "ranker.joblib")
            st.success("Modèle candidat créé. Il n'est pas activé automatiquement.")
            st.json(metadata)
        except ValueError as exc:
            st.error(str(exc))
