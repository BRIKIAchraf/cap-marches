"""Pied de page indépendant du design system principal."""

from __future__ import annotations

import streamlit as st


def render_footer() -> None:
    st.markdown(
        """
        <footer class="cm-footer">
          <div class="cm-footer-brand">
            <span style="display:inline-grid;place-items:center;width:26px;height:26px;border-radius:8px;background:linear-gradient(135deg,#38d6df 0%, #2864dc 100%);color:#fff;font-weight:900;font-size:0.75rem;">CM</span>
            Cap Marchés
          </div>
          <div class="cm-footer-meta">Veille commerciale, scoring explicable et preuves publiques.</div>
          <div class="cm-footer-links">
            <a href="/">Radar</a>
            <a href="/2_Profil_entreprise">Profil</a>
            <a href="/3_Agent_IA">Agent</a>
            <a href="/4_Apprentissage">Apprentissage</a>
          </div>
        </footer>
        """,
        unsafe_allow_html=True,
    )
