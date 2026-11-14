"""Mémoire durable de l'entreprise."""

from __future__ import annotations

import streamlit as st

import storage
from ui import hero, navigation, section, setup_page


setup_page("Profil entreprise", "🏢")
navigation()
profile = storage.load_profile() or {}

hero(
    "Le contexte qui rend l'agent pertinent",
    "Décrivez votre offre une fois. Le moteur sémantique et l'agent réutiliseront ce profil pour cibler, classer et expliquer les opportunités.",
    "Mémoire d'entreprise",
    [
        ("Profil enregistré" if profile else "Profil à compléter", "ok" if profile else "demo"),
        ("Stockage local sécurisé", "ok"),
        ("Aucun secret dans ce profil", "ok"),
    ],
)

section(
    "Positionnement commercial",
    "Soyez précis sur les problèmes résolus, vos prestations et vos marchés cibles.",
)

preset_col1, preset_col2 = st.columns([1.2, 0.8])
with preset_col1:
    if st.button("✨ Appliquer le profil recommandé (Omegup · SaaS RH)", help="Remplit automatiquement les mots-clés SIRH et codes CPV recommandés."):
        storage.ensure_default_profile()
        st.success("Profil mis à jour avec les paramètres recommandés !")
        st.rerun()

with st.form("company-profile"):
    identity, targeting = st.columns([1.15, 0.85])
    with identity:
        company_name = st.text_input(
            "Nom de l'entreprise *",
            value=profile.get("company_name", ""),
            placeholder="Ex. Nova Conseil",
        )
        offer = st.text_area(
            "Offre et savoir-faire *",
            value=profile.get("offer", ""),
            placeholder=(
                "Ex. Nous intégrons des logiciels RH SaaS et accompagnons les "
                "organisations publiques dans la migration, la formation et le support."
            ),
            height=170,
        )
        keywords = st.text_input(
            "Mots-clés métier",
            value=profile.get("keywords", ""),
            placeholder="SIRH, paie, SaaS, ressources humaines, migration",
        )
    with targeting:
        cpv_codes = st.text_input(
            "Codes CPV",
            value=profile.get("cpv_codes", ""),
            placeholder="48000000, 72260000",
        )
        departments = st.text_input(
            "Départements cibles",
            value=profile.get("departments", ""),
            placeholder="75, 92, 93, 94",
        )
        minimum = st.number_input(
            "Montant minimum (€)",
            min_value=0.0,
            value=float(profile.get("minimum", 0)),
            step=10_000.0,
        )
        maximum = st.number_input(
            "Montant maximum (€)",
            min_value=0.0,
            value=float(profile.get("maximum", 1_000_000)),
            step=10_000.0,
        )
    submitted = st.form_submit_button(
        "Enregistrer le profil", type="primary", width="stretch"
    )

if submitted:
    if maximum < minimum:
        st.error("Le montant maximum doit être supérieur au minimum.")
    else:
        try:
            storage.save_profile(
                {
                    "company_name": company_name,
                    "offer": offer,
                    "keywords": keywords,
                    "cpv_codes": cpv_codes,
                    "departments": departments,
                    "minimum": minimum,
                    "maximum": maximum,
                }
            )
            st.success("Profil enregistré. L'agent peut désormais l'utiliser.")
            st.balloons()
        except ValueError as exc:
            st.error(str(exc))

section("Bon profil, meilleurs résultats")
first, second, third = st.columns(3)
first.info("**Décrivez les résultats livrés**\n\nPréférez « migration SIRH et formation » à « informatique ».")
second.info("**Ciblez vos territoires**\n\nSéparez les départements par des virgules.")
third.info("**Restez non sensible**\n\nNe saisissez ni clé API, ni mot de passe, ni donnée personnelle.")
