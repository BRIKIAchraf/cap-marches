"""Interface de l'agent de veille outillé et sourcé."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

import storage
from services import agent, hemicycle, llm


ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="Agent IA · Cap Marchés", page_icon="🤖", layout="wide")
st.title("🤖 Agent de veille marchés publics")
st.caption("Un agent contrôlé : plan déterministe, outils bornés, preuves visibles, synthèse facultative.")

profile = storage.load_profile()
if not profile:
    st.warning("Créez d'abord votre profil dans la page « Profil entreprise ».")
    st.stop()

question = st.text_area(
    "Mission",
    value="Trouve les meilleures opportunités à venir et explique qui contacter en priorité.",
)
offline = st.checkbox("Mode démonstration hors ligne", value=not hemicycle.is_configured())

if st.button("Lancer l'agent", type="primary"):
    kwargs = {}
    if offline:
        projects = json.loads((ROOT / "data" / "sample_projects.json").read_text(encoding="utf-8"))
        contracts = json.loads((ROOT / "data" / "sample.json").read_text(encoding="utf-8"))
        organizations = json.loads((ROOT / "data" / "sample_organizations.json").read_text(encoding="utf-8"))
        kwargs = {
            "project_fetcher": lambda *args, **kw: projects,
            "contract_fetcher": lambda *args, **kw: contracts,
            "organization_fetcher": lambda *args, **kw: organizations,
        }
    try:
        with st.spinner("L'agent consulte les trois jeux, classe et vérifie les preuves…"):
            result = agent.run_agent(profile, question, **kwargs)
        st.session_state["agent_result"] = result
    except (ValueError, hemicycle.HemicycleError) as exc:
        st.error(str(exc))

result = st.session_state.get("agent_result")
if result:
    with st.expander("Plan exécuté", expanded=True):
        st.json(result["plan"])
    first, second = st.columns(2)
    first.metric("Projets futurs", len(result["projects"]))
    second.metric("Marchés historiques", len(result["contracts"]))
    st.subheader("Opportunités prioritaires")
    st.dataframe(result["projects"], hide_index=True, width="stretch")
    with st.expander("Dossier de preuves transmis à l'IA"):
        st.json(result["evidence"])
    if llm.is_configured() and st.button("Produire la recommandation sourcée"):
        try:
            with st.spinner("Rédaction à partir des preuves uniquement…"):
                st.markdown(llm.answer_from_evidence(question, result["evidence"]))
        except llm.LlmError as exc:
            st.error(str(exc))
    elif not llm.is_configured():
        st.info("Ajoutez FEATHERLESS_API_KEY pour obtenir une synthèse narrative. Le classement agent fonctionne déjà sans LLM.")
