"""Agent de veille outillé et sourcé."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import storage
from services import agent, hemicycle, llm
from ui import empty_state, hero, navigation, safe_page_link, section, setup_page
from site_footer import render_footer


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
setup_page("Agent de veille", "🤖")
navigation()
profile = storage.load_profile()

hero(
    "Un agent qui enquête, classe et justifie",
    "Il transforme votre profil en plan de recherche, consulte les trois jeux publics, confronte l'historique et conserve les preuves de chaque recommandation.",
    "Agent commercial contrôlé",
    [
        (
            "Profil disponible" if profile else "Profil requis",
            "ok" if profile else "demo",
        ),
        (
            "Hémicycle connecté" if hemicycle.is_configured() else "Mode démonstration",
            "ok" if hemicycle.is_configured() else "demo",
        ),
        ("Réponse sourcée", "ok"),
    ],
)

if not profile:
    empty_state(
        "Votre agent a besoin de contexte",
        "Complétez d'abord le profil entreprise : offre, mots-clés, territoires et fourchette budgétaire.",
        "🏢",
    )
    safe_page_link("pages/2_Profil_entreprise.py", "Créer le profil entreprise", "🏢")
    st.stop()

section(
    "Confier une mission",
    f"L'agent travaillera pour {profile['company_name']} avec un périmètre borné.",
)
mission, settings = st.columns([1.4, 0.6])
with mission:
    question = st.text_area(
        "Objectif de la mission",
        value="Trouve les meilleures opportunités à venir et explique qui contacter en priorité.",
        height=120,
        placeholder="Ex. Identifie les projets RH en Île-de-France publiés dans les six prochains mois.",
    )
with settings:
    offline = st.toggle(
        "Mode démonstration",
        value=False,
        help="Option explicite pour tester l'interface avec les échantillons locaux. Elle ne doit pas être utilisée pour une analyse réelle.",
    )
    limit = st.slider("Résultats par source", 5, 50, 20, 5)
    launch = st.button(
        "Lancer la mission",
        type="primary",
        width="stretch",
    )

if launch:
    kwargs = {}
    if offline:
        projects = json.loads(
            (ROOT / "data" / "sample_projects.json").read_text(encoding="utf-8")
        )
        contracts = json.loads(
            (ROOT / "data" / "sample.json").read_text(encoding="utf-8")
        )
        organizations = json.loads(
            (ROOT / "data" / "sample_organizations.json").read_text(encoding="utf-8")
        )
        kwargs = {
            "project_fetcher": lambda *args, **kw: projects,
            "contract_fetcher": lambda *args, **kw: contracts,
            "organization_fetcher": lambda *args, **kw: organizations,
        }
    try:
        with st.spinner("Planification, collecte, comparaison et vérification…"):
            st.session_state["agent_result"] = agent.run_agent(
                profile, question, limit=limit, **kwargs
            )
            st.session_state["agent_question"] = question
    except (ValueError, hemicycle.HemicycleError) as exc:
        st.error(str(exc))

result = st.session_state.get("agent_result")
if not result:
    empty_state(
        "L'agent est prêt",
        "Décrivez la mission puis lancez-la. Chaque conclusion conservera son jeu source, son identifiant et les composantes de son score.",
        "◎",
    )
    st.stop()

projects_frame = pd.DataFrame(result["projects"])
contracts_frame = pd.DataFrame(result["contracts"])
organizations_frame = pd.DataFrame(result["organizations"])

one, two, three, four = st.columns(4)
one.metric("Projets futurs", len(projects_frame))
two.metric("Marchés historiques", len(contracts_frame))
three.metric("Organisations", len(organizations_frame))
four.metric("Preuves conservées", len(result["evidence"]))

tab_results, tab_plan, tab_proof, tab_answer = st.tabs(
    ["Recommandations", "Plan exécuté", "Preuves", "Synthèse IA"]
)

with tab_results:
    section("Opportunités recommandées", "Classées par pertinence pour votre profil.")
    if projects_frame.empty:
        st.info("Aucun projet futur trouvé pour cette mission.")
    else:
        columns = [
            column
            for column in [
                "libelle",
                "denomination_acheteur",
                "montant_estime_du_marche",
                "date_previsionnelle_de_publication",
                "departement_s_d_execution_du_marche",
                "score",
            ]
            if column in projects_frame
        ]
        st.dataframe(
            projects_frame[columns],
            hide_index=True,
            width="stretch",
            column_config={
                "libelle": "Projet",
                "denomination_acheteur": "Acheteur",
                "montant_estime_du_marche": "Budget",
                "date_previsionnelle_de_publication": "Publication",
                "departement_s_d_execution_du_marche": "Territoire",
                "score": st.column_config.ProgressColumn(
                    "Score", min_value=0, max_value=100
                ),
            },
        )
    with st.expander("Voir les signaux historiques associés"):
        if contracts_frame.empty:
            st.write("Aucun marché historique associé.")
        else:
            st.dataframe(
                contracts_frame,
                hide_index=True,
                width="stretch",
            )

with tab_plan:
    st.markdown("#### Ce que l'agent a réellement fait")
    for index, step in enumerate(result["plan"]["steps"], start=1):
        st.write(f"**{index}.** {step}")
    st.json(
        {
            "requête": result["plan"]["query"],
            "département": result["plan"]["department"] or "France",
            "catégorie": result["plan"]["category"] or "Toutes",
            "fourchette": result["plan"]["amount_range"],
        }
    )

with tab_proof:
    st.markdown("#### Dossier transmis au modèle de langage")
    st.caption("Ces données publiques sont le seul contexte autorisé pour la synthèse.")
    st.json(result["evidence"], expanded=True)

with tab_answer:
    has_llm = llm.is_configured()
    if has_llm:
        st.caption(
            "La réponse sera générée via Featherless à partir du dossier de preuves uniquement."
        )
    else:
        st.caption(
            "Synthèse factuelle certifiée sans hallucination (Ajoutez `FEATHERLESS_API_KEY` dans `.env` pour l'analyse générative)."
        )
    if st.button(
        "Produire la recommandation sourcée",
        type="primary",
        width="stretch",
    ):
        try:
            with st.spinner("Rédaction à partir des preuves publiques uniquement…"):
                answer = llm.answer_from_evidence(
                    st.session_state.get("agent_question", question),
                    result["evidence"],
                    allow_heuristic=True,
                )
            st.session_state["agent_answer"] = answer
        except llm.LlmError as exc:
            st.error(str(exc))
    if st.session_state.get("agent_answer"):
        st.markdown(st.session_state["agent_answer"])

render_footer()
