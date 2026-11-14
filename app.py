"""Interface principale de Cap Marchés."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

import storage
from scoring import DISPLAY_COLUMNS, PROJECT_DISPLAY_COLUMNS, score_contracts, score_projects
from services import decp, hemicycle, llm
from services.evidence import contract_evidence, project_evidence
from services.semantic import semantic_scores
from ui import brand, empty_state, euro, hero, section, setup_page


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
setup_page("Radar d'opportunités")


@st.cache_data(ttl=3600, show_spinner=False)
def load_json_sample(filename: str) -> list[dict[str, Any]]:
    return json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))


@st.cache_data(ttl=3600, show_spinner=False)
def load_records(
    analysis: str,
    provider: str,
    keyword: str,
    department: str,
    category: str,
    limit: int,
) -> tuple[list[dict[str, Any]], str]:
    if provider == "Démonstration hors ligne":
        filename = "sample_projects.json" if analysis == "future" else "sample.json"
        return load_json_sample(filename), "Démonstration synthétique"
    if analysis == "future":
        if provider == "Hémicycle":
            return (
                hemicycle.fetch_upcoming_projects(
                    keyword, department=department, category=category, limit=limit
                ),
                "Hémicycle · projets_achats_publics",
            )
        if hemicycle.is_configured():
            try:
                return (
                    hemicycle.fetch_upcoming_projects(
                        keyword, department=department, category=category, limit=limit
                    ),
                    "Hémicycle · projets_achats_publics",
                )
            except hemicycle.HemicycleError:
                pass
        return load_json_sample("sample_projects.json"), "Démonstration synthétique"
    if provider == "Hémicycle":
        return (
            hemicycle.fetch_contracts(keyword, department=department, limit=limit),
            "Hémicycle · marches_publics",
        )
    if provider == "DECP officielle":
        return decp.fetch_contracts(keyword, limit=limit), "DECP officielle"
    if hemicycle.is_configured():
        try:
            return (
                hemicycle.fetch_contracts(keyword, department=department, limit=limit),
                "Hémicycle · marches_publics",
            )
        except hemicycle.HemicycleError:
            pass
    try:
        return decp.fetch_contracts(keyword, limit=limit), "DECP officielle"
    except decp.DecpError:
        return load_json_sample("sample.json"), "Démonstration synthétique"


@st.cache_data(ttl=3600, show_spinner=False)
def load_organizations(
    identifiers: tuple[str, ...], identifier_type: str, synthetic: bool
) -> tuple[list[dict[str, Any]], str]:
    if synthetic:
        return load_json_sample("sample_organizations.json"), "Sirene de démonstration"
    if not hemicycle.is_configured() or not identifiers:
        return [], "Sirene non connecté"
    return (
        hemicycle.fetch_organizations(
            identifiers, identifier_type=identifier_type, limit=100
        ),
        "Hémicycle · sirene_etablissements",
    )


def enrich_with_organizations(
    frame: pd.DataFrame, organizations: list[dict[str, Any]], *, identifier_type: str
) -> pd.DataFrame:
    enriched = frame.copy()
    if enriched.empty or not organizations:
        enriched["denomination_acheteur"] = None
        enriched["commune_acheteur"] = None
        enriched["activite_acheteur"] = None
        return enriched
    orgs = pd.DataFrame(organizations)
    source_key = (
        "siren_de_l_entite_acheteuse" if identifier_type == "siren" else "acheteur_id"
    )
    if identifier_type not in orgs:
        return enrich_with_organizations(frame, [], identifier_type=identifier_type)
    for column in ("denomination", "commune", "activite_principale"):
        if column not in orgs:
            orgs[column] = None
    orgs[identifier_type] = orgs[identifier_type].astype(str)
    orgs = orgs.drop_duplicates(identifier_type)[
        [identifier_type, "denomination", "commune", "activite_principale"]
    ].rename(
        columns={
            "denomination": "denomination_acheteur",
            "commune": "commune_acheteur",
            "activite_principale": "activite_acheteur",
        }
    )
    enriched[source_key] = enriched[source_key].astype(str)
    return enriched.merge(
        orgs, left_on=source_key, right_on=identifier_type, how="left"
    )


def semantic_documents(records: list[dict[str, Any]], analysis: str) -> list[str]:
    keys = (
        ("libelle", "description", "code_s_cpv", "categorie_d_achat")
        if analysis == "future"
        else ("objet", "codecpv", "nature")
    )
    return [
        " ".join(str(record.get(key, "") or "") for key in keys) for record in records
    ]


def perform_analysis(config: dict[str, Any]) -> dict[str, Any]:
    records, source_label = load_records(
        config["analysis"],
        config["provider"],
        config["keyword"],
        config["department"],
        config["category"],
        config["limit"],
    )
    semantics = (
        semantic_scores(
            config["keyword"], semantic_documents(records, config["analysis"])
        )
        if config["use_semantic"]
        else None
    )
    scoring_args = {
        "keyword": config["keyword"],
        "location": config["department"],
        "minimum": config["minimum"],
        "maximum": config["maximum"],
        "semantic_scores": semantics,
    }
    if config["analysis"] == "future":
        frame = score_projects(records, **scoring_args)
        identifier_column, identifier_type = "siren_de_l_entite_acheteuse", "siren"
    else:
        frame = score_contracts(records, **scoring_args)
        identifier_column, identifier_type = "acheteur_id", "siret"
    sirene_label = "Enrichissement désactivé"
    if config["enrich"] and not frame.empty:
        identifiers = tuple(
            frame[identifier_column].dropna().astype(str).drop_duplicates().head(100)
        )
        try:
            organizations, sirene_label = load_organizations(
                identifiers,
                identifier_type,
                synthetic="synthétique" in source_label.lower(),
            )
        except hemicycle.HemicycleError:
            organizations, sirene_label = [], "Sirene temporairement indisponible"
        frame = enrich_with_organizations(
            frame, organizations, identifier_type=identifier_type
        )
    else:
        frame = enrich_with_organizations(
            frame, [], identifier_type=identifier_type
        )
    return {
        "frame": frame,
        "source_label": source_label,
        "sirene_label": sirene_label,
        "identifier_column": identifier_column,
        "identifier_type": identifier_type,
        "config": config,
    }


def selected_label(row: pd.Series, index: int, analysis: str) -> str:
    title = row.get("libelle") if analysis == "future" else row.get("objet")
    return f"{index + 1:02d} · {str(title or 'Sans titre')[:92]}"


with st.sidebar:
    brand()
    st.caption("NAVIGATION")
    st.page_link("app.py", label="Radar d'opportunités", icon="🎯")
    st.page_link("pages/2_Profil_entreprise.py", label="Profil entreprise", icon="🏢")
    st.page_link("pages/3_Agent_IA.py", label="Agent de veille", icon="🤖")
    st.page_link("pages/4_Apprentissage.py", label="Apprentissage", icon="📈")
    st.divider()
    st.caption("NOUVELLE ANALYSE")
    with st.form("search-form"):
        mode_label = st.radio(
            "Périmètre",
            ["Achats à venir", "Historique"],
            horizontal=True,
        )
        analysis = "future" if mode_label == "Achats à venir" else "history"
        keyword = st.text_input(
            "Votre offre",
            value="logiciel RH",
            placeholder="Ex. cybersécurité, formation, conseil…",
        )
        department = st.text_input(
            "Territoire",
            placeholder="Département, ex. 75",
        )
        category = ""
        if analysis == "future":
            chosen_category = st.selectbox(
                "Catégorie",
                ["Toutes", "Services", "Fournitures", "Travaux"],
            )
            category = "" if chosen_category == "Toutes" else chosen_category
        amounts = st.slider(
            "Fourchette de marché",
            min_value=0,
            max_value=5_000_000,
            value=(50_000, 500_000),
            step=10_000,
            format="%d €",
        )
        providers = ["Auto", "Hémicycle", "Démonstration hors ligne"]
        if analysis == "history":
            providers.insert(2, "DECP officielle")
        provider = st.selectbox("Source", providers)
        with st.expander("Options avancées"):
            use_semantic = st.checkbox("Compréhension sémantique", value=True)
            enrich = st.checkbox("Enrichissement Sirene", value=True)
            limit = st.slider("Volume analysé", 20, 100, 100, 10)
        submitted = st.form_submit_button(
            "Lancer l'analyse", type="primary", width="stretch"
        )


hero(
    "Votre radar de marchés publics",
    "Détectez les projets avant publication, comprenez les acheteurs et transformez les données publiques en actions commerciales vérifiables.",
    "Veille augmentée par les données publiques",
    [
        (
            "Hémicycle connecté" if hemicycle.is_configured() else "Mode démonstration",
            "ok" if hemicycle.is_configured() else "demo",
        ),
        (
            "Featherless connecté" if llm.is_configured() else "Synthèse IA facultative",
            "ok" if llm.is_configured() else "demo",
        ),
        ("Score explicable", "ok"),
    ],
)

if submitted:
    config = {
        "analysis": analysis,
        "keyword": keyword.strip(),
        "department": department.strip(),
        "category": category,
        "minimum": float(amounts[0]),
        "maximum": float(amounts[1]),
        "provider": provider,
        "use_semantic": use_semantic,
        "enrich": enrich,
        "limit": limit,
    }
    if not config["keyword"]:
        st.error("Décrivez votre offre avec au moins un mot-clé.")
    else:
        try:
            with st.spinner("Collecte, enrichissement et classement des opportunités…"):
                st.session_state["analysis_result"] = perform_analysis(config)
                st.session_state["selected_opportunity"] = 0
        except (ValueError, decp.DecpError, hemicycle.HemicycleError) as exc:
            st.error(str(exc))

result = st.session_state.get("analysis_result")
if not result:
    empty_state(
        "Commencez par une recherche ciblée",
        "Décrivez votre offre dans le panneau de gauche. Cap Marchés confrontera les projets futurs, l'historique et les organisations publiques.",
        "⌖",
    )
    section("Un parcours simple", "De la donnée brute à la prochaine action commerciale.")
    first, second, third = st.columns(3)
    first.info("**1 · Cibler**\n\nOffre, territoire et budget définissent votre périmètre.")
    second.info("**2 · Comprendre**\n\nLe score hybride explique chaque priorité.")
    third.info("**3 · Agir**\n\nQualifiez, sauvegardez et préparez votre approche.")
    st.stop()

frame: pd.DataFrame = result["frame"]
active = result["config"]
if frame.empty:
    empty_state(
        "Aucune opportunité trouvée",
        "Élargissez le territoire, la fourchette budgétaire ou reformulez votre offre.",
        "∅",
    )
    st.stop()

is_future = active["analysis"] == "future"
analysis_name = "Achats à venir" if is_future else "Historique des marchés"
st.caption(
    f"Recherche active · **{active['keyword']}** · {analysis_name} · "
    f"{result['source_label']} · {result['sirene_label']}"
)

metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Opportunités analysées", len(frame))
if is_future:
    horizon = pd.Timestamp(date.today() + timedelta(days=90))
    upcoming = int(
        frame["date_previsionnelle_de_publication"].between(
            pd.Timestamp(date.today()), horizon
        ).sum()
    )
    metric2.metric("Publications sous 90 jours", upcoming)
else:
    median = frame["montant"].median() if frame["montant"].notna().any() else None
    metric2.metric("Montant médian", euro(median))
metric3.metric(
    "Acheteurs identifiés",
    int(frame[result["identifier_column"]].nunique(dropna=True)),
)
metric4.metric("Meilleur score", f"{int(frame['score'].max())} / 100")

section(
    "Résultats prioritaires",
    "Sélectionnez une ligne pour comprendre son score, consulter ses preuves et décider de la suite.",
)
labels = [
    selected_label(row, index, active["analysis"]) for index, (_, row) in enumerate(frame.head(30).iterrows())
]
selected_index = st.selectbox(
    "Opportunité ouverte",
    range(len(labels)),
    format_func=lambda index: labels[index],
    key="selected_opportunity",
    label_visibility="collapsed",
)
selected = frame.iloc[int(selected_index)]

tab_list, tab_analysis, tab_actions = st.tabs(
    ["Vue d'ensemble", "Analyse & preuves", "Actions commerciales"]
)

with tab_list:
    if is_future:
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
            if column in frame
        ]
        display = frame[columns].head(30).copy()
        if "date_previsionnelle_de_publication" in display:
            display["date_previsionnelle_de_publication"] = display[
                "date_previsionnelle_de_publication"
            ].dt.strftime("%d/%m/%Y")
        config = {
            "libelle": "Projet",
            "denomination_acheteur": "Acheteur",
            "montant_estime_du_marche": "Budget estimé",
            "date_previsionnelle_de_publication": "Publication",
            "departement_s_d_execution_du_marche": "Territoire",
            "score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100
            ),
        }
    else:
        columns = [
            column
            for column in [
                "objet",
                "denomination_acheteur",
                "montant",
                "date_fin_estimee",
                "lieuexecution_code",
                "score",
            ]
            if column in frame
        ]
        display = frame[columns].head(30).copy()
        if "date_fin_estimee" in display:
            display["date_fin_estimee"] = display["date_fin_estimee"].dt.strftime(
                "%d/%m/%Y"
            )
        config = {
            "objet": "Marché",
            "denomination_acheteur": "Acheteur",
            "montant": st.column_config.NumberColumn("Montant", format="%.0f €"),
            "date_fin_estimee": "Fin estimée",
            "lieuexecution_code": "Territoire",
            "score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100
            ),
        }
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_config=config,
        height=470,
    )
    chart_source = (
        "departement_s_d_execution_du_marche" if is_future else "lieuexecution_code"
    )
    chart = (
        frame.assign(
            territoire=frame[chart_source].fillna("Non renseigné").astype(str)
        )
        .groupby("territoire", as_index=False)
        .agg(opportunites=("score", "count"), score_moyen=("score", "mean"))
        .sort_values("opportunites", ascending=False)
        .head(10)
    )
    figure = px.bar(
        chart,
        x="territoire",
        y="opportunites",
        color="score_moyen",
        color_continuous_scale=["#bcd8f8", "#2864dc", "#12315d"],
        labels={
            "territoire": "Territoire",
            "opportunites": "Opportunités",
            "score_moyen": "Score moyen",
        },
    )
    figure.update_layout(
        margin=dict(l=10, r=10, t=25, b=10),
        height=330,
        coloraxis_colorbar=dict(title="Score"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(figure, width="stretch")

with tab_analysis:
    title = selected.get("libelle") if is_future else selected.get("objet")
    st.subheader(str(title or "Opportunité"))
    buyer = selected.get("denomination_acheteur") or "Acheteur non enrichi"
    locality = selected.get("commune_acheteur") or (
        selected.get("departement_s_d_execution_du_marche")
        if is_future
        else selected.get("lieuexecution_code")
    )
    st.caption(f"{buyer} · {locality or 'Territoire non renseigné'}")
    score_columns = st.columns(5)
    score_columns[0].metric("Score global", f"{int(selected['score'])}/100")
    score_columns[1].metric(
        "Sens", f"{int(selected.get('score_semantique', 0))}/35"
    )
    score_columns[2].metric("Mots", f"{int(selected.get('score_mots', 0))}/30 brut")
    score_columns[3].metric(
        "Territoire", f"{int(selected.get('score_territoire', 0))}/20 brut"
    )
    score_columns[4].metric(
        "Budget", f"{int(selected.get('score_montant', 0))}/20 brut"
    )
    evidence = (
        project_evidence(selected.to_dict())
        if is_future
        else contract_evidence(selected.to_dict())
    )
    facts, proof = st.columns([1.05, 0.95])
    with facts:
        st.markdown("#### Lecture commerciale")
        if is_future:
            st.write(
                f"**Budget :** {selected.get('montant_estime_du_marche') or 'Non renseigné'}"
            )
            publication = selected.get("date_previsionnelle_de_publication")
            st.write(
                f"**Publication prévue :** {publication.strftime('%d/%m/%Y') if pd.notna(publication) else 'Non renseignée'}"
            )
            st.write(
                f"**Catégorie :** {selected.get('categorie_d_achat') or 'Non renseignée'}"
            )
            link = selected.get("lien_vers_la_consultation")
            if link:
                st.link_button("Ouvrir la consultation", str(link))
        else:
            st.write(f"**Montant :** {euro(selected.get('montant'))}")
            st.write(
                f"**Durée :** {selected.get('dureemois') or 'Non renseignée'} mois"
            )
            ending = selected.get("date_fin_estimee")
            st.write(
                f"**Fin estimée :** {ending.strftime('%d/%m/%Y') if pd.notna(ending) else 'Non renseignée'}"
            )
        st.info(
            "Le score sert à prioriser. Il ne remplace pas l'analyse du dossier ni une date officielle de publication."
        )
    with proof:
        st.markdown("#### Dossier de preuve")
        st.json(evidence, expanded=True)

with tab_actions:
    action_col, watch_col = st.columns(2)
    record = selected.to_dict()
    opportunity_key = str(
        record.get("code")
        or f"{record.get('acheteur_id', '')}:{record.get('objet', '')}"
    )
    with action_col:
        st.markdown("#### Qualifier cette opportunité")
        with st.form("feedback-form"):
            label = st.selectbox(
                "Décision",
                [
                    "pertinent",
                    "a_contacter",
                    "contacte",
                    "gagne",
                    "non_pertinent",
                    "perdu",
                ],
                format_func=lambda value: value.replace("_", " ").capitalize(),
            )
            notes = st.text_area(
                "Note interne",
                placeholder="Pourquoi ce signal est-il important ?",
            )
            feedback_submit = st.form_submit_button(
                "Enregistrer la décision", type="primary"
            )
        if feedback_submit:
            record["note_interne"] = notes.strip()
            storage.record_feedback(
                opportunity_key,
                label,
                "projets_achats_publics" if is_future else "marches_publics",
                record,
            )
            st.success("Décision enregistrée. Elle alimentera la boucle d'apprentissage.")
    with watch_col:
        st.markdown("#### Sauvegarder la veille")
        with st.form("watch-form"):
            watch_name = st.text_input(
                "Nom de la veille",
                value=f"{active['keyword']} · {active['department'] or 'France'}",
            )
            alert = st.checkbox(
                "Préparer l'alerte quotidienne",
                help="La planification est enregistrée ; aucun email n'est envoyé par défaut.",
            )
            watch_submit = st.form_submit_button("Sauvegarder la veille")
        if watch_submit:
            storage.save_search(watch_name, active, alert)
            st.success("Veille sauvegardée.")
    st.divider()
    download_col, ai_col = st.columns(2)
    with download_col:
        st.download_button(
            "Exporter les résultats en CSV",
            data=frame.to_csv(index=False).encode("utf-8-sig"),
            file_name="cap-marches-opportunites.csv",
            mime="text/csv",
            width="stretch",
        )
    with ai_col:
        if not llm.is_configured():
            st.button(
                "Synthèse IA non connectée",
                disabled=True,
                width="stretch",
                help="Ajoutez FEATHERLESS_API_KEY dans .env.",
            )
        elif st.button(
            "Générer la note commerciale",
            type="primary",
            width="stretch",
        ):
            try:
                with st.spinner("Rédaction factuelle à partir des preuves…"):
                    brief = llm.build_brief(
                        frame.head(5).to_dict(orient="records"),
                        company_offer=active["keyword"],
                    )
                st.markdown(brief)
            except llm.LlmError as exc:
                st.error(str(exc))

if "synthétique" in result["source_label"].lower():
    st.warning(
        "Mode démonstration : les lignes affichées sont synthétiques et ne doivent pas être présentées comme des achats réels."
    )
else:
    st.caption(
        "Sources : APProch, DECP et Sirene via Hémicycle · Licence Ouverte 2.0 · Les scores sont des indicateurs d'aide à la décision."
    )
