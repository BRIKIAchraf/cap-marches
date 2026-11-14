"""Cap Marchés - radar de prospection fondé sur trois jeux Hémicycle."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from scoring import DISPLAY_COLUMNS, PROJECT_DISPLAY_COLUMNS, score_contracts, score_projects
from services import decp, hemicycle, llm
from services.evidence import contract_evidence, project_evidence
from services.semantic import semantic_scores
import storage


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

st.set_page_config(page_title="Cap Marchés", page_icon="🎯", layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def load_json_sample(filename: str) -> list[dict]:
    return json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))


@st.cache_data(ttl=3600, show_spinner=False)
def load_records(
    analysis: str,
    provider: str,
    keyword: str,
    department: str,
    category: str,
    limit: int,
) -> tuple[list[dict], str]:
    """Charge la bonne source avec un repli explicite pour la démo."""

    if provider == "Démonstration hors ligne":
        filename = "sample_projects.json" if analysis == "future" else "sample.json"
        return load_json_sample(filename), "Données synthétiques de démonstration"

    if analysis == "future":
        if provider == "Hémicycle":
            return (
                hemicycle.fetch_upcoming_projects(
                    keyword,
                    department=department,
                    category=category,
                    limit=limit,
                ),
                "Hémicycle · projets_achats_publics",
            )
        if hemicycle.is_configured():
            try:
                return (
                    hemicycle.fetch_upcoming_projects(
                        keyword,
                        department=department,
                        category=category,
                        limit=limit,
                    ),
                    "Hémicycle · projets_achats_publics",
                )
            except hemicycle.HemicycleError:
                pass
        return (
            load_json_sample("sample_projects.json"),
            "Données synthétiques (clé Hémicycle non configurée)",
        )

    if provider == "Hémicycle":
        return (
            hemicycle.fetch_contracts(
                keyword, department=department, limit=limit
            ),
            "Hémicycle · marches_publics",
        )
    if provider == "DECP officielle":
        return decp.fetch_contracts(keyword, limit=limit), "DECP officielle"
    if hemicycle.is_configured():
        try:
            return (
                hemicycle.fetch_contracts(
                    keyword, department=department, limit=limit
                ),
                "Hémicycle · marches_publics",
            )
        except hemicycle.HemicycleError:
            pass
    try:
        return decp.fetch_contracts(keyword, limit=limit), "DECP officielle"
    except decp.DecpError:
        return (
            load_json_sample("sample.json"),
            "Données synthétiques (repli hors ligne)",
        )


@st.cache_data(ttl=3600, show_spinner=False)
def load_organizations(
    identifiers: tuple[str, ...], identifier_type: str, synthetic: bool
) -> tuple[list[dict], str]:
    if synthetic:
        return load_json_sample("sample_organizations.json"), "Sirene de démonstration"
    if not hemicycle.is_configured() or not identifiers:
        return [], "Sirene non configuré"
    return (
        hemicycle.fetch_organizations(
            identifiers, identifier_type=identifier_type, limit=100
        ),
        "Hémicycle · sirene_etablissements",
    )


def enrich_with_organizations(
    frame: pd.DataFrame, organizations: list[dict], *, identifier_type: str
) -> pd.DataFrame:
    if frame.empty or not organizations:
        frame = frame.copy()
        frame["denomination_acheteur"] = None
        frame["commune_acheteur"] = None
        return frame

    orgs = pd.DataFrame(organizations)
    key = identifier_type
    source_key = (
        "siren_de_l_entite_acheteuse" if identifier_type == "siren" else "acheteur_id"
    )
    if key not in orgs:
        return enrich_with_organizations(frame, [], identifier_type=identifier_type)
    for column in ("denomination", "commune", "activite_principale"):
        if column not in orgs:
            orgs[column] = None
    orgs[key] = orgs[key].astype(str)
    orgs = orgs.drop_duplicates(key)[
        [key, "denomination", "commune", "activite_principale"]
    ].rename(
        columns={
            "denomination": "denomination_acheteur",
            "commune": "commune_acheteur",
            "activite_principale": "activite_acheteur",
        }
    )
    enriched = frame.copy()
    enriched[source_key] = enriched[source_key].astype(str)
    return enriched.merge(orgs, left_on=source_key, right_on=key, how="left")


st.title("🎯 Cap Marchés")
st.caption(
    "Repérez les achats publics avant l'appel d'offres, confrontez-les à "
    "l'historique et identifiez les acheteurs avec Sirene."
)

with st.sidebar:
    st.header("Votre cible")
    mode_label = st.radio(
        "Vue",
        ["Opportunités à venir", "Historique des marchés"],
        help="Les opportunités futures proviennent d'APProch ; l'historique des DECP.",
    )
    analysis = "future" if mode_label == "Opportunités à venir" else "history"
    keyword = st.text_input("Produit ou service", value="logiciel RH")
    department = st.text_input(
        "Département (facultatif)", value="", placeholder="75"
    )
    category = ""
    if analysis == "future":
        category = st.selectbox(
            "Catégorie d'achat",
            ["Toutes", "Services", "Fournitures", "Travaux"],
        )
        category = "" if category == "Toutes" else category
    minimum, maximum = st.slider(
        "Montant recherché",
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
    enrich = st.checkbox(
        "Identifier les acheteurs avec Sirene",
        value=True,
        help="Un appel Hémicycle supplémentaire, soit 1 crédit par page.",
    )
    use_semantic = st.checkbox(
        "Classement sémantique hybride",
        value=True,
        help="Combine le sens de votre offre avec les critères métier explicables.",
    )
    limit = st.slider("Lignes analysées", 20, 100, 100, 10)
    run = st.button("Analyser les opportunités", type="primary", width="stretch")

    st.divider()
    if analysis == "future":
        st.caption(
            "Score hybride : sens (35), mots (15), territoire (15), montant (15) "
            "et calendrier (20)."
        )
    else:
        st.caption(
            "Score hybride : sens (35), mots (15), territoire (15), montant (15) "
            "et renouvellement estimé (20)."
        )

with st.expander("Les trois jeux de données utilisés"):
    st.markdown(
        "- **`projets_achats_publics`** : achats annoncés avant l'appel d'offres.\n"
        "- **`marches_publics`** : contrats notifiés, montants et titulaires.\n"
        "- **`sirene_etablissements`** : nom, activité et commune de l'acheteur."
    )

if not run:
    st.info(
        "Cliquez sur **Analyser les opportunités**. Sans clé Hémicycle, la vue "
        "future utilise automatiquement un échantillon synthétique clairement signalé."
    )
    st.stop()

try:
    with st.spinner("Lecture des données publiques…"):
        records, source_label = load_records(
            analysis, provider, keyword, department, category, limit
        )
except (ValueError, decp.DecpError, hemicycle.HemicycleError) as exc:
    st.error(str(exc))
    st.stop()

if analysis == "future":
    semantic_values = None
    if use_semantic:
        documents = [
            " ".join(
                str(row.get(key, "") or "")
                for key in ("libelle", "description", "code_s_cpv", "categorie_d_achat")
            )
            for row in records
        ]
        semantic_values = semantic_scores(keyword, documents)
    frame = score_projects(
        records,
        keyword=keyword,
        location=department,
        minimum=minimum,
        maximum=maximum,
        semantic_scores=semantic_values,
    )
    identifier_column, identifier_type = "siren_de_l_entite_acheteuse", "siren"
else:
    semantic_values = None
    if use_semantic:
        documents = [
            " ".join(str(row.get(key, "") or "") for key in ("objet", "codecpv", "nature"))
            for row in records
        ]
        semantic_values = semantic_scores(keyword, documents)
    frame = score_contracts(
        records,
        keyword=keyword,
        location=department,
        minimum=minimum,
        maximum=maximum,
        semantic_scores=semantic_values,
    )
    identifier_column, identifier_type = "acheteur_id", "siret"

if frame.empty:
    st.warning("Aucune ligne ne correspond à cette recherche.")
    st.stop()

sirene_label = "Enrichissement désactivé"
if enrich:
    identifiers = tuple(
        frame[identifier_column].dropna().astype(str).drop_duplicates().head(100)
    )
    try:
        with st.spinner("Identification des acheteurs via Sirene…"):
            organizations, sirene_label = load_organizations(
                identifiers,
                identifier_type,
                synthetic="synthétiques" in source_label.lower(),
            )
        frame = enrich_with_organizations(
            frame, organizations, identifier_type=identifier_type
        )
    except hemicycle.HemicycleError as exc:
        st.warning(f"Enrichissement Sirene ignoré : {exc}")
        frame = enrich_with_organizations(frame, [], identifier_type=identifier_type)
else:
    frame = enrich_with_organizations(frame, [], identifier_type=identifier_type)

st.success(f"{len(frame)} lignes analysées · {source_label} · {sirene_label}")

if analysis == "future":
    next_90 = date.today() + timedelta(days=90)
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Projets", len(frame))
    metric2.metric(
        "Publications sous 90 j",
        int(
            frame["date_previsionnelle_de_publication"].between(
                pd.Timestamp(date.today()), pd.Timestamp(next_90)
            ).sum()
        ),
    )
    metric3.metric(
        "Acheteurs",
        int(frame[identifier_column].nunique(dropna=True)),
    )
    metric4.metric("Meilleur score", f"{int(frame['score'].max())}/100")

    left, right = st.columns([1.35, 0.65])
    with left:
        st.subheader("Opportunités annoncées")
        display_columns = [
            column for column in PROJECT_DISPLAY_COLUMNS if column in frame.columns
        ]
        display = frame[display_columns].head(20).copy()
        for column in (
            "date_previsionnelle_de_publication",
            "date_cible_de_remise_des_offres",
        ):
            display[column] = display[column].dt.strftime("%Y-%m-%d")
        st.dataframe(
            display,
            hide_index=True,
            width="stretch",
            column_config={
                "libelle": "Projet",
                "denomination_acheteur": "Acheteur",
                "categorie_d_achat": "Catégorie",
                "montant_estime_du_marche": "Budget estimé",
                "date_previsionnelle_de_publication": "Publication prévue",
                "date_cible_de_remise_des_offres": "Remise des offres",
                "departement_s_d_execution_du_marche": "Département(s)",
                "lien_vers_la_consultation": st.column_config.LinkColumn(
                    "Consultation", display_text="Ouvrir"
                ),
                "score": st.column_config.ProgressColumn(
                    "Score", min_value=0, max_value=100
                ),
            },
        )
    with right:
        st.subheader("Répartition territoriale")
        chart_data = (
            frame.assign(
                territoire=frame["departement_s_d_execution_du_marche"]
                .fillna("Non renseigné")
                .astype(str)
            )
            .groupby("territoire", as_index=False)
            .agg(projets=("libelle", "count"))
            .sort_values("projets", ascending=False)
            .head(10)
        )
        fig = px.bar(
            chart_data,
            x="territoire",
            y="projets",
            labels={"territoire": "Territoire", "projets": "Projets"},
        )
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=420)
        st.plotly_chart(fig, width="stretch")

    with st.expander("Pourquoi le premier projet est prioritaire ?", expanded=True):
        top = frame.iloc[0]
        cols = st.columns(5)
        cols[0].metric("Sens", f"{int(top['score_semantique'])}/35")
        cols[1].metric("Mots-clés", f"{int(top['score_mots'])}/30 brut")
        cols[2].metric("Territoire", f"{int(top['score_territoire'])}/20 brut")
        cols[3].metric("Montant", f"{int(top['score_montant'])}/20 brut")
        cols[4].metric("Calendrier", f"{int(top['score_calendrier'])}/30 brut")
        st.write(top["libelle"])
        st.json(project_evidence(top.to_dict()), expanded=False)
else:
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Marchés", len(frame))
    metric2.metric(
        "Montant médian",
        f"{frame['montant'].median():,.0f} €".replace(",", " ")
        if frame["montant"].notna().any()
        else "N/D",
    )
    metric3.metric("Acheteurs", int(frame[identifier_column].nunique(dropna=True)))
    metric4.metric("Meilleur score", f"{int(frame['score'].max())}/100")

    left, right = st.columns([1.3, 0.7])
    with left:
        st.subheader("Historique et renouvellements")
        historical_columns = [
            "objet",
            "denomination_acheteur",
            *[column for column in DISPLAY_COLUMNS if column != "objet"],
        ]
        display = frame[historical_columns].head(20).copy()
        display["datenotification"] = display["datenotification"].dt.strftime(
            "%Y-%m-%d"
        )
        display["date_fin_estimee"] = display["date_fin_estimee"].dt.strftime(
            "%Y-%m-%d"
        )
        st.dataframe(
            display,
            hide_index=True,
            width="stretch",
            column_config={
                "objet": "Objet",
                "denomination_acheteur": "Acheteur",
                "montant": st.column_config.NumberColumn("Montant", format="%.0f €"),
                "datenotification": "Notification",
                "dureemois": "Durée (mois)",
                "date_fin_estimee": "Fin estimée",
                "lieuexecution_code": "Lieu",
                "acheteur_id": "Acheteur (SIRET)",
                "score": st.column_config.ProgressColumn(
                    "Score", min_value=0, max_value=100
                ),
            },
        )
    with right:
        st.subheader("Montants par territoire")
        chart_data = (
            frame.assign(
                territoire=frame["lieuexecution_code"]
                .fillna("Non renseigné")
                .astype(str)
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
            labels={"territoire": "Territoire", "montant": "Montant (€)"},
        )
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=420)
        st.plotly_chart(fig, width="stretch")

    with st.expander("Pourquoi le premier marché est prioritaire ?", expanded=True):
        top = frame.iloc[0]
        cols = st.columns(5)
        cols[0].metric("Sens", f"{int(top['score_semantique'])}/35")
        cols[1].metric("Mots-clés", f"{int(top['score_mots'])}/30 brut")
        cols[2].metric("Territoire", f"{int(top['score_territoire'])}/20 brut")
        cols[3].metric("Montant", f"{int(top['score_montant'])}/20 brut")
        cols[4].metric("Renouvellement", f"{int(top['score_renouvellement'])}/30 brut")
        st.write(top["objet"])
        st.json(contract_evidence(top.to_dict()), expanded=False)

st.subheader("Capitaliser et exporter")
action_col, save_col, export_col = st.columns(3)
top_record = frame.iloc[0].to_dict()
opportunity_key = str(
    top_record.get("code")
    or f"{top_record.get('acheteur_id', '')}:{top_record.get('objet', '')}"
)
with action_col:
    label = st.selectbox(
        "Retour sur la première opportunité",
        ["pertinent", "non_pertinent", "a_contacter", "contacte", "gagne", "perdu"],
    )
    if st.button("Enregistrer le retour"):
        storage.record_feedback(
            opportunity_key,
            label,
            "projets_achats_publics" if analysis == "future" else "marches_publics",
            top_record,
        )
        st.toast("Retour enregistré pour le futur modèle de ranking.")
with save_col:
    search_name = st.text_input("Nom de la veille", value=f"Veille {keyword}")
    alerts_enabled = st.checkbox("Préparer une alerte quotidienne", value=False)
    if st.button("Sauvegarder la veille"):
        storage.save_search(
            search_name,
            {
                "analysis": analysis,
                "keyword": keyword,
                "department": department,
                "category": category,
                "minimum": minimum,
                "maximum": maximum,
            },
            alerts_enabled,
        )
        st.toast("Veille sauvegardée. L'envoi automatique reste désactivé.")
with export_col:
    csv = frame.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Télécharger les résultats CSV",
        data=csv,
        file_name="cap-marches-opportunites.csv",
        mime="text/csv",
        width="stretch",
    )

st.subheader("Préparer l'approche commerciale")
if not llm.is_configured():
    st.info(
        "Ajoutez `FEATHERLESS_API_KEY` dans `.env` pour générer une note. "
        "Le classement fonctionne sans IA."
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
        "être présentées comme des achats réels."
    )
else:
    st.caption(
        "Sources : APProch, DECP et répertoire Sirene via Hémicycle. "
        "Licence Ouverte 2.0 (Etalab). Les scores et dates de fin sont des "
        "indicateurs d'aide à la prospection, pas des prédictions certaines."
    )
