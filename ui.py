"""Design system partagé de Cap Marchés."""

from __future__ import annotations

from html import escape

import streamlit as st
from streamlit.errors import StreamlitPageNotFoundError


CSS = """
<style>
  :root {
    --navy: #11233f;
    --blue: #2864dc;
    --cyan: #35b7c9;
    --ink: #17243a;
    --muted: #64748b;
    --surface: #ffffff;
    --soft: #f3f6fb;
    --line: #dce5f1;
    --success: #14866d;
    --warning: #b66a18;
  }
  .stApp { background: linear-gradient(180deg, #f7f9fd 0%, #ffffff 42%); color: var(--ink); }
  [data-testid="stHeader"] { background: transparent; }
  [data-testid="stSidebar"] { background: #10213b; border-right: 0; }
  [data-testid="stSidebar"] * { color: #eef5ff; }
  [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stCaption { color: #bccae0 !important; }
  [data-testid="stSidebar"] input { color: #17243a !important; }
  [data-testid="stSidebar"] [data-baseweb="select"] * { color: #17243a !important; }
  [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.14); }
  .block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 4rem; }
  h1, h2, h3 { color: var(--navy); letter-spacing: -.025em; }
  h1 { font-weight: 760; }
  .cm-brand { display:flex; align-items:center; gap:.8rem; margin:.25rem 0 1.5rem; }
  .cm-mark { display:grid; place-items:center; width:42px; height:42px; border-radius:13px;
    background:linear-gradient(135deg,#52d2d8,#3d73ec); color:#fff; font-weight:800; box-shadow:0 8px 22px rgba(34,105,215,.28); }
  .cm-brand-title { font-size:1.05rem; font-weight:750; color:#fff; line-height:1.1; }
  .cm-brand-sub { font-size:.73rem; color:#9fb1ca; margin-top:.15rem; }
  .cm-nav-link { display:flex; align-items:center; gap:.55rem; padding:.48rem .6rem; margin:.12rem 0;
    color:#eef5ff !important; text-decoration:none !important; border-radius:9px; font-size:.9rem; }
  .cm-nav-link:hover { background:rgba(255,255,255,.09); }
  .cm-hero { position:relative; overflow:hidden; padding:1.65rem 1.8rem; border:1px solid #d8e3f2;
    border-radius:22px; background:linear-gradient(130deg,#fff 20%,#edf4ff 100%); box-shadow:0 12px 38px rgba(31,63,104,.08); margin-bottom:1.35rem; }
  .cm-hero:after { content:""; position:absolute; width:250px; height:250px; border-radius:50%; right:-90px; top:-120px; background:radial-gradient(circle,#74d9df66,transparent 68%); }
  .cm-eyebrow { color:var(--blue); text-transform:uppercase; font-size:.72rem; letter-spacing:.12em; font-weight:800; margin-bottom:.45rem; }
  .cm-hero h1 { font-size:clamp(1.8rem,3vw,2.65rem); margin:0 0 .45rem; }
  .cm-hero p { color:var(--muted); font-size:1rem; max-width:780px; margin:0; line-height:1.6; }
  .cm-pills { display:flex; flex-wrap:wrap; gap:.45rem; margin-top:1rem; }
  .cm-pill { display:inline-flex; align-items:center; gap:.38rem; padding:.35rem .65rem; border-radius:999px; background:#fff; border:1px solid var(--line); color:#42526b; font-size:.76rem; font-weight:650; }
  .cm-dot { width:7px; height:7px; border-radius:50%; background:#93a4bb; }
  .cm-dot.ok { background:#20a383; box-shadow:0 0 0 3px #d7f3eb; }
  .cm-dot.demo { background:#e6a146; box-shadow:0 0 0 3px #fff0d9; }
  .cm-section { display:flex; align-items:end; justify-content:space-between; gap:1rem; margin:1.5rem 0 .75rem; }
  .cm-section h2 { font-size:1.25rem; margin:0; }
  .cm-section p { color:var(--muted); margin:.2rem 0 0; font-size:.86rem; }
  [data-testid="stMetric"] { background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:1rem 1.05rem; box-shadow:0 5px 20px rgba(34,62,100,.05); }
  [data-testid="stMetricLabel"] { color:var(--muted); }
  [data-testid="stMetricValue"] { color:var(--navy); font-weight:750; }
  [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:16px; overflow:hidden; }
  [data-testid="stTabs"] [data-baseweb="tab-list"] { gap:.45rem; border-bottom:1px solid var(--line); }
  [data-testid="stTabs"] button { border-radius:10px 10px 0 0; padding:.65rem 1rem; }
  .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button { border-radius:11px; font-weight:700; min-height:2.65rem; }
  .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] { background:linear-gradient(135deg,#245fd4,#347ae8); border:0; box-shadow:0 7px 18px rgba(41,99,216,.22); }
  [data-testid="stExpander"] { background:#fff; border:1px solid var(--line); border-radius:14px; }
  .cm-callout { padding:1rem 1.1rem; border:1px solid var(--line); border-left:4px solid var(--blue); border-radius:12px; background:#fff; color:#46556d; line-height:1.55; }
  .cm-score { display:inline-flex; align-items:center; justify-content:center; min-width:52px; padding:.3rem .6rem; border-radius:999px; color:#fff; background:var(--blue); font-weight:800; }
  .cm-empty { text-align:center; padding:3.3rem 1rem; border:1px dashed #bdcadc; border-radius:20px; background:#fff; }
  .cm-empty-icon { font-size:2rem; margin-bottom:.5rem; }
  .cm-empty h3 { margin:.2rem 0; }
  .cm-empty p { color:var(--muted); max-width:560px; margin:.4rem auto 0; }
  @media (max-width: 700px) {
    .block-container { padding:1rem .8rem 3rem; }
    .cm-hero { padding:1.25rem; border-radius:16px; }
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
          <div><div class="cm-brand-title">Cap Marchés</div>
          <div class="cm-brand-sub">Intelligence commerciale publique</div></div>
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


def hero(title: str, subtitle: str, eyebrow: str, pills: list[tuple[str, str]] | None = None) -> None:
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
          <p>{escape(subtitle)}</p>
          {rendered}
        </section>
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
