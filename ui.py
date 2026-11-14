"""Design system partagé et composants de storytelling pour Cap Marchés."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st
from streamlit.errors import StreamlitPageNotFoundError


CSS = """
<style>
  :root {
    --navy: #0f1f38;
    --navy-light: #182e52;
    --blue: #2864dc;
    --blue-dark: #1b4bb0;
    --cyan: #19b5bc;
    --cyan-glow: rgba(25, 181, 188, 0.16);
    --ink: #111e33;
    --muted: #5e718d;
    --surface: #ffffff;
    --soft: #f4f7fc;
    --line: #d8e3f0;
    --success: #128266;
    --success-bg: #e7f7f3;
    --warning: #b36314;
    --warning-bg: #fdf3e7;
    --gold: #f59e0b;
    --radius-lg: 20px;
    --radius-md: 14px;
    --radius-sm: 8px;
    --shadow-soft: 0 10px 30px rgba(16, 35, 65, 0.06);
    --shadow-hover: 0 16px 42px rgba(16, 35, 65, 0.12);
  }

  .stApp {
    background: linear-gradient(180deg, #f7f9fd 0%, #ffffff 35%);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }

  [data-testid="stHeader"] { background: transparent; }
  [data-testid="stSidebar"] {
    background: linear-gradient(185deg, #0d1a2f 0%, #132542 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
  }
  [data-testid="stSidebar"] * { color: #edf4ff; }
  [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stCaption { color: #adc0d9 !important; font-weight: 550; }
  [data-testid="stSidebar"] input { color: #17243a !important; font-weight: 500; }
  [data-testid="stSidebar"] [data-baseweb="select"] * { color: #17243a !important; }
  [data-testid="stSidebar"] hr { border-color: rgba(255, 255, 255, 0.12); }

  .block-container {
    max-width: 1440px;
    padding-top: 1.8rem;
    padding-bottom: 4rem;
  }

  h1, h2, h3, h4 { color: var(--navy); letter-spacing: -0.025em; font-weight: 780; }
  h1 { font-size: clamp(2rem, 3.2vw, 2.9rem); line-height: 1.15; }
  h2 { font-size: clamp(1.4rem, 2vw, 1.85rem); }

  /* Brand */
  .cm-brand { display: flex; align-items: center; gap: 0.85rem; margin: 0.25rem 0 1.6rem; }
  .cm-mark {
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    border-radius: 13px;
    background: linear-gradient(135deg, #38d6df 0%, #2864dc 100%);
    color: #fff;
    font-weight: 900;
    font-size: 1.15rem;
    box-shadow: 0 8px 24px rgba(40, 100, 220, 0.35);
  }
  .cm-brand-title { font-size: 1.12rem; font-weight: 800; color: #fff; line-height: 1.1; }
  .cm-brand-sub { font-size: 0.74rem; color: #9ab4d6; margin-top: 0.2rem; font-weight: 500; }

  .cm-nav-link {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.55rem 0.75rem;
    margin: 0.2rem 0;
    color: #eef5ff !important;
    text-decoration: none !important;
    border-radius: 10px;
    font-size: 0.92rem;
    font-weight: 550;
    transition: all 0.15s ease;
  }
  .cm-nav-link:hover {
    background: rgba(255, 255, 255, 0.1);
    transform: translateX(3px);
  }

  /* Landing Hero */
  .cm-hero {
    position: relative;
    overflow: hidden;
    padding: 2.4rem 2.6rem;
    border: 1px solid var(--line);
    border-radius: 26px;
    background: linear-gradient(135deg, #ffffff 0%, #f1f6ff 55%, #e9f2ff 100%);
    box-shadow: 0 14px 44px rgba(27, 65, 120, 0.08);
    margin-bottom: 2rem;
  }
  .cm-hero:before {
    content: "";
    position: absolute;
    width: 320px;
    height: 320px;
    border-radius: 50%;
    right: -100px;
    top: -120px;
    background: radial-gradient(circle, rgba(40, 100, 220, 0.18) 0%, transparent 70%);
    pointer-events: none;
  }
  .cm-hero:after {
    content: "";
    position: absolute;
    width: 240px;
    height: 240px;
    border-radius: 50%;
    right: 180px;
    bottom: -110px;
    background: radial-gradient(circle, rgba(25, 181, 188, 0.14) 0%, transparent 70%);
    pointer-events: none;
  }
  .cm-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--blue);
    background: rgba(40, 100, 220, 0.09);
    padding: 0.32rem 0.85rem;
    border-radius: 999px;
    font-size: 0.74rem;
    letter-spacing: 0.08em;
    font-weight: 800;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
    border: 1px solid rgba(40, 100, 220, 0.15);
  }
  .cm-hero h1 { margin: 0 0 0.85rem; max-width: 920px; }
  .cm-hero p.cm-hero-desc {
    color: var(--muted);
    font-size: 1.12rem;
    max-width: 860px;
    margin: 0 0 1.4rem;
    line-height: 1.65;
  }

  .cm-pills { display: flex; flex-wrap: wrap; gap: 0.55rem; margin-top: 1rem; }
  .cm-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.42rem;
    padding: 0.38rem 0.8rem;
    border-radius: 999px;
    background: #ffffff;
    border: 1px solid var(--line);
    color: #3b4e6b;
    font-size: 0.8rem;
    font-weight: 650;
    box-shadow: 0 2px 8px rgba(15, 31, 56, 0.04);
  }
  .cm-dot { width: 8px; height: 8px; border-radius: 50%; background: #93a4bb; }
  .cm-dot.ok { background: #16a37f; box-shadow: 0 0 0 3px #d6f4ea; }
  .cm-dot.demo { background: #e8982a; box-shadow: 0 0 0 3px #fff1db; }

  /* KPI Grid */
  .cm-kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1.1rem;
    margin: 1.6rem 0 2.2rem;
  }
  .cm-kpi-card {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    padding: 1.35rem 1.45rem;
    box-shadow: var(--shadow-soft);
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .cm-kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-hover);
  }
  .cm-kpi-card:before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, var(--blue) 0%, var(--cyan) 100%);
  }
  .cm-kpi-num {
    font-size: 2.1rem;
    font-weight: 850;
    color: var(--navy);
    line-height: 1.1;
    margin-bottom: 0.35rem;
  }
  .cm-kpi-label { font-size: 0.95rem; font-weight: 750; color: #223758; margin-bottom: 0.25rem; }
  .cm-kpi-desc { font-size: 0.8rem; color: var(--muted); line-height: 1.45; }

  /* Storytelling Compare Grid */
  .cm-compare-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.4rem;
    margin: 1.4rem 0 2rem;
  }
  .cm-compare-card {
    border-radius: var(--radius-lg);
    padding: 1.6rem 1.8rem;
    border: 1px solid var(--line);
  }
  .cm-compare-bad {
    background: #fafbfe;
    border-left: 5px solid #d9534f;
  }
  .cm-compare-good {
    background: linear-gradient(135deg, #ffffff 0%, #f2f9fb 100%);
    border-left: 5px solid var(--success);
    box-shadow: 0 10px 30px rgba(18, 130, 102, 0.08);
  }
  .cm-compare-badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.8rem;
  }
  .cm-badge-bad { background: #fee2e2; color: #991b1b; }
  .cm-badge-good { background: #dcfce7; color: #166534; }
  .cm-compare-title { font-size: 1.15rem; font-weight: 750; margin-bottom: 0.75rem; color: var(--navy); }
  .cm-compare-list { list-style: none; padding: 0; margin: 0; }
  .cm-compare-list li {
    position: relative;
    padding-left: 1.55rem;
    margin-bottom: 0.65rem;
    font-size: 0.9rem;
    line-height: 1.5;
    color: #3b4e6b;
  }
  .cm-compare-list li:before {
    position: absolute;
    left: 0;
    top: 0;
    font-size: 1rem;
    font-weight: 700;
  }
  .cm-compare-bad .cm-compare-list li:before { content: "✕"; color: #dc2626; }
  .cm-compare-good .cm-compare-list li:before { content: "✓"; color: #16a34a; }

  /* Process Timeline */
  .cm-step-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.1rem;
    margin: 1.5rem 0 2rem;
  }
  .cm-step-card {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    padding: 1.4rem 1.3rem;
    box-shadow: var(--shadow-soft);
    position: relative;
    transition: transform 0.2s ease;
  }
  .cm-step-card:hover { transform: translateY(-4px); }
  .cm-step-num {
    display: grid;
    place-items: center;
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: linear-gradient(135deg, #2864dc 0%, #173b88 100%);
    color: #ffffff;
    font-weight: 850;
    font-size: 1.05rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 4px 14px rgba(40, 100, 220, 0.25);
  }
  .cm-step-title { font-size: 1rem; font-weight: 750; color: var(--navy); margin-bottom: 0.4rem; }
  .cm-step-text { font-size: 0.82rem; color: var(--muted); line-height: 1.5; }

  /* Badges NOUVEAU / DÉJÀ VU / SIRENE */
  .cm-tag-new {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    background: #eef2ff;
    color: #3730a3;
    font-size: 0.72rem;
    font-weight: 800;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    border: 1px solid #c7d2fe;
    letter-spacing: 0.03em;
  }
  .cm-tag-seen {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    background: #f1f5f9;
    color: #475569;
    font-size: 0.72rem;
    font-weight: 650;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
  }
  .cm-tag-sirene {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    background: #ecfdf5;
    color: #065f46;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    border: 1px solid #a7f3d0;
  }

  /* Section Header */
  .cm-section {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    margin: 1.8rem 0 0.85rem;
    border-bottom: 2px solid #eef3f9;
    padding-bottom: 0.6rem;
  }
  .cm-section h2 { margin: 0; }
  .cm-section p { color: var(--muted); margin: 0.25rem 0 0; font-size: 0.9rem; }

  /* UI controls */
  [data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1.1rem 1.2rem;
    box-shadow: var(--shadow-soft);
  }
  [data-testid="stMetricLabel"] { color: var(--muted); font-size: 0.85rem; font-weight: 600; }
  [data-testid="stMetricValue"] { color: var(--navy); font-weight: 800; font-size: 1.8rem; }
  [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 16px; overflow: hidden; box-shadow: var(--shadow-soft); }

  [data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0.55rem;
    border-bottom: 2px solid var(--line);
    margin-bottom: 1.2rem;
  }
  [data-testid="stTabs"] button {
    border-radius: 12px 12px 0 0;
    padding: 0.75rem 1.3rem;
    font-weight: 700;
    font-size: 0.95rem;
  }

  .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
    border-radius: 12px;
    font-weight: 750;
    min-height: 2.75rem;
    transition: all 0.2s ease;
  }
  .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
    transform: translateY(-1px);
  }
  .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    border: 0;
    box-shadow: 0 8px 22px rgba(37, 99, 235, 0.28);
  }

  [data-testid="stExpander"] {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 16px;
    box-shadow: var(--shadow-soft);
  }

  .cm-empty {
    text-align: center;
    padding: 3.5rem 1.5rem;
    border: 2px dashed #cbd5e1;
    border-radius: 22px;
    background: #ffffff;
    box-shadow: var(--shadow-soft);
  }
  .cm-empty-icon { font-size: 2.4rem; margin-bottom: 0.6rem; }
  .cm-empty h3 { margin: 0.3rem 0; font-size: 1.35rem; }
  .cm-empty p { color: var(--muted); max-width: 620px; margin: 0.4rem auto 0; font-size: 0.95rem; }

  @media (max-width: 900px) {
    .cm-step-grid { grid-template-columns: 1fr 1fr; }
    .cm-compare-grid { grid-template-columns: 1fr; }
  }
  @media (max-width: 600px) {
    .cm-step-grid { grid-template-columns: 1fr; }
  }
</style>
"""


def setup_page(title: str, icon: str = "🎯") -> None:
    st.set_page_config(page_title=f"{title} · Cap Marchés", page_icon=icon, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


def brand() -> None:
    st.markdown(
        """
        <div class="cm-brand">
          <div class="cm-mark">CM</div>
          <div>
            <div class="cm-brand-title">Cap Marchés</div>
            <div class="cm-brand-sub">Intelligence commerciale & Commande publique</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def navigation() -> None:
    with st.sidebar:
        brand()
        st.caption("NAVIGATION")
        safe_page_link("app.py", "Radar d'opportunités", "🎯")
        safe_page_link("pages/2_Profil_entreprise.py", "Profil entreprise", "🏢")
        safe_page_link("pages/3_Agent_IA.py", "Agent de veille", "🤖")
        safe_page_link("pages/4_Apprentissage.py", "Apprentissage", "📈")


def safe_page_link(page: str, label: str, icon: str | None = None) -> bool:
    """Affiche un lien multipage et reste testable en exécution isolée."""
    if page == "app.py":
        st.markdown(
            f'<a class="cm-nav-link" href="/" target="_self">{escape(icon or "")} {escape(label)}</a>',
            unsafe_allow_html=True,
        )
        return True
    try:
        st.page_link(page, label=label, icon=icon)
        return True
    except StreamlitPageNotFoundError:
        return False


def hero(
    title: str,
    subtitle: str,
    eyebrow: str,
    pills: list[tuple[str, str]] | None = None,
) -> None:
    rendered = ""
    if pills:
        rendered = '<div class="cm-pills">' + "".join(
            f'<span class="cm-pill"><span class="cm-dot {escape(kind)}"></span>{escape(label)}</span>'
            for label, kind in pills
        ) + "</div>"
    st.markdown(
        f"""
        <section class="cm-hero">
          <div class="cm-eyebrow">{escape(eyebrow)}</div>
          <h1>{escape(title)}</h1>
          <p class="cm-hero-desc">{escape(subtitle)}</p>
          {rendered}
        </section>
        """,
        unsafe_allow_html=True,
    )


def landing_storytelling() -> None:
    """Affiche la section de storytelling immersive pour la Landing Page."""
    st.markdown(
        """
        <div class="cm-kpi-grid">
          <div class="cm-kpi-card">
            <div class="cm-kpi-num">200+ Mrd €</div>
            <div class="cm-kpi-label">Commande publique annuelle</div>
            <div class="cm-kpi-desc">Le premier marché de France ouvert aux entreprises et PME innovantes.</div>
          </div>
          <div class="cm-kpi-card">
            <div class="cm-kpi-num">90 à 365 j</div>
            <div class="cm-kpi-label">Anticipation stratégique</div>
            <div class="cm-kpi-desc">Détectez les projets d'achats dès la programmation budgétaire, bien avant le CCTP officiel.</div>
          </div>
          <div class="cm-kpi-card">
            <div class="cm-kpi-num">100% Souverain</div>
            <div class="cm-kpi-label">Données officielles d'État</div>
            <div class="cm-kpi-desc">Croisement direct APProch, DECP et répertoire national Sirene de l'INSEE.</div>
          </div>
          <div class="cm-kpi-card">
            <div class="cm-kpi-num">0 Hallucination</div>
            <div class="cm-kpi-label">Scoring hybride transparent</div>
            <div class="cm-kpi-desc">Chaque recommandation est rigoureusement appuyée sur un dossier de preuves vérifiables.</div>
          </div>
        </div>

        <div style="margin: 2.2rem 0 1rem;">
          <h2 style="margin-bottom: 0.3rem;">Pourquoi la veille classique échoue (et comment Cap Marchés change la donne)</h2>
          <p style="color: var(--muted); margin: 0; font-size: 1rem;">La majorité des entreprises perdent les marchés publics avant même d'avoir postulé.</p>
        </div>

        <div class="cm-compare-grid">
          <div class="cm-compare-card cm-compare-bad">
            <span class="cm-compare-badge cm-badge-bad">La veille traditionnelle</span>
            <div class="cm-compare-title">Réactive & Tardive</div>
            <ul class="cm-compare-list">
              <li><strong>Découverte à J-20</strong> : L'appel d'offres est déjà rédigé, vous découvrez le cahier des charges trop tard.</li>
              <li><strong>Temps perdu</strong> : Des dizaines d'heures passées à éplucher le BOAMP, le JOUE et des dizaines de profils acheteurs.</li>
              <li><strong>Angle mort sur l'acheteur</strong> : Aucun historique sur les titulaires sortants ni sur les budgets réels.</li>
              <li><strong>Mots-clés rigides</strong> : Des centaines de marchés pertinents manqués à cause de libellés administratifs abscons.</li>
            </ul>
          </div>
          <div class="cm-compare-card cm-compare-good">
            <span class="cm-compare-badge cm-badge-good">Le Radar Cap Marchés</span>
            <div class="cm-compare-title">Prédictif & Augmenté</div>
            <ul class="cm-compare-list">
              <li><strong>Anticipation à J-180</strong> : Détectez les projets avant l'appel d'offres grâce aux déclarations officielles APProch.</li>
              <li><strong>Compréhension sémantique IA</strong> : L'algorithme saisit le sens réel de votre savoir-faire, pas de simples mots-clés.</li>
              <li><strong>Identité Sirene enrichie</strong> : Dénomination officielle, commune, direction acheteuse et volume budgétaire.</li>
              <li><strong>Sourçage légal autorisé</strong> : Prenez contact en amont avec les acheteurs dans le cadre légal du Code de la commande publique.</li>
            </ul>
          </div>
        </div>

        <div style="margin: 2.4rem 0 1rem;">
          <h2 style="margin-bottom: 0.3rem;">La méthode en 4 étapes : Du signal faible au contrat signé</h2>
          <p style="color: var(--muted); margin: 0; font-size: 1rem;">Un processus commercial fluide et rigoureux pour transformer la donnée publique en chiffre d'affaires.</p>
        </div>

        <div class="cm-step-grid">
          <div class="cm-step-card">
            <div class="cm-step-num">1</div>
            <div class="cm-step-title">Détecter en amont</div>
            <div class="cm-step-text">Cap Marchés interroge les projets d'achats prévisionnels et les fins de marchés existants.</div>
          </div>
          <div class="cm-step-card">
            <div class="cm-step-num">2</div>
            <div class="cm-step-title">Scorer & Justifier</div>
            <div class="cm-step-text">Chaque opportunité reçoit une note sur 100 décomposée : sens métier, territoire, budget et échéance.</div>
          </div>
          <div class="cm-step-card">
            <div class="cm-step-num">3</div>
            <div class="cm-step-title">Préparer l'approche</div>
            <div class="cm-step-text">Consultez le dossier de preuves, enrichi de l'identité Sirene et d'une note commerciale factuelle.</div>
          </div>
          <div class="cm-step-card">
            <div class="cm-step-num">4</div>
            <div class="cm-step-title">Veille automatisée</div>
            <div class="cm-step-text">Recevez automatiquement par alerte quotidienne uniquement les nouveaux marchés pertinents.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="cm-section"><div><h2>{escape(title)}</h2><p>{escape(subtitle)}</p></div></div>',
        unsafe_allow_html=True,
    )


def empty_state(title: str, text: str, icon: str = "⌁") -> None:
    st.markdown(
        f'<div class="cm-empty"><div class="cm-empty-icon">{escape(icon)}</div><h3>{escape(title)}</h3><p>{escape(text)}</p></div>',
        unsafe_allow_html=True,
    )


def callout(text: str) -> None:
    st.markdown(f'<div class="cm-callout">{escape(text)}</div>', unsafe_allow_html=True)


def euro(value: object) -> str:
    try:
        return f"{float(value):,.0f} €".replace(",", " ")
    except (TypeError, ValueError):
        return "Non renseigné"
