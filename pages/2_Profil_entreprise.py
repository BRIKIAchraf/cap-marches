"""Mémoire durable de l'entreprise, sans secret ni donnée personnelle."""

from __future__ import annotations

import streamlit as st

import storage


st.set_page_config(page_title="Profil entreprise · Cap Marchés", page_icon="🏢", layout="wide")
st.title("🏢 Profil de votre entreprise")
st.caption("Cette mémoire sert de contexte au moteur sémantique et à l'agent de veille.")

profile = storage.load_profile() or {}
with st.form("company-profile"):
    company_name = st.text_input("Nom de l'entreprise", value=profile.get("company_name", ""))
    offer = st.text_area(
        "Offre et savoir-faire",
        value=profile.get("offer", ""),
        placeholder="Ex. Intégration de logiciels RH SaaS, migration et accompagnement…",
        height=140,
    )
    keywords = st.text_input("Mots-clés", value=profile.get("keywords", ""))
    cpv_codes = st.text_input("Codes CPV", value=profile.get("cpv_codes", ""))
    departments = st.text_input("Départements cibles", value=profile.get("departments", ""))
    minimum, maximum = st.columns(2)
    min_value = minimum.number_input(
        "Montant minimum (€)", min_value=0.0, value=float(profile.get("minimum", 0)), step=10_000.0
    )
    max_value = maximum.number_input(
        "Montant maximum (€)", min_value=0.0, value=float(profile.get("maximum", 1_000_000)), step=10_000.0
    )
    submitted = st.form_submit_button("Enregistrer le profil", type="primary")

if submitted:
    if max_value < min_value:
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
                    "minimum": min_value,
                    "maximum": max_value,
                }
            )
            st.success("Profil enregistré dans la base locale.")
        except ValueError as exc:
            st.error(str(exc))

st.info("Ne stockez ici aucune clé API, aucun mot de passe et aucune donnée personnelle.")
