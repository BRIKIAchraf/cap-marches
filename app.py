"""Cap Marchés - MVP Streamlit du hackathon Hémicycle."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from scoring import DISPLAY_COLUMNS, score_contracts
from services import decp, hemicycle, llm


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

st.set_page_config(
    page_title="Cap Marchés",
    page_icon="🎯",
    layout="wide",
)


@st.cache_data(ttl=3600, show_spinner=False)
def load_sample() -> list[dict]:
    return json.loads((ROOT / "data" / "sample.json").read_text(encoding="utf-8"))


@st.cache_data(ttl=3600, show_spinner=False)
def load_records(provider: str, keyword: str, limit: int) -> tuple[list[dict], str]:
    """Charge les données et applique le repli documenté du mode Auto."""

    if provider == "Démonstration hors ligne":
        return load_sample(), "Données synthétiques de démonstration"
    if provider == "Hémicycle":
        return hemicycle.fetch_contracts(keyword, limit=limit), "Hémicycle"
    if provider == "DECP officielle":
        return decp.fetch_contracts(keyword, limit=limit), "DECP officielle"

    if hemicycle.is_configured():
        try:
            return hemicycle.fetch_contracts(keyword, limit=limit), "Hémicycle"
        except hemicycle.HemicycleError:
            pass
    try:
        return decp.fetch_contracts(keyword, limit=limit), "DECP officielle"
    except decp.DecpError:
        return load_sample(), "Données synthétiques (repli hors ligne)"


st.title("🎯 Cap Marchés")
st.caption(
    "Un radar de prospection qui transforme les marchés publics en signaux "
    "commerciaux explicables."
)

with st.sidebar:
    st.header("Votre cible")
    keyword = st.text_input("Produit ou service", value="logiciel RH")
    location = st.text_input(
        "Département ou lieu (facultatif)", value="", placeholder="75"
    )
    minimum, maximum = st.slider(
        "Montant recherché",
        min_value=0,
        max_value=2_000_000,
        value=(50_000, 500_000),
        step=10_000,
        format="%d €",
    )
    provider = st.selectbox(
        "Source",
        ["Auto", "Hémicycle", "DECP officielle", "Démonstration hors ligne"],
    )
    limit = st.slider("Nombre de marchés analysés", 20, 100, 100, 10)
    run = st.button("Analyser les opportunités", type="primary", width="stretch")

    st.divider()
    st.caption(
        "Le score est calculé sans IA : mots-clés (30), territoire (20), "
        "montant (20) et renouvellement estimé (30)."
    )

if not run:
    st.info(
        "Choisissez une offre puis cliquez sur **Analyser les opportunités**. "
        "Le mode Auto utilise Hémicycle s'il est configuré, sinon l'API DECP."
    )
    st.stop()

try:
    with st.spinner("Lecture des données publiques…"):
        records, source_label = load_records(provider, keyword, limit)
except (ValueError, decp.DecpError, hemicycle.HemicycleError) as exc:
    st.error(str(exc))
    st.stop()

frame = score_contracts(
    records,
    keyword=keyword,
    location=location,
    minimum=minimum,
    maximum=maximum,
)

if frame.empty:
    st.warning("Aucun marché ne correspond à cette recherche.")
    st.stop()

st.success(f"{len(frame)} marchés analysés - Source : {source_label}")
metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Marchés", f"{len(frame):,}".replace(",", " "))
metric2.metric(
    "Montant médian",
    f"{frame['montant'].median():,.0f} €".replace(",", " ")
    if frame["montant"].notna().any()
    else "N/D",
)
metric3.metric("Acheteurs", int(frame["acheteur_id"].nunique(dropna=True)))
metric4.metric("Meilleur score", f"{int(frame['score'].max())}/100")

left, right = st.columns([1.15, 0.85])
with left:
    st.subheader("Signaux prioritaires")
    display = frame[DISPLAY_COLUMNS].head(20).copy()
    display["datenotification"] = display["datenotification"].dt.strftime("%Y-%m-%d")
    display["date_fin_estimee"] = display["date_fin_estimee"].dt.strftime("%Y-%m-%d")
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_config={
            "objet": "Objet",
            "montant": st.column_config.NumberColumn("Montant", format="%.0f €"),
            "datenotification": "Notification",
            "dureemois": "Durée (mois)",
            "date_fin_estimee": "Fin estimée",
            "lieuexecution_code": "Lieu",
            "acheteur_id": "Acheteur (SIRET)",
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
        },
    )

with right:
    st.subheader("Où se trouvent les signaux ?")
    chart_data = (
        frame.assign(
            territoire=frame["lieuexecution_code"].fillna("Non renseigné").astype(str)
        )
        .groupby("territoire", as_index=False)
        .agg(montant=("montant", "sum"), marches=("objet", "count"))
        .sort_values("montant", ascending=False)
        .head(10)
    )
    fig = px.bar(
        chart_data,
        x="territoire",
        y="montant",
        hover_data=["marches"],
        labels={"territoire": "Territoire", "montant": "Montant cumulé (€)"},
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=420)
    st.plotly_chart(fig, width="stretch")

st.subheader("Pourquoi ces résultats ?")
with st.expander("Voir le détail du meilleur score", expanded=True):
    top = frame.iloc[0]
    cols = st.columns(4)
    cols[0].metric("Mots-clés", f"{int(top['score_mots'])}/30")
    cols[1].metric("Territoire", f"{int(top['score_territoire'])}/20")
    cols[2].metric("Montant", f"{int(top['score_montant'])}/20")
    cols[3].metric("Renouvellement", f"{int(top['score_renouvellement'])}/30")
    st.write(top["objet"])

st.subheader("Préparer l'approche commerciale")
if not llm.is_configured():
    st.info(
        "Ajoutez `FEATHERLESS_API_KEY` dans `.env` pour générer une note. "
        "Le classement ci-dessus fonctionne sans IA."
    )
elif st.button("Générer la fiche avec Featherless"):
    try:
        with st.spinner("Rédaction factuelle…"):
            brief = llm.build_brief(
                frame.head(5).to_dict(orient="records"), company_offer=keyword
            )
        st.markdown(brief)
    except llm.LlmError as exc:
        st.error(str(exc))

st.divider()
if "synthétiques" in source_label.lower():
    st.warning(
        "Mode démonstration : ces lignes sont synthétiques et ne doivent pas "
        "être présentées comme des marchés réels."
    )
else:
    st.caption(
        "Source : Hémicycle ou Données essentielles de la commande publique "
        "(DECP). Licence Ouverte 2.0. La fin de contrat est une estimation calculée "
        "à partir de la date de notification et de la durée publiée."
    )

