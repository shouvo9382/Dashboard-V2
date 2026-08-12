"""
Bangladesh Sports Ministry — National Athlete Performance Dashboard
===================================================================
A demonstration SaaS dashboard for a national sports ministry, built with
Streamlit + Plotly. It reads the athlete workbook directly (read-only), cleans
the human-formatted fields, and provides:

  • Executive Summary with headline KPIs and portfolio-level charts
  • Player Profile cards with cascading Sport -> Player filters
  • Performance & Fitness analytics
  • Injury & Training insights, plus Intake-vs-Burn calorie analysis
  • A configurable, within-sport ranking system + live leaderboard

Run locally:
    pip install -r requirements.txt
    streamlit run app.py

All scoring/parsing logic lives in scoring.py (documented there). Weights are
adjustable from the sidebar and default to the values in scoring.DEFAULT_WEIGHTS.
"""

from __future__ import annotations

from pathlib import Path

import base64

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as _pio

# Global chart theme so every Plotly figure matches the enterprise design
# (transparent card background, Inter font, clean grid) without per-chart edits.
_pio.templates["gov"] = go.layout.Template(
    layout=dict(
        font=dict(family="Inter, sans-serif", color="#12283A", size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=["#0B4F8A", "#1B8A4C", "#1667a8", "#2ea966", "#5aa9d6",
                  "#F2C14E", "#7cc79a", "#8a6d3b"],
        xaxis=dict(gridcolor="#eef3f8", zerolinecolor="#e7edf4"),
        yaxis=dict(gridcolor="#eef3f8", zerolinecolor="#e7edf4"),
        legend=dict(font=dict(size=11)),
        margin=dict(l=6, r=6, t=10, b=6),
    )
)
_pio.templates.default = "plotly+gov"
import streamlit as st

import scoring
import i18n
from i18n import t, gt, ts, is_bangla, LANG_KEY

# --------------------------------------------------------------------------- #
#  CONSTANTS + THEME                                                           #
# --------------------------------------------------------------------------- #
APP_DIR = Path(__file__).parent
DATA_PATH = APP_DIR / "data" / "Dashboard_Data.xlsx"
EMBLEM_PATH = APP_DIR / "assets" / "emblem.svg"

NAVY = "#0B4F8A"
NAVY_DARK = "#083b68"
GREEN = "#1B8A4C"
GREEN_LIGHT = "#2ea966"
GOLD = "#F2C14E"
INK = "#12283A"
MUTED = "#5a6b7b"
BG_SOFT = "#F1F6FB"

# Ordered categorical palette used across charts (blue -> green government feel).
SEQ = [NAVY, "#1667a8", GREEN, GREEN_LIGHT, "#5aa9d6", "#7cc79a", GOLD, "#8a6d3b"]

STATUS_COLORS = {
    "Fully Fit": GREEN,
    "Cleared / Recovered": "#5aa9d6",
    "Actively Managed": GOLD,
    "Monitored / Restricted": "#c0563b",
}

st.set_page_config(
    page_title="BD Sports Ministry — Athlete Dashboard",
    page_icon="🇧🇩",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800;900&display=swap');

:root {{
  --navy:{NAVY}; --navy2:{NAVY_DARK}; --green:{GREEN}; --green2:{GREEN_LIGHT};
  --gold:{GOLD}; --ink:{INK}; --muted:{MUTED};
  --bg:#eef2f7; --panel:#ffffff; --line:#e7edf4; --line2:#eef3f8;
  --shadow:0 1px 3px rgba(16,32,52,.04), 0 8px 24px rgba(16,32,52,.06);
  --shadow-lg:0 12px 40px rgba(16,32,52,.12);
  --radius:18px;
}}

/* ---------- Global reset of Streamlit chrome (minimal, safe subset only) ----------
   We ONLY hide elements that are never structurally load-bearing for the
   sidebar: the hamburger menu and the footer. We deliberately do NOT hide
   header[data-testid="stHeader"], stToolbar, or stDecoration — the sidebar's
   show/hide arrow ([data-testid="collapsedControl"]) lives inside that header,
   and display:none on an ancestor removes descendants from rendering with no
   way to override from a child rule. Hiding the header fully means that once
   a user collapses the sidebar, there is no way to bring it back. ---- */
#MainMenu, footer {{ display:none !important; }}
.stApp {{ background:
  radial-gradient(1200px 600px at 100% -5%, #e3edf9 0%, transparent 55%),
  radial-gradient(900px 500px at -10% 10%, #e8f5ee 0%, transparent 45%),
  var(--bg); }}
html, body, [class*="css"], .stMarkdown, p, span, div, label, input, button, td, th {{
  font-family:'Inter','Plus Jakarta Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
}}
h1,h2,h3,h4,.pname,.gv,.kpi .value {{ font-family:'Plus Jakarta Sans','Inter',sans-serif; }}
.block-container {{ padding:1.4rem 2rem 3rem; max-width:1560px; }}
.main .block-container {{ animation:fadeUp .45s ease both; }}
@keyframes fadeUp {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:none; }} }}
@keyframes popIn {{ from {{ opacity:0; transform:scale(.97); }} to {{ opacity:1; transform:none; }} }}

/* ---------- Sidebar as a dark enterprise rail ---------- */
[data-testid="stSidebar"] {{
  background:linear-gradient(185deg, #08243f 0%, #0b2f52 55%, #0a3b46 130%);
  border-right:1px solid rgba(255,255,255,.06); width:290px !important;
}}
[data-testid="stSidebar"] > div {{ padding-top:.4rem; }}
[data-testid="stSidebar"] * {{ color:#dbe7f2; }}
[data-testid="stSidebar"] .brand {{
  display:flex; align-items:center; gap:12px; padding:6px 10px 2px; }}
[data-testid="stSidebar"] .brand .bt {{ font-family:'Plus Jakarta Sans';
  font-weight:800; font-size:1.02rem; color:#fff; line-height:1.15; letter-spacing:-.01em; }}
[data-testid="stSidebar"] .brand .bs {{ font-size:.72rem; color:#8fb0cc; letter-spacing:.02em; }}
[data-testid="stSidebar"] hr {{ border-color:rgba(255,255,255,.08); margin:.7rem 0; }}
[data-testid="stSidebar"] .navlabel {{ font-size:.68rem; font-weight:700; letter-spacing:.14em;
  text-transform:uppercase; color:#6d90b0; padding:6px 12px 2px; }}

/* Radio -> nav items */
[data-testid="stSidebar"] [role="radiogroup"] {{ gap:3px; display:flex; flex-direction:column; }}
[data-testid="stSidebar"] [role="radiogroup"] label {{
  padding:9px 13px; border-radius:11px; font-weight:600; font-size:.9rem;
  color:#c4d6e8 !important; transition:all .16s ease; cursor:pointer;
  border:1px solid transparent; }}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
  background:rgba(255,255,255,.06); color:#fff !important; }}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
  background:linear-gradient(100deg, rgba(46,169,102,.28), rgba(11,79,138,.30));
  border-color:rgba(120,199,154,.5); color:#fff !important;
  box-shadow:inset 3px 0 0 var(--green); }}
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {{ display:none; }}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {{ color:#8fb0cc !important; }}

/* ==========================================================================
   UNIVERSAL RULE (sidebar AND main area, every page):
     Any control with a light/white box (text input, selectbox, multiselect,
     dropdown popover) -> WHITE background + BLACK text.
     Any element with an intentionally dark/coloured background (nav rail,
     selected-tag chips, the masthead) -> keeps LIGHT text.
   This one rule replaces all the earlier per-widget guesses, so a box's
   background and its text colour can never end up mismatched again. ---- */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-testid="stMultiSelect"] > div > div {{
  background:#ffffff !important;
  border:1px solid rgba(255,255,255,.35) !important; border-radius:10px !important; }}
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-testid="stSelectbox"] *,
[data-testid="stSidebar"] [data-testid="stMultiSelect"] * {{
  color:{INK} !important; -webkit-text-fill-color:{INK} !important; fill:{INK} !important; }}
[data-testid="stSidebar"] input::placeholder {{
  color:{MUTED} !important; -webkit-text-fill-color:{MUTED} !important; opacity:1 !important; }}

/* The FIELD NAME/LABEL above each control ("Sport", "Player", "Division", ...)
   sits directly on the dark sidebar, NOT inside the white input box — so it
   must stay light. It is nested inside the same wrapper as the control, so
   the wildcard rule above would otherwise also darken it; this more specific
   rule (extra data-testid segment) wins over that wildcard and restores it. */
[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] *,
[data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-testid="stWidgetLabel"] *,
[data-testid="stSidebar"] [data-testid="stTextInput"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] [data-testid="stTextInput"] [data-testid="stWidgetLabel"] * {{
  color:#c9dced !important; -webkit-text-fill-color:#c9dced !important; }}

/* Selected multiselect tags (chips): these ARE a deliberate colour background,
   so they correctly keep white text/icon — the one intentional exception. */
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
  background:linear-gradient(100deg,{NAVY},{GREEN}) !important; border:none !important; }}
[data-testid="stMultiSelect"] span[data-baseweb="tag"] * {{
  color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; fill:#ffffff !important; }}

/* Dropdown option lists (render in a portal, outside sidebar/main containers) */
div[data-baseweb="popover"] {{
  background:#ffffff !important; border-radius:12px !important; box-shadow:var(--shadow-lg) !important; }}
div[data-baseweb="popover"] * {{ color:{INK} !important; -webkit-text-fill-color:{INK} !important; }}

/* Same universal rule for the MAIN content area (Coach Directory search,
   News Center filters, Rankings selects, etc.) — belt-and-braces in case any
   global light-text rule elsewhere ever leaks in. */
.main input, .main textarea,
.main [data-testid="stSelectbox"] > div > div,
.main [data-testid="stMultiSelect"] > div > div {{
  background:#ffffff !important; }}
.main input, .main textarea,
.main [data-testid="stSelectbox"] *,
.main [data-testid="stMultiSelect"] * {{
  color:{INK} !important; -webkit-text-fill-color:{INK} !important; }}
.main [data-testid="stMultiSelect"] span[data-baseweb="tag"] * {{
  color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; }}

[data-testid="stSidebar"] [data-testid="stExpander"] {{
  background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.09);
  border-radius:12px; }}


/* ---------- Topbar / masthead ---------- */
.gov-header {{
  position:relative; overflow:hidden; aspect-ratio:3/1; min-height:220px;
  background:linear-gradient(115deg, var(--navy) 0%, var(--navy2) 50%, #0a3b46 120%);
  border-radius:22px; margin:0 0 22px; color:#fff;
  display:grid; /* every direct child stacks in the same single cell below */
  box-shadow:0 18px 50px rgba(11,79,138,.30); border:1px solid rgba(255,255,255,.10);
  animation:popIn .5s ease both; }}
/* CSS Grid single-cell stacking: every direct child of .gov-header occupies
   the SAME grid cell (the full header), layered by plain DOM order -- later
   children paint on top of earlier ones automatically. This replaces a
   fragile chain of position:absolute + inset:0 + z-index overrides that kept
   breaking as new elements (the carousel) were added: each fix required
   guessing which OTHER rule might still be silently overriding it. Grid
   stacking has no such ambiguity -- there is nothing to override, and every
   child automatically stretches to fill the cell with no inset arithmetic. */
.gov-header > * {{ grid-area:1/1; min-width:0; min-height:0; }}
.gov-header::before {{ content:""; position:absolute; inset:0; z-index:1;
  background:radial-gradient(500px 180px at 88% -10%, rgba(46,169,102,.4), transparent 70%); }}
.gov-header::after {{ content:""; position:absolute; right:26px; top:0; bottom:0; width:1px;
  z-index:1; background:linear-gradient(180deg,transparent,rgba(255,255,255,.15),transparent); }}
.gov-header h1 {{ font-size:1.6rem; margin:0; line-height:1.1; color:#fff;
  font-weight:800; letter-spacing:-.02em; }}
.gov-header .sub {{ opacity:.9; font-size:.9rem; margin-top:5px; font-weight:500; }}
.gov-header .flag {{ height:5px; width:88px; border-radius:4px; margin-top:11px;
  background:linear-gradient(90deg,var(--green) 0 72%, var(--gold) 72% 100%);
  box-shadow:0 2px 10px rgba(242,193,78,.5); }}
/* The icon+text row: the LAST child in DOM order, so it paints above both the
   carousel and the decorative pseudo-highlights (z-index:1) without needing
   its own z-index at all under grid stacking -- but we set one explicitly
   anyway as a second, independent guarantee. */
.gh-row {{ position:relative; z-index:2; display:flex; align-items:center;
  gap:20px; padding:22px 30px; height:100%; }}
.topstat {{ margin-left:auto; display:flex; gap:26px; }}
.topstat .ts {{ text-align:right; }}
.topstat .tv {{ font-family:'Plus Jakarta Sans'; font-weight:800; font-size:1.35rem; color:#fff; }}
.topstat .tl {{ font-size:.68rem; color:#a9c6e0; text-transform:uppercase; letter-spacing:.08em; }}

/* ---------- Masthead photo carousel (behind the text, above the gradient) --
   Each photo shows for a clean 3-second window, then crossfades to the next,
   looping forever over a 9-second cycle. A dark scrim sits on top so header
   text stays legible no matter what the photos look like. Renders nothing
   (no layout change) until assets/masthead1.jpg etc. actually exist. Fills
   its grid cell automatically -- no position/inset needed. ---- */
.mh-carousel {{ position:relative; width:100%; height:100%; overflow:hidden; }}
.mh-photo {{ position:absolute; inset:0; width:100%; height:100%;
  object-fit:fill; opacity:0; }}
.mh-photo1 {{ animation:mhFade1 9s ease-in-out infinite; }}
.mh-photo2 {{ animation:mhFade2 9s ease-in-out infinite; }}
.mh-photo3 {{ animation:mhFade3 9s ease-in-out infinite; }}
@keyframes mhFade1 {{
  0% {{ opacity:0; }} 2% {{ opacity:.85; }} 30% {{ opacity:.85; }}
  36% {{ opacity:0; }} 100% {{ opacity:0; }} }}
@keyframes mhFade2 {{
  0% {{ opacity:0; }} 33% {{ opacity:0; }} 36% {{ opacity:.85; }}
  63% {{ opacity:.85; }} 69% {{ opacity:0; }} 100% {{ opacity:0; }} }}
@keyframes mhFade3 {{
  0% {{ opacity:0; }} 66% {{ opacity:0; }} 69% {{ opacity:.85; }}
  97% {{ opacity:.85; }} 100% {{ opacity:0; }} }}
/* Darken ONLY a narrow band directly behind the title text -- the photo
   should read as covering the whole banner, so the wash fades out fast
   (fully clear by ~38% width) instead of dimming a big chunk of it. */
.mh-scrim {{ position:absolute; inset:0;
  background:linear-gradient(100deg, rgba(10,35,52,.42) 0%, rgba(10,35,52,.24) 14%,
             rgba(10,35,52,.08) 26%, rgba(10,35,52,0) 38%); }}

/* ---------- KPI tiles ---------- */
.kpi {{
  position:relative; background:var(--panel); border:1px solid var(--line);
  border-radius:16px; padding:17px 19px; height:100%; box-shadow:var(--shadow);
  transition:transform .2s cubic-bezier(.2,.7,.3,1), box-shadow .2s ease; overflow:hidden;
  animation:popIn .4s ease both; }}
.kpi::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:4px;
  background:linear-gradient(180deg,var(--navy),var(--navy2)); border-radius:4px 0 0 4px; }}
.kpi.green::before {{ background:linear-gradient(180deg,var(--green2),var(--green)); }}
.kpi.gold::before  {{ background:linear-gradient(180deg,var(--gold),#d9a53a); }}
.kpi:hover {{ transform:translateY(-4px); box-shadow:var(--shadow-lg); }}
.kpi .label {{ color:var(--muted); font-size:.72rem; text-transform:uppercase;
  letter-spacing:.07em; font-weight:700; }}
.kpi .value {{ color:var(--ink); font-size:1.85rem; font-weight:800; line-height:1.04;
  letter-spacing:-.02em; margin-top:3px; }}
.kpi .foot {{ color:var(--muted); font-size:.76rem; margin-top:3px; font-weight:500; }}

/* ---------- Big glance tiles ---------- */
.glance {{ position:relative; border-radius:20px; padding:24px; color:#fff; overflow:hidden;
  box-shadow:var(--shadow-lg); transition:transform .22s cubic-bezier(.2,.7,.3,1), box-shadow .22s;
  min-height:150px; display:flex; flex-direction:column; justify-content:space-between;
  animation:popIn .5s ease both; }}
.glance:hover {{ transform:translateY(-6px) scale(1.01); }}
.glance .gv {{ font-family:'Plus Jakarta Sans'; font-size:2.5rem; font-weight:800; line-height:1;
  letter-spacing:-.03em; }}
.glance .gl {{ font-size:.86rem; font-weight:600; opacity:.96; margin-top:8px;
  text-transform:uppercase; letter-spacing:.05em; }}
.glance .gi {{ font-size:1.9rem; opacity:.92; }}
.glance::after {{ content:""; position:absolute; right:-34px; bottom:-34px; width:140px; height:140px;
  border-radius:50%; background:rgba(255,255,255,.10); }}
.glance::before {{ content:""; position:absolute; left:-20px; top:-30px; width:90px; height:90px;
  border-radius:50%; background:rgba(255,255,255,.07); }}

/* ---------- Panels / cards ---------- */
.profile {{ background:var(--panel); border:1px solid var(--line); border-radius:var(--radius);
  padding:22px 24px; box-shadow:var(--shadow); transition:box-shadow .2s ease, transform .2s ease;
  animation:popIn .4s ease both; }}
.profile:hover {{ box-shadow:var(--shadow-lg); }}
.profile .avatar {{ width:78px; height:78px; border-radius:22px;
  background:linear-gradient(135deg,var(--navy),var(--green)); color:#fff;
  display:flex; align-items:center; justify-content:center; font-family:'Plus Jakarta Sans';
  font-size:1.7rem; font-weight:800; flex-shrink:0; box-shadow:0 8px 20px rgba(11,79,138,.32); }}
.profile .pname {{ font-size:1.45rem; font-weight:800; color:var(--ink); line-height:1.08;
  letter-spacing:-.02em; }}
.profile .prole {{ color:var(--muted); font-size:.94rem; font-weight:500; }}
.chip {{ display:inline-block; padding:4px 13px; border-radius:999px; font-size:.75rem;
  font-weight:700; margin:4px 6px 0 0; letter-spacing:.01em; }}
.chip.navy {{ background:#eef4fb; color:var(--navy); border:1px solid #d3e3f2; }}
.chip.green{{ background:#e8f7ee; color:var(--green); border:1px solid #c1e8cf; }}
.chip.gold {{ background:#fdf4dc; color:#8a6d1e; border:1px solid #f0dfa4; }}

/* ---------- Rank badge ---------- */
.rankbadge {{ background:linear-gradient(135deg,var(--navy),var(--green)); color:#fff;
  border-radius:18px; padding:17px 20px; text-align:center; box-shadow:0 10px 26px rgba(11,79,138,.28);
  transition:transform .2s ease; }}
.rankbadge:hover {{ transform:translateY(-3px); }}
.rankbadge .r {{ font-family:'Plus Jakarta Sans'; font-size:2.3rem; font-weight:800; line-height:1;
  letter-spacing:-.02em; }}
.rankbadge .l {{ font-size:.74rem; opacity:.93; text-transform:uppercase; letter-spacing:.06em; }}

.metric-row {{ display:flex; justify-content:space-between; padding:9px 0;
  border-bottom:1px solid var(--line2); font-size:.92rem; }}
.metric-row:last-child {{ border-bottom:none; }}
.metric-row .k {{ color:var(--muted); font-weight:500; }}
.metric-row .v {{ color:var(--ink); font-weight:700; }}

.section-title {{ color:var(--ink); font-weight:800; font-size:1.12rem; padding:2px 0 2px 13px;
  margin:14px 0 13px; letter-spacing:-.01em; position:relative; }}
.section-title::before {{ content:""; position:absolute; left:0; top:3px; bottom:3px; width:4px;
  border-radius:3px; background:linear-gradient(180deg,var(--green),var(--navy)); }}

/* ---------- Streamlit widgets restyle ---------- */
.stButton>button, .stDownloadButton>button, .stLinkButton>a {{
  border-radius:11px !important; font-weight:700 !important; border:1px solid var(--line) !important;
  box-shadow:var(--shadow); transition:transform .14s ease, box-shadow .14s ease;
  background:var(--panel) !important; color:var(--navy) !important; }}
.stButton>button:hover, .stDownloadButton>button:hover, .stLinkButton>a:hover {{
  transform:translateY(-2px); box-shadow:var(--shadow-lg); border-color:#cddcec !important; }}
[data-testid="stMetric"] {{ background:var(--panel); border:1px solid var(--line);
  border-radius:14px; padding:14px 16px; box-shadow:var(--shadow); }}

/* Tabs -> pill segmented control */
.stTabs [data-baseweb="tab-list"] {{ gap:6px; background:transparent; border-bottom:none;
  flex-wrap:wrap; }}
.stTabs [data-baseweb="tab"] {{ background:var(--panel); border:1px solid var(--line);
  border-radius:11px; padding:8px 15px; font-weight:600; font-size:.86rem; color:var(--muted);
  transition:all .15s ease; }}
.stTabs [data-baseweb="tab"]:hover {{ color:var(--navy); border-color:#cddcec; }}
.stTabs [aria-selected="true"] {{ background:linear-gradient(100deg,var(--navy),var(--green)) !important;
  color:#fff !important; border-color:transparent !important; box-shadow:0 6px 16px rgba(11,79,138,.25); }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}

/* Dataframe / tables */
[data-testid="stDataFrame"] {{ border:1px solid var(--line); border-radius:14px; overflow:hidden;
  box-shadow:var(--shadow); }}
[data-testid="stDataFrame"] thead tr th {{ background:#f3f7fb !important; color:var(--ink) !important;
  font-weight:700 !important; text-transform:uppercase; font-size:.72rem; letter-spacing:.04em; }}

/* Expander */
[data-testid="stExpander"] {{ border:1px solid var(--line) !important; border-radius:14px !important;
  box-shadow:var(--shadow); background:var(--panel); }}
[data-testid="stExpander"] summary {{ font-weight:700; }}

/* Alerts */
[data-testid="stAlert"] {{ border-radius:14px; border:1px solid var(--line); box-shadow:var(--shadow); }}

/* Plotly containers get a card frame */
[data-testid="stPlotlyChart"] {{ background:var(--panel); border:1px solid var(--line);
  border-radius:16px; padding:8px; box-shadow:var(--shadow); }}

/* Selectbox / inputs on main area */
.main div[data-baseweb="select"] > div {{ border-radius:11px; border-color:var(--line); }}
.main .stTextInput input {{ border-radius:11px; }}

hr {{ border-color:var(--line); margin:1rem 0; }}
::-webkit-scrollbar {{ width:10px; height:10px; }}
::-webkit-scrollbar-thumb {{ background:#c4d3e2; border-radius:8px; }}
::-webkit-scrollbar-thumb:hover {{ background:#a9bccf; }}

@media (max-width:1000px) {{
  .gov-header h1 {{ font-size:1.25rem; }} .topstat {{ display:none; }}
  .glance .gv {{ font-size:2rem; }} .kpi .value {{ font-size:1.5rem; }}
  .block-container {{ padding:1rem 1rem 2rem; }}
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(f"<style>{i18n.BANGLA_FONT_CSS}</style>", unsafe_allow_html=True)


def _bd_flag_svg(size: str = "2.3rem") -> str:
    """A clean, proportionally-correct Bangladesh flag as inline SVG (no
    external image dependency — reliable regardless of network/hotlinking).
    Real flag proportions: 10:6 field, red disc diameter = 2/5 height,
    centered vertically, offset slightly toward the hoist (left) side.
    `size` sets the rendered height; width follows the 10:6 ratio."""
    return (
        f"<svg viewBox='0 0 100 60' xmlns='http://www.w3.org/2000/svg' "
        f"style='height:{size};width:auto;display:block;border-radius:3px;"
        f"box-shadow:0 2px 6px rgba(0,0,0,.25)'>"
        f"<rect width='100' height='60' fill='#006A4E'/>"
        f"<circle cx='45' cy='30' r='20' fill='#F42A41'/>"
        f"</svg>"
    )


# Masthead background carousel — reads up to 3 local photos, if present.
# Expected files (add these yourself; none are required for the app to run):
#   assets/masthead1.jpg, assets/masthead2.jpg, assets/masthead3.jpg
# Until those files exist, the header simply shows its plain gradient
# background — there is no error, no missing-image icon, no regression.
MASTHEAD_IMG_PATHS = [APP_DIR / "assets" / f"masthead{i}.jpg" for i in (1, 2, 3)]


@st.cache_data(show_spinner=False)
def _masthead_images_b64() -> list[str]:
    """Base64-encode whichever masthead photos exist (skips missing ones)."""
    out = []
    for p in MASTHEAD_IMG_PATHS:
        if p.exists():
            out.append(base64.b64encode(p.read_bytes()).decode())
    return out


def _masthead_carousel_html(opacity: float = 0.55) -> str:
    """Absolutely-positioned, auto-rotating background layer for the header:
    each photo shows for a clean 3-second window (9s total for 3 images),
    then crossfades to the next, looping forever. A translucent navy scrim
    sits above the photos so header text stays legible regardless of what
    the photos look like. Returns "" (nothing) if no photos are present yet."""
    imgs = _masthead_images_b64()
    if not imgs:
        return ""
    layers = "".join(
        f"<img src='data:image/jpeg;base64,{b64}' class='mh-photo mh-photo{i+1}'/>"
        for i, b64 in enumerate(imgs)
    )
    return (
        f"<div class='mh-carousel'>{layers}"
        f"<div class='mh-scrim'></div></div>"
    )


# --------------------------------------------------------------------------- #
#  ACCESS GATE                                                                 #
# --------------------------------------------------------------------------- #
# Protects the dashboard when it is hosted on the public internet (e.g.
# Streamlit Community Cloud), because it displays named athletes with health
# and injury data. The password is read from Streamlit "secrets":
#
#   • Locally  -> .streamlit/secrets.toml  (never commit this file)
#   • On Cloud -> the app's Settings ▸ Secrets panel
#
# If NO password is configured at all, the gate stays OPEN so local
# development and the run_dashboard.bat launcher keep working unchanged.
def _check_access() -> bool:
    try:
        expected = st.secrets.get("app_password", None)
    except Exception:
        expected = None  # no secrets file present -> gate disabled

    if not expected:
        return True  # no password set -> open (local/offline use)

    if st.session_state.get("_authed", False):
        return True

    st.markdown(
        f"<div class='gov-header'><div class='gh-row'>{_bd_flag_svg('2.4rem')}"
        "<div><h1>National Athlete Performance Dashboard</h1>"
        "<div class='sub'>Ministry of Youth &amp; Sports · Bangladesh</div>"
        "<div class='flag'></div></div></div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("#### 🔒 Restricted access")
    st.caption("This portal contains athlete health information. "
               "Please enter the access code provided to you.")
    entered = st.text_input("Access code", type="password",
                            label_visibility="collapsed",
                            placeholder="Access code")
    if entered:
        if entered == expected:
            st.session_state["_authed"] = True
            st.rerun()
        else:
            st.error("Incorrect access code. Please try again.")
    st.stop()  # halt the script here until authenticated


_check_access()


# --------------------------------------------------------------------------- #
#  DATA (cached)                                                               #
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def get_clean_data(path_str: str) -> pd.DataFrame:
    return scoring.load_data(path_str)


@st.cache_data(show_spinner=False)
def get_scored_data(path_str: str, weights_items: tuple,
                    fweights_items: tuple, ideal_ratio: float) -> pd.DataFrame:
    base = get_clean_data(path_str)
    return scoring.compute_scores(
        base,
        weights=dict(weights_items),
        fitness_weights=dict(fweights_items),
        ideal_ratio=ideal_ratio,
    )


@st.cache_data(show_spinner=False)
def get_coaches(path_str: str) -> pd.DataFrame:
    import dataset
    sports = sorted(get_clean_data(path_str)["Sport"].dropna().unique().tolist())
    return dataset.load_coaches(sports)


def _stt(english_text: str) -> str:
    """Section-title translation helper: returns the Bangla version of a known
    section heading when in Bangla mode, else the original English unchanged."""
    return i18n.SECTION_TITLES_BN.get(english_text, english_text) if is_bangla() else english_text


def kpi(col, label, value, foot="", cls=""):
    col.markdown(
        f"<div class='kpi {cls}'><div class='label'>{label}</div>"
        f"<div class='value'>{value}</div><div class='foot'>{foot}</div></div>",
        unsafe_allow_html=True,
    )


def initials(name: str) -> str:
    parts = [p for p in str(name).split() if p]
    if not parts:
        return "?"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


# --------------------------------------------------------------------------- #
#  SIDEBAR — branding, navigation, cascading filters, weights                 #
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.session_state.setdefault(LANG_KEY, "en")
    lang_pick = st.radio(t("language_label"), ["English", "বাংলা"],
                        index=(0 if st.session_state[LANG_KEY] == "en" else 1),
                        horizontal=True, key="lang_radio", label_visibility="visible")
    st.session_state[LANG_KEY] = "bn" if lang_pick == "বাংলা" else "en"
    st.markdown("<hr style='margin:6px 0'>", unsafe_allow_html=True)

    st.markdown(
        "<div class='brand'>"
        "<div style='width:44px;height:44px;border-radius:13px;flex-shrink:0;"
        "background:linear-gradient(135deg,#1b8a4c,#0b4f8a);display:flex;"
        "align-items:center;justify-content:center;"
        f"box-shadow:0 6px 16px rgba(0,0,0,.3)'>{_bd_flag_svg('1.35rem')}</div>"
        f"<div><div class='bt'>{t('brand_title')}</div>"
        f"<div class='bs'>{t('brand_sub')}</div></div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='navlabel'>{t('nav_label')}</div>", unsafe_allow_html=True)

    _nav_keys = ["nav_glance", "nav_notunkuri", "nav_stipend", "nav_summary",
                "nav_profile", "nav_fitness", "nav_injury", "nav_rankings",
                "nav_coaches", "nav_rules", "nav_news"]
    _nav_en = ["At a Glance", "Notun Kuri", "Stipend Program", "Executive Summary",
              "Player Profile", "Performance & Fitness", "Injury & Training",
              "Rankings & Leaderboard", "Coach Directory", "Rule Book", "News Center"]
    _nav_display = [t(k) for k in _nav_keys]
    _nav_display_to_en = dict(zip(_nav_display, _nav_en))

    page_display = st.radio(
        "Navigate", _nav_display, label_visibility="collapsed", key="nav_radio",
    )
    page = _nav_display_to_en[page_display]  # internal routing stays on English keys
    st.markdown(f"<div class='navlabel'>{t('filters_label')}</div>", unsafe_allow_html=True)

    # --- Cascading filters: Sport -> (advanced) -> Player -------------------
    clean = get_clean_data(str(DATA_PATH))
    sports = sorted(clean["Sport"].dropna().unique().tolist())
    sport_choice = st.selectbox(t("filter_sport"), [t("filter_all_sports")] + sports, index=0)
    if sport_choice == t("filter_all_sports"):
        sport_choice = "All Sports"  # normalise back to the internal sentinel

    pool = clean if sport_choice == "All Sports" else clean[clean["Sport"] == sport_choice]

    # Handle a pending "clear filters" before the widgets are built.
    _filter_keys = ["f_search", "f_div", "f_dist", "f_gender", "f_avail",
                    "f_club", "f_nat", "f_age", "f_perf", "f_fit", "f_career"]
    if st.session_state.pop("_clear_filters", False):
        for k in _filter_keys:
            st.session_state.pop(k, None)

    # Smart search across name / club / district / event.
    search = st.text_input(t("filter_search"),
                           placeholder=t("filter_search_placeholder"), key="f_search")

    with st.expander(t("filter_advanced"), expanded=False):
        div_sel = st.multiselect(t("filter_division"), sorted(clean["division"].dropna().unique()), key="f_div")
        dist_sel = st.multiselect(t("filter_district"), sorted(pool["district"].dropna().unique()), key="f_dist")
        gender_sel = st.multiselect(t("filter_gender"), sorted(clean["gender"].dropna().unique()), key="f_gender")
        avail_sel = st.multiselect(t("filter_availability"), sorted(clean["injury_status"].dropna().unique()), key="f_avail")
        club_sel = st.multiselect(t("filter_club"), sorted(clean["club"].dropna().unique()), key="f_club")
        nat_sel = st.multiselect(t("filter_national_team"), sorted(clean["national_team"].dropna().unique()), key="f_nat")
        a_lo, a_hi = int(clean["age"].min()), int(clean["age"].max())
        age_rng = st.slider(t("filter_age"), a_lo, a_hi, (a_lo, a_hi), key="f_age")
        perf_rng = st.slider(t("filter_performance"), 0, 100, (0, 100), 5, key="f_perf")
        fit_rng = st.slider(t("filter_fitness"), 0, 100, (0, 100), 5, key="f_fit")
        career_rng = st.slider(t("filter_career_win"), 0, 100, (0, 100), 5, key="f_career")
        st.button(t("filter_clear"),
                  on_click=lambda: st.session_state.update(_clear_filters=True))

    # Build a combined mask on the sport-scoped pool.
    import numpy as _np
    mask = pd.Series(True, index=pool.index)
    if search:
        s = search.strip().lower()
        hay = (pool["Name"].fillna("") + " " + pool["club"].fillna("") + " "
               + pool["district"].fillna("") + " " + pool["Position/Event"].fillna("")
               ).str.lower()
        mask &= hay.str.contains(s, regex=False)
    if div_sel:
        mask &= pool["division"].isin(div_sel)
    if dist_sel:
        mask &= pool["district"].isin(dist_sel)
    if gender_sel:
        mask &= pool["gender"].isin(gender_sel)
    if avail_sel:
        mask &= pool["injury_status"].isin(avail_sel)
    if club_sel:
        mask &= pool["club"].isin(club_sel)
    if nat_sel:
        mask &= pool["national_team"].isin(nat_sel)
    mask &= pool["age"].between(age_rng[0], age_rng[1])
    mask &= pd.to_numeric(pool["performance_rating"], errors="coerce").between(*perf_rng)
    mask &= pd.to_numeric(pool["fitness_rating"], errors="coerce").between(*fit_rng)
    mask &= pd.to_numeric(pool["career_win_pct"], errors="coerce").between(*career_rng)

    filtered = pool[mask].sort_values("Name")
    filter_ids = set(filtered["ID"])

    player_names = filtered["Name"].tolist()
    if player_names:
        player_choice = st.selectbox(t("filter_player"), player_names, index=0)
    else:
        st.selectbox(t("filter_player"),
                    ["(কোনো অ্যাথলিট মেলেনি)" if is_bangla() else "(no athletes match filters)"],
                    index=0)
        player_choice = None

    st.caption(
        t("filter_scope_caption", n=len(filtered), total=len(pool))
        + ("" if sport_choice == "All Sports" else f" · {sport_choice}")
    )
    st.divider()

    # --- Weight controls (drive the ranking model live) ---
    # Driven by scoring.MODEL_COMPONENTS so the 6-component model lives in one place.
    _comp_labels = {
        "fitness": "Fitness (VO₂ / HR / body-fat)",
        "career": "Career performance",
        "nutrition": "Nutrition (fuelling)",
        "attendance": "Training attendance",
        "medical": "Medical / availability",
        "coach": "Coach evaluation",
    }
    _slider_keys = {wkey: f"w_{wkey}" for _, wkey, _ in scoring.MODEL_COMPONENTS}
    for wkey, skey in _slider_keys.items():
        st.session_state.setdefault(skey, scoring.DEFAULT_WEIGHTS[wkey])
    if st.session_state.pop("_reset_weights", False):
        for wkey, skey in _slider_keys.items():
            st.session_state[skey] = scoring.DEFAULT_WEIGHTS[wkey]

    with st.expander("⚙️ Ranking model weights", expanded=False):
        st.caption("Adjust the emphasis of each component. "
                   "Values are auto-normalised to 100%.")
        for _, wkey, _ in scoring.MODEL_COMPONENTS:
            st.slider(_comp_labels[wkey], 0.0, 1.0, step=0.05, key=f"w_{wkey}")
        st.button("↺ Reset to defaults",
                  on_click=lambda: st.session_state.update(_reset_weights=True))

weights = {wkey: st.session_state[f"w_{wkey}"]
           for _, wkey, _ in scoring.MODEL_COMPONENTS}
norm_w = scoring._normalise_weights(weights)

df = get_scored_data(
    str(DATA_PATH),
    tuple(sorted(weights.items())),
    tuple(sorted(scoring.DEFAULT_FITNESS_WEIGHTS.items())),
    scoring.IDEAL_INTAKE_BURN_RATIO,
)

# Scope used by pages that respect the filters (sport + advanced).
scoped = df[df["ID"].isin(filter_ids)]


# --------------------------------------------------------------------------- #
#  HEADER BANNER                                                               #
# --------------------------------------------------------------------------- #
st.markdown(
    f"<div class='gov-header'>{_masthead_carousel_html()}"
    f"<div class='gh-row'>{_bd_flag_svg('2.3rem')}"
    "<div><h1>National Athlete Performance Platform</h1>"
    "<div class='sub'>Ministry of Youth &amp; Sports · Government of Bangladesh</div>"
    "<div class='flag'></div></div></div></div>",
    unsafe_allow_html=True,
)


# =========================================================================== #
#  PAGE 1 — EXECUTIVE SUMMARY                                                  #
# =========================================================================== #
def page_summary():
    import dataset as _ds
    coaches = get_coaches(str(DATA_PATH))
    nk = _ds.get_notun_kuri()

    st.markdown(f"<div class='section-title'>{t('page_summary_title')}</div>",
                unsafe_allow_html=True)
    st.caption(t('page_summary_sub'))

    # ---- Outcome KPIs spanning the entire platform ----
    injured = df["injury_status"].isin(["Actively Managed", "Monitored / Restricted"])
    c1, c2, c3, c4, c5 = st.columns(5)
    kpi(c1, t("kpi_grassroots"), f"{nk['totals']['registered']:,}",
        t("kpi_registered"))
    kpi(c2, t("kpi_elite"), f"{len(df):,}",
        f"{df['Sport'].nunique()} " + ("খেলা" if is_bangla() else "sports"), cls="green")
    kpi(c3, t("kpi_coaches"), f"{len(coaches):,}",
        "জাতীয় + বিভাগীয়" if is_bangla() else "national + divisional", cls="green")
    kpi(c4, t("kpi_avg_perf"), f"{df['overall_score'].mean():.0f}", t("kpi_model_score"), cls="gold")
    kpi(c5, t("kpi_match_ready"), f"{(~injured).mean()*100:.0f}%",
        f"{int(injured.sum())} " + t("kpi_on_watch"), cls="gold")

    st.write("")
    left, right = st.columns([1, 1])

    # ---- Talent pipeline funnel (ties grassroots to elite) ----
    with left:
        st.markdown(f"<div class='section-title'>{_stt('Talent pipeline — grassroots to elite')}</div>",
                    unsafe_allow_html=True)
        stages = nk["stages"][:4] + [("Elite athlete pool", len(df))]
        fig = go.Figure(go.Funnel(
            y=[s for s, _ in stages], x=[v for _, v in stages],
            textinfo="value", marker=dict(color=[NAVY, "#1667a8", GREEN, GREEN_LIGHT, GOLD]),
            connector=dict(line=dict(color="#cfe0ef"))))
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=6, b=0))
        st.plotly_chart(fig, width='stretch')

    # ---- Top performers nationwide (cross-sport) ----
    with right:
        st.markdown(f"<div class='section-title'>{_stt('Top performers nationwide')}</div>",
                    unsafe_allow_html=True)
        top = df.nlargest(8, "overall_score")[["Name", "Sport", "overall_score", "division"]]
        tfig = px.bar(top.sort_values("overall_score"), x="overall_score", y="Name",
                      orientation="h", color="overall_score",
                      color_continuous_scale=["#cfe0ef", GREEN_LIGHT, NAVY],
                      hover_data=["Sport", "division"], text="overall_score")
        tfig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        tfig.update_layout(height=340, margin=dict(l=0, r=10, t=6, b=0),
                           coloraxis_showscale=False, xaxis_title="Overall score",
                           yaxis_title="")
        st.plotly_chart(tfig, width='stretch')

    # ---- Coverage + readiness row ----
    l2, r2 = st.columns([1, 1])
    with l2:
        st.markdown(f"<div class='section-title'>{_stt('Elite athletes by sport')}</div>",
                    unsafe_allow_html=True)
        counts = df["Sport"].value_counts().rename_axis("Sport").reset_index(name="Athletes")
        fig = px.bar(counts, x="Athletes", y="Sport", orientation="h",
                     color="Sport", color_discrete_sequence=SEQ, text="Athletes")
        fig.update_layout(showlegend=False, height=360, margin=dict(l=0, r=10, t=6, b=0),
                          yaxis=dict(categoryorder="total ascending"))
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, width='stretch')
    with r2:
        st.markdown(f"<div class='section-title'>{_stt('Squad readiness')}</div>", unsafe_allow_html=True)
        status = df["injury_status"].value_counts().rename_axis("Status").reset_index(name="Count")
        fig = px.pie(status, names="Status", values="Count", hole=0.58,
                     color="Status", color_discrete_map=STATUS_COLORS)
        fig.update_layout(height=360, margin=dict(l=0, r=0, t=6, b=0),
                          legend=dict(orientation="h", y=-0.12))
        st.plotly_chart(fig, width='stretch')

    # ---- Auto-generated key insights (synthesizes the system) ----
    st.markdown(f"<div class='section-title'>{_stt('Key insights')}</div>", unsafe_allow_html=True)
    best_sport = df.groupby("Sport")["overall_score"].mean().idxmax()
    top_div = df["division"].value_counts().idxmax()
    girls_pct = nk["totals"]["girls"] / nk["totals"]["registered"] * 100
    conv = len(df) / nk["totals"]["registered"] * 100
    top_athlete = df.nlargest(1, "overall_score").iloc[0]
    insights = [
        f"🏆 <b>{best_sport}</b> is the strongest discipline by average performance score.",
        f"📍 <b>{top_div}</b> division contributes the largest share of the elite pool.",
        f"🌱 Grassroots pipeline holds <b>{nk['totals']['registered']:,}</b> prospects; "
        f"girls are <b>{girls_pct:.0f}%</b> — a clear equity target.",
        f"⭐ <b>{top_athlete['Name']}</b> ({top_athlete['Sport']}) leads nationally with a "
        f"score of <b>{top_athlete['overall_score']:.0f}</b>.",
        f"🩺 <b>{(~injured).mean()*100:.0f}%</b> of elite athletes are currently match-ready.",
        f"🎓 Coaching coverage: <b>{len(coaches)}</b> coaches across "
        f"<b>{df['Sport'].nunique()}</b> sports and <b>8</b> divisions.",
    ]
    ic = st.columns(2)
    for i, ins in enumerate(insights):
        ic[i % 2].markdown(
            f"<div class='profile' style='padding:14px 18px;margin-bottom:12px;"
            f"font-size:.92rem;color:{INK}'>{ins}</div>", unsafe_allow_html=True)

    st.caption("Synthesises data across the grassroots pipeline, elite athlete pool, "
               "performance model and coaching network. Grassroots figures are "
               "illustrative; see Notun Kuri for detail.")


# =========================================================================== #
#  PAGE 2 — PLAYER PROFILE                                                     #
# =========================================================================== #
def page_profile():
    row = df[df["Name"] == player_choice]
    if row.empty:
        st.warning("Select a player from the sidebar.")
        return
    a = row.iloc[0]

    top = st.columns([2.3, 1, 1])
    with top[0]:
        club_label = "ক্লাব / দল:" if is_bangla() else "Club / Team:"
        form_label = "সাম্প্রতিক ফর্ম:" if is_bangla() else "Recent form:"
        st.markdown(
            f"<div class='profile'><div style='display:flex;gap:16px;align-items:center'>"
            f"<div class='avatar'>{initials(a['Name'])}</div>"
            f"<div><div class='pname'>{a['Name']}</div>"
            f"<div class='prole'>{a.get('Position/Event','')}</div>"
            f"<div><span class='chip navy'>{a['Sport']}</span>"
            f"<span class='chip green'>{a['tier_label']}</span>"
            f"<span class='chip gold'>ID {a['ID']}</span></div></div></div>"
            f"<div style='margin-top:12px;color:{MUTED};font-size:.9rem'>"
            f"<b>{club_label}</b> {a.get('Team/Club','—')}</div>"
            f"<div style='margin-top:6px;color:{INK};font-size:.9rem'>"
            f"<b>{form_label}</b> {gt(a.get('Recent Stats','—'))}</div></div>",
            unsafe_allow_html=True,
        )
    with top[1]:
        rank_in_label = f"{a['Sport']} এ র‍্যাঙ্ক" if is_bangla() else f"Rank in {a['Sport']}"
        of_label = f"{int(a['sport_size'])} জনের মধ্যে" if is_bangla() else f"of {int(a['sport_size'])}"
        st.markdown(
            f"<div class='rankbadge'><div class='l'>{rank_in_label}</div>"
            f"<div class='r'>#{int(a['sport_rank'])}</div>"
            f"<div class='l'>{of_label}</div></div>",
            unsafe_allow_html=True,
        )
    with top[2]:
        pctl_label = "পার্সেন্টাইল" if is_bangla() else "Percentile"
        overall_label = (f"সার্বিক স্কোর {a['overall_score']:.1f}" if is_bangla()
                         else f"overall score {a['overall_score']:.1f}")
        st.markdown(
            f"<div class='rankbadge' style='background:linear-gradient(135deg,{GREEN},{NAVY})'>"
            f"<div class='l'>{pctl_label}</div>"
            f"<div class='r'>{a['sport_percentile']:.0f}</div>"
            f"<div class='l'>{overall_label}</div></div>",
            unsafe_allow_html=True,
        )

    st.write("")

    # ===================== ATHLETE 360 PROFILE (tabbed) ===================== #
    # Existing Overview is preserved as the first tab; new sections added after.
    import dataset as _ds
    tabs = st.tabs([t("tab_overview"), t("tab_personal"), t("tab_career"),
                    t("tab_performance"), t("tab_fitness_training"),
                    t("tab_health_coach"), t("tab_ai_insights"),
                    t("tab_compare"), t("tab_export")])

    # ---- TAB 1: Overview (unchanged existing content) --------------------- #
    with tabs[0]:
        c1, c2 = st.columns([1, 1.15])
        with c1:
            st.markdown(f"<div class='section-title'>{_stt('Biometrics &amp; vitals')}</div>",
                        unsafe_allow_html=True)
            _yrs = "বছর" if is_bangla() else "yrs"
            rows = [
                (t("metric_age"), f"{a['age']:.0f} {_yrs}"),
                (t("metric_height"), f"{a['height_cm']:.0f} cm"),
                (t("metric_weight"), f"{a['weight_kg']:.0f} kg"),
                (t("metric_vo2"), f"{a['vo2max']:.0f} mL/kg/min"),
                (t("metric_resting_hr"), f"{a['resting_hr']:.0f} BPM"),
                (t("metric_body_fat"), f"{a['body_fat']:.1f}%"),
                (t("metric_intake"), f"{a['intake_kcal']:,.0f} kcal"),
                (t("metric_burn"), f"{a['burn_kcal']:,.0f} kcal"),
                (t("metric_energy_balance"), f"{a['energy_balance']:+,.0f} kcal"),
            ]
            html = "".join(
                f"<div class='metric-row'><span class='k'>{k}</span>"
                f"<span class='v'>{v}</span></div>" for k, v in rows
            )
            status_color = STATUS_COLORS.get(a["injury_status"], MUTED)
            html += (f"<div class='metric-row'><span class='k'>{t('metric_injury_status')}</span>"
                     f"<span class='v' style='color:{status_color}'>"
                     f"● {ts(a['injury_status'])}</span></div>")
            st.markdown(f"<div class='profile'>{html}</div>", unsafe_allow_html=True)
            _injury_note_label = "ইনজুরি নোট:" if is_bangla() else "Injury note:"
            st.caption(f"{_injury_note_label} {gt(a.get('Injury History','—'))}")

        with c2:
            st.markdown("<div class='section-title'>Component breakdown "
                        "(0–100, vs same-sport peers)</div>", unsafe_allow_html=True)
            comps = [lbl for lbl, _, _ in scoring.MODEL_COMPONENTS]
            vals = [float(a[col]) for _, _, col in scoring.MODEL_COMPONENTS]
            radar = go.Figure()
            radar.add_trace(go.Scatterpolar(
                r=vals + [vals[0]], theta=comps + [comps[0]], fill="toself",
                line=dict(color=NAVY, width=2), fillcolor="rgba(27,138,76,.28)",
                name=a["Name"]))
            radar.update_layout(
                polar=dict(radialaxis=dict(range=[0, 100], showline=False,
                                           gridcolor="#e4edf5")),
                showlegend=False, height=330, margin=dict(l=30, r=30, t=20, b=20))
            st.plotly_chart(radar, width='stretch')

            cal = pd.DataFrame({"Metric": ["Intake", "Burn"],
                                "kcal": [a["intake_kcal"], a["burn_kcal"]]})
            fig = px.bar(cal, x="Metric", y="kcal", color="Metric", text="kcal",
                         color_discrete_map={"Intake": NAVY, "Burn": GREEN})
            fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig.update_layout(showlegend=False, height=250,
                              margin=dict(l=0, r=0, t=24, b=0),
                              title=dict(text="Daily calories: intake vs burn",
                                         font=dict(size=13, color=INK)))
            st.plotly_chart(fig, width='stretch')

    # ---- TAB 2: Personal Information -------------------------------------- #
    with tabs[1]:
        st.markdown(f"<div class='section-title'>{_stt('Personal information')}</div>",
                    unsafe_allow_html=True)
        src = str(a.get("data_source", ""))
        if "real-name" in src:
            st.caption("ℹ️ Real athlete name; attached statistics are illustrative "
                       "demonstration data, not verified records.")
        elif src == "dummy":
            st.caption("ℹ️ Illustrative demonstration profile (dummy data).")
        pers = [
            ("Full name", a.get("Name", "—")), ("Athlete ID", a.get("ID", "—")),
            ("Gender", a.get("gender", "—")), ("Age", f"{a['age']:.0f} yrs"),
            ("Sport", a.get("Sport", "—")), ("Event / Position", a.get("Position/Event", "—")),
            ("Division", a.get("division", "—")), ("District", a.get("district", "—")),
            ("Club", a.get("club", "—")), ("National team", a.get("national_team", "—")),
            ("Blood group", a.get("blood_group", "—")),
            ("Height", f"{a['height_cm']:.0f} cm"), ("Weight", f"{a['weight_kg']:.0f} kg"),
            ("BMI", f"{a.get('bmi','—')}"),
            ("Emergency contact", a.get("emergency_contact", "—")),
        ]
        colA, colB = st.columns(2)
        half = (len(pers) + 1) // 2
        for col, chunk in ((colA, pers[:half]), (colB, pers[half:])):
            html = "".join(f"<div class='metric-row'><span class='k'>{k}</span>"
                           f"<span class='v'>{v}</span></div>" for k, v in chunk)
            col.markdown(f"<div class='profile'>{html}</div>", unsafe_allow_html=True)

    # ---- TAB 3: Career (statistics + timeline + achievements) ------------- #
    with tabs[2]:
        # --- Sport-specific performance (real per-sport metrics) ----------
        st.markdown(f"<div class='section-title'>{a['Sport']} performance "
                    f"<span style='font-size:.72rem;color:{MUTED}'>"
                    f"(sport-specific metrics)</span></div>", unsafe_allow_html=True)
        sstats = a.get("sport_stats") or []
        if sstats:
            per_row = 4
            for start in range(0, len(sstats), per_row):
                chunk = sstats[start:start + per_row]
                cols = st.columns(len(chunk))
                for col, (label, value) in zip(cols, chunk):
                    col.markdown(
                        f"<div class='kpi' style='border-left-color:{NAVY}'>"
                        f"<div class='label'>{label}</div>"
                        f"<div class='value' style='font-size:1.3rem'>{value}</div>"
                        f"</div>", unsafe_allow_html=True)
            st.write("")

        st.markdown(f"<div class='section-title'>{_stt('Career summary')}</div>",
                    unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        kpi(k1, "Matches", f"{int(a.get('career_matches',0)):,}")
        kpi(k2, "Win %", f"{a.get('career_win_pct',0):.0f}%", cls="green")
        kpi(k3, "Medals", f"{int(a.get('career_medals',0))}", cls="gold")
        kpi(k4, "Nat. rank", f"#{int(a.get('national_ranking',0))}")
        k5, k6, k7, k8 = st.columns(4)
        kpi(k5, "Wins", f"{int(a.get('career_wins',0))}")
        kpi(k6, "Losses", f"{int(a.get('career_losses',0))}")
        kpi(k7, "Medal %", f"{a.get('career_medal_pct',0):.0f}%", cls="gold")
        kpi(k8, "Int. rank", f"#{int(a.get('international_ranking',0))}")

        st.markdown(f"<div style='margin-top:10px'></div>", unsafe_allow_html=True)
        st.markdown(f"<span class='chip green'>Best: {a.get('best_performance','—')}</span>"
                    f"<span class='chip navy'>Worst: {a.get('worst_performance','—')}</span>",
                    unsafe_allow_html=True)

        cta, ctb = st.columns(2)
        with cta:
            st.markdown(f"<div class='section-title'>{_stt('Career timeline')}</div>",
                        unsafe_allow_html=True)
            tl = a.get("career_timeline") or []
            if isinstance(tl, list) and tl:
                tldf = pd.DataFrame(tl)
                st.dataframe(tldf, width='stretch', hide_index=True,
                             height=min(320, 40 + 34 * len(tldf)))
            else:
                st.caption("No timeline available.")
        with ctb:
            st.markdown(f"<div class='section-title'>{_stt('National &amp; international results')}</div>",
                        unsafe_allow_html=True)
            nat = a.get("national_results") or []
            intl = a.get("international_results") or []
            merged = ([{**r, "level": "National"} for r in nat] +
                      [{**r, "level": "International"} for r in intl])
            if merged:
                st.dataframe(pd.DataFrame(merged)[["year", "level", "competition", "result"]],
                             width='stretch', hide_index=True,
                             height=min(320, 40 + 34 * len(merged)))
            else:
                st.caption("No results recorded.")

        st.markdown(f"<div class='section-title'>{_stt('Achievements &amp; highlights')}</div>",
                    unsafe_allow_html=True)
        hl = a.get("career_highlights") or []
        if isinstance(hl, list) and hl:
            st.markdown("".join(f"<span class='chip gold'>🏅 {gt(h)}</span>" for h in hl),
                        unsafe_allow_html=True)
        else:
            st.caption("কোনো কৃতিত্ব রেকর্ড করা হয়নি।" if is_bangla() else "No highlights recorded.")

    # ---- TAB 4: Performance trends + ranking details ---------------------- #
    with tabs[3]:
        st.markdown(f"<div class='section-title'>{_stt('Career progress trend')}</div>",
                    unsafe_allow_html=True)
        prog = a.get("career_progress") or []
        if isinstance(prog, list) and prog:
            pdf = pd.DataFrame(prog)
            fig = px.area(pdf, x="year", y="rating", markers=True,
                          labels={"rating": "Rating (0–100)", "year": "Year"})
            fig.update_traces(line_color=NAVY, fillcolor="rgba(27,138,76,.18)")
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=6, b=0),
                              yaxis_range=[40, 100])
            st.plotly_chart(fig, width='stretch')

        sc = a.get("season_stats") or []
        if isinstance(sc, list) and sc:
            st.markdown(f"<div class='section-title'>{_stt('Season-by-season')}</div>",
                        unsafe_allow_html=True)
            sdf = pd.DataFrame(sc)
            fig = px.bar(sdf, x="season", y=["wins", "losses"], barmode="stack",
                         color_discrete_map={"wins": GREEN, "losses": "#c0563b"},
                         labels={"value": "Matches", "season": "Season"})
            fig.update_layout(height=280, margin=dict(l=0, r=0, t=6, b=0),
                              legend=dict(orientation="h", y=1.15))
            st.plotly_chart(fig, width='stretch')

        st.markdown(f"<div class='section-title'>{_stt('Ranking details')}</div>",
                    unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        kpi(r1, f"Rank in {a['Sport']}", f"#{int(a['sport_rank'])}",
            f"of {int(a['sport_size'])}")
        kpi(r2, "Percentile", f"{a['sport_percentile']:.0f}", "within sport", cls="green")
        kpi(r3, "Overall score", f"{a['overall_score']:.1f}", "0–100", cls="gold")
        st.caption("Overall score is the weighted blend of Performance, Fitness, "
                   "Availability, Training load and Nutrition — each normalised "
                   "against same-sport peers. See the Rankings page for the formula.")

    # ---- TAB 5: Fitness history + training attendance --------------------- #
    with tabs[4]:
        st.markdown(f"<div class='section-title'>{_stt('Fitness profile')}</div>",
                    unsafe_allow_html=True)
        f1, f2, f3, f4 = st.columns(4)
        kpi(f1, "Fitness rating", f"{int(a.get('fitness_rating',0))}", "0–100", cls="green")
        kpi(f2, "VO₂ Max", f"{a['vo2max']:.0f}", "mL/kg/min")
        kpi(f3, "Resting HR", f"{a['resting_hr']:.0f}", "BPM", cls="green")
        kpi(f4, "Body Fat", f"{a['body_fat']:.1f}%", "")

        st.markdown(f"<div class='section-title'>{_stt('Training attendance')}</div>",
                    unsafe_allow_html=True)
        att = float(a.get("training_attendance", 0))
        gfig = go.Figure(go.Indicator(
            mode="gauge+number", value=att,
            number={"suffix": "%"},
            gauge={"axis": {"range": [0, 100]},
                   "bar": {"color": GREEN},
                   "steps": [{"range": [0, 70], "color": "#f3d6cf"},
                             {"range": [70, 85], "color": "#fdf3dc"},
                             {"range": [85, 100], "color": "#e8f6ee"}]}))
        gfig.update_layout(height=240, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(gfig, width='stretch')
        st.caption(f"Attendance of {att:.0f}% — "
                   + ("excellent consistency." if att >= 85
                      else "room to tighten session consistency." if att >= 70
                      else "attendance is limiting adaptation."))

    # ---- TAB 6: Injury history + coach feedback --------------------------- #
    with tabs[5]:
        st.markdown(f"<div class='section-title'>{_stt('Injury &amp; availability')}</div>",
                    unsafe_allow_html=True)
        sc_color = STATUS_COLORS.get(a["injury_status"], MUTED)
        _cur_status_lbl = "বর্তমান অবস্থা" if is_bangla() else "Current status"
        _avail_idx_lbl = "প্রাপ্যতা সূচক" if is_bangla() else "Availability index"
        _hist_note_lbl = "ইতিহাস নোট" if is_bangla() else "History note"
        st.markdown(f"<div class='profile'>"
                    f"<div class='metric-row'><span class='k'>{_cur_status_lbl}</span>"
                    f"<span class='v' style='color:{sc_color}'>● {ts(a['injury_status'])}</span></div>"
                    f"<div class='metric-row'><span class='k'>{_avail_idx_lbl}</span>"
                    f"<span class='v'>{a.get('health_score',0):.0f}/100</span></div>"
                    f"<div class='metric-row'><span class='k'>{_hist_note_lbl}</span>"
                    f"<span class='v'>{gt(a.get('Injury History','—'))}</span></div></div>",
                    unsafe_allow_html=True)

        st.markdown(f"<div class='section-title'>{_stt('Coach feedback')}</div>",
                    unsafe_allow_html=True)
        # Divisional coach for this athlete's sport+division (from coach DB).
        coaches = get_coaches(str(DATA_PATH))
        match = coaches[(coaches["sport"] == a["Sport"]) &
                        (coaches["division"] == a.get("division"))]
        if not match.empty:
            c = match.iloc[0]
            fb = gt(_coach_feedback(a))
            _division_word = "বিভাগ" if is_bangla() else "Division"
            _yrs_exp = "বছরের অভিজ্ঞতা" if is_bangla() else "yrs exp"
            st.markdown(
                f"<div class='profile'><div style='display:flex;gap:14px;align-items:center'>"
                f"<div class='avatar'>{initials(c['name'])}</div>"
                f"<div><div class='pname' style='font-size:1.05rem'>{c['name']}</div>"
                f"<div class='prole'>{gt(c['specialization'])} · {c['division']} {_division_word}</div>"
                f"<div><span class='chip navy'>{gt(c['license'])}</span>"
                f"<span class='chip green'>{c['experience_years']} {_yrs_exp}</span></div>"
                f"</div></div><div style='margin-top:12px;color:{INK};font-size:.92rem'>"
                f"“{fb}”</div></div>", unsafe_allow_html=True)
        else:
            st.caption("No assigned divisional coach on record.")

    # ---- TAB 7: AI Insights (recommendation engine) ----------------------- #
    with tabs[6]:
        rec = _ds.generate_recommendations_bn(a) if is_bangla() else _ds.generate_recommendations(a)
        _ai_title = "এআই পারফরম্যান্স পরামর্শ" if is_bangla() else "AI performance insight"
        _ai_sub = "(নিয়মভিত্তিক বিশ্লেষণ)" if is_bangla() else "(rule-based analytics)"
        st.markdown(f"<div class='section-title'>{_ai_title} "
                    f"<span style='font-size:.7rem;color:#5a6b7b'>{_ai_sub}</span>"
                    "</div>", unsafe_allow_html=True)
        sA, sB = st.columns(2)
        with sA:
            st.markdown(f"**💪 {'শক্তির ক্ষেত্র' if is_bangla() else 'Strengths'}**")
            st.markdown("".join(f"<span class='chip green'>{s}</span>" for s in rec["strengths"]),
                        unsafe_allow_html=True)
        with sB:
            st.markdown(f"**🎯 {'উন্নতির ক্ষেত্র' if is_bangla() else 'Focus areas'}**")
            st.markdown("".join(f"<span class='chip gold'>{w}</span>" for w in rec["weaknesses"]),
                        unsafe_allow_html=True)

        st.markdown(f"<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        if is_bangla():
            recmap = [("🏃 ফিটনেস", rec["fitness"]), ("🏋️ প্রশিক্ষণ", rec["training"]),
                     ("🛌 পুনরুদ্ধার", rec["recovery"]), ("🥗 খাদ্য", rec["diet"]),
                     ("🎽 কারিগরি", rec["technical"]), ("🧠 মানসিক প্রশিক্ষণ", rec["mental"])]
        else:
            recmap = [("🏃 Fitness", rec["fitness"]), ("🏋️ Training", rec["training"]),
                     ("🛌 Recovery", rec["recovery"]), ("🥗 Diet", rec["diet"]),
                     ("🎽 Technical", rec["technical"]), ("🧠 Mental coaching", rec["mental"])]
        cc = st.columns(2)
        for i, (title, body) in enumerate(recmap):
            with cc[i % 2]:
                st.markdown(f"<div class='profile' style='margin-bottom:10px'>"
                            f"<b>{title}</b><div style='color:{MUTED};font-size:.9rem;"
                            f"margin-top:4px'>{body}</div></div>", unsafe_allow_html=True)

        _exp_label = "প্রত্যাশিত উন্নতি" if is_bangla() else "Expected improvement"
        st.markdown(f"<div class='rankbadge' style='margin-top:6px'>"
                    f"<div class='l'>{_exp_label}</div>"
                    f"<div class='r'>{rec['current_overall']:.0f} → {rec['projected_overall']:.0f}</div>"
                    f"<div class='l'>{rec['expected_improvement']}</div></div>",
                    unsafe_allow_html=True)
        st.caption("সুপারিশগুলো একটি স্বচ্ছ নিয়মভিত্তিক ইঞ্জিন দ্বারা এই অ্যাথলিটের নিজস্ব "
                  "পরিসংখ্যান থেকে তৈরি — কোনো ব্ল্যাক-বক্স মডেল নয়।" if is_bangla() else
                  "Recommendations are generated by a transparent rules engine "
                  "from this athlete's own metrics — not a black-box model.")

    # ---- TAB 8: Compare player ------------------------------------------- #
    with tabs[7]:
        st.markdown(f"<div class='section-title'>{_stt('Compare with another athlete')}</div>",
                    unsafe_allow_html=True)
        same_sport = df[df["Sport"] == a["Sport"]]["Name"].tolist()
        others = [n for n in same_sport if n != a["Name"]]
        if not others:
            st.caption("No other athlete in this sport to compare.")
        else:
            other = st.selectbox(f"Compare {a['Name']} against:", others, key="cmp_sel")
            b = df[df["Name"] == other].iloc[0]
            comps = [lbl for lbl, _, _ in scoring.MODEL_COMPONENTS]
            keys = [col for _, _, col in scoring.MODEL_COMPONENTS]
            radar = go.Figure()
            for who, color, fill in ((a, NAVY, "rgba(11,79,138,.22)"),
                                     (b, GREEN, "rgba(27,138,76,.22)")):
                rv = [who[k] for k in keys]
                radar.add_trace(go.Scatterpolar(r=rv + [rv[0]], theta=comps + [comps[0]],
                                                fill="toself", name=who["Name"],
                                                line=dict(color=color, width=2), fillcolor=fill))
            radar.update_layout(polar=dict(radialaxis=dict(range=[0, 100], gridcolor="#e4edf5")),
                                height=380, margin=dict(l=30, r=30, t=20, b=30),
                                legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(radar, width='stretch')
            cmp_rows = [
                ("Overall score", f"{a['overall_score']:.1f}", f"{b['overall_score']:.1f}"),
                ("Rank in sport", f"#{int(a['sport_rank'])}", f"#{int(b['sport_rank'])}"),
                ("Win %", f"{a.get('career_win_pct',0):.0f}%", f"{b.get('career_win_pct',0):.0f}%"),
                ("Medals", f"{int(a.get('career_medals',0))}", f"{int(b.get('career_medals',0))}"),
                ("VO₂ Max", f"{a['vo2max']:.0f}", f"{b['vo2max']:.0f}"),
                ("Fitness rating", f"{int(a.get('fitness_rating',0))}", f"{int(b.get('fitness_rating',0))}"),
            ]
            cmp_html = ("<div class='profile'><div class='metric-row'>"
                        f"<span class='k'><b>Metric</b></span>"
                        f"<span class='v'>{a['Name'].split()[0]} · {b['Name'].split()[0]}</span></div>")
            for k, va, vb in cmp_rows:
                cmp_html += (f"<div class='metric-row'><span class='k'>{k}</span>"
                             f"<span class='v'>{va} &nbsp;·&nbsp; {vb}</span></div>")
            cmp_html += "</div>"
            st.markdown(cmp_html, unsafe_allow_html=True)

    # ---- TAB 9: Export profile ------------------------------------------- #
    with tabs[8]:
        st.markdown(f"<div class='section-title'>{_stt('Export this profile')}</div>",
                    unsafe_allow_html=True)
        flat = {k: a.get(k) for k in [
            "ID", "Name", "Sport", "Position/Event", "gender", "age", "division",
            "district", "club", "national_team", "blood_group", "height_cm",
            "weight_kg", "bmi", "vo2max", "resting_hr", "body_fat",
            "career_matches", "career_wins", "career_losses", "career_medals",
            "career_win_pct", "career_medal_pct", "national_ranking",
            "international_ranking", "performance_rating", "fitness_rating",
            "training_attendance", "injury_status", "overall_score",
            "sport_rank", "sport_percentile", "best_performance", "worst_performance",
        ]}
        rec = _ds.generate_recommendations(a)
        export = {"profile": flat,
                  "career_timeline": a.get("career_timeline"),
                  "season_stats": a.get("season_stats"),
                  "highlights": a.get("career_highlights"),
                  "ai_recommendations": rec}
        import json as _json
        payload = _json.dumps(export, indent=2, default=str)
        st.download_button("⬇️ Download full profile (JSON)", payload,
                           file_name=f"{a['ID']}_{a['Name'].replace(' ','_')}_profile.json",
                           mime="application/json")
        csv_row = pd.DataFrame([flat]).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download summary (CSV)", csv_row,
                           file_name=f"{a['ID']}_{a['Name'].replace(' ','_')}_summary.csv",
                           mime="text/csv")
        st.caption("Exports use this athlete's current model-derived values.")


def _coach_feedback(a) -> str:
    """A short, stat-aware coach note (deterministic)."""
    pct = float(a.get("sport_percentile", 50))
    status = str(a.get("injury_status", ""))
    if status in ("Monitored / Restricted", "Actively Managed"):
        return ("Managing workload carefully this cycle; technically sound, and I "
                "expect a strong return once fully cleared.")
    if pct >= 80:
        return ("A standout in the divisional pool — disciplined in training and "
                "reliable under pressure. Pushing for national-camp selection.")
    if pct >= 50:
        return ("Solid, coachable athlete with clear upside. Consistency in the "
                "gym is turning into competition results.")
    return ("Raw potential that needs volume and routine. With steady attendance "
            "the base will come quickly.")


# =========================================================================== #
#  PAGE 3 — PERFORMANCE & FITNESS                                             #
# =========================================================================== #
def page_fitness():
    scope_label = t("scope_all_sports") if sport_choice == "All Sports" else sport_choice
    st.markdown(f"<div class='section-title'>{t('sec_fitness_analytics', scope=scope_label)}</div>",
                unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, t("kpi_avg_vo2"), f"{scoped['vo2max'].mean():.1f}", "mL/kg/min")
    kpi(c2, t("kpi_avg_resting_hr"), f"{scoped['resting_hr'].mean():.0f}", "BPM", cls="green")
    kpi(c3, t("kpi_avg_bodyfat"), f"{scoped['body_fat'].mean():.1f}%", "", cls="green")
    kpi(c4, t("kpi_fittest"),
        f"{scoped.loc[scoped['fitness_n'].idxmax(), 'Name'].split()[0]}"
        if len(scoped) else "—",
        t("foot_fitness_index", v=f"{scoped['fitness_n'].max():.0f}") if len(scoped) else "",
        cls="gold")

    st.write("")
    l, r = st.columns(2)
    with l:
        st.markdown(f"<div class='section-title'>{_stt('VO₂ Max vs Body Fat')}</div>",
                    unsafe_allow_html=True)
        fig = px.scatter(scoped, x="vo2max", y="body_fat", color="Sport",
                         size="overall_score", hover_name="Name",
                         color_discrete_sequence=SEQ,
                         labels={"vo2max": "VO₂ Max (mL/kg/min)",
                                 "body_fat": "Body Fat (%)"})
        fig.update_layout(height=420, margin=dict(l=0, r=0, t=6, b=0),
                          legend=dict(orientation="h", y=-0.25)
                          if sport_choice == "All Sports" else dict())
        if sport_choice != "All Sports":
            fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width='stretch')

    with r:
        st.markdown(f"<div class='section-title'>{_stt('VO₂ Max distribution')}</div>",
                    unsafe_allow_html=True)
        if sport_choice == "All Sports":
            fig = px.box(df, x="Sport", y="vo2max", color="Sport",
                         color_discrete_sequence=SEQ,
                         labels={"vo2max": "VO₂ Max"})
            fig.update_layout(showlegend=False, height=420,
                              margin=dict(l=0, r=0, t=6, b=0),
                              xaxis=dict(tickangle=-40))
        else:
            fig = px.histogram(scoped, x="vo2max", nbins=12,
                               color_discrete_sequence=[NAVY],
                               labels={"vo2max": "VO₂ Max (mL/kg/min)"})
            fig.update_layout(height=420, margin=dict(l=0, r=0, t=6, b=0),
                              bargap=0.05)
        st.plotly_chart(fig, width='stretch')

    st.markdown(f"<div class='section-title'>{_stt('Fitness component index by athlete')}</div>",
                unsafe_allow_html=True)
    top_n = scoped.nlargest(min(15, len(scoped)), "fitness_n")
    fig = px.bar(top_n.sort_values("fitness_n"), x="fitness_n", y="Name",
                 orientation="h", color="fitness_n",
                 color_continuous_scale=["#cfe0ef", NAVY, GREEN],
                 labels={"fitness_n": "Fitness index (0–100)", "Name": ""})
    fig.update_layout(height=max(300, 26 * len(top_n)),
                      margin=dict(l=0, r=0, t=6, b=0), coloraxis_showscale=False)
    st.plotly_chart(fig, width='stretch')


# =========================================================================== #
#  PAGE 4 — INJURY & TRAINING                                                 #
# =========================================================================== #
def page_injury():
    scope_label = t("scope_all_sports") if sport_choice == "All Sports" else sport_choice
    _inj_title = "ইনজুরি ও প্রশিক্ষণ" if is_bangla() else "Injury &amp; training"
    st.markdown(f"<div class='section-title'>{_inj_title} — {scope_label}</div>",
                unsafe_allow_html=True)

    watch = scoped["injury_status"].isin(
        ["Actively Managed", "Monitored / Restricted"])
    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, t("kpi_fully_fit"), f"{(scoped['injury_status']=='Fully Fit').sum()}",
        f"{(scoped['injury_status']=='Fully Fit').mean()*100:.0f}{t('foot_of_scope')}")
    kpi(c2, t("kpi_on_watch_full"), f"{int(watch.sum())}",
        t("foot_managed_restricted"), cls="gold")
    kpi(c3, t("kpi_avg_burn"), f"{scoped['burn_kcal'].mean():,.0f}",
        t("foot_kcal_day"), cls="green")
    kpi(c4, t("kpi_avg_avail"), f"{scoped['health_score'].mean():.0f}",
        t("foot_health_index"), cls="green")

    st.write("")
    l, r = st.columns([1, 1.2])
    with l:
        st.markdown(f"<div class='section-title'>{_stt('Availability breakdown')}</div>",
                    unsafe_allow_html=True)
        status = (scoped["injury_status"].value_counts()
                  .rename_axis("Status").reset_index(name="Count"))
        fig = px.bar(status, x="Count", y="Status", orientation="h",
                     color="Status", color_discrete_map=STATUS_COLORS, text="Count")
        fig.update_layout(showlegend=False, height=320,
                          margin=dict(l=0, r=0, t=6, b=0),
                          yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig, width='stretch')

    with r:
        st.markdown(f"<div class='section-title'>{_stt('Training load vs availability')}</div>",
                    unsafe_allow_html=True)
        fig = px.scatter(scoped, x="burn_kcal", y="health_score",
                         color="injury_status", hover_name="Name",
                         size="intake_kcal", color_discrete_map=STATUS_COLORS,
                         labels={"burn_kcal": "Daily burn (kcal)",
                                 "health_score": "Availability index"})
        fig.update_layout(height=320, margin=dict(l=0, r=0, t=6, b=0),
                          legend=dict(orientation="h", y=-0.3))
        st.plotly_chart(fig, width='stretch')

    # ---- Calorie intake vs burn (headline requirement) ----
    st.markdown(f"<div class='section-title'>{_stt('Calorie intake vs burn')}</div>",
                unsafe_allow_html=True)
    if sport_choice == "All Sports":
        cal = (df.groupby("Sport")
               .agg(Intake=("intake_kcal", "mean"), Burn=("burn_kcal", "mean"))
               .reset_index().sort_values("Intake"))
        m = cal.melt(id_vars="Sport", value_vars=["Intake", "Burn"],
                     var_name="Metric", value_name="kcal")
        fig = px.bar(m, x="Sport", y="kcal", color="Metric", barmode="group",
                     color_discrete_map={"Intake": NAVY, "Burn": GREEN},
                     labels={"kcal": "Avg kcal / day"})
        fig.update_layout(height=420, margin=dict(l=0, r=0, t=6, b=0),
                          xaxis=dict(tickangle=-40),
                          legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, width='stretch')
        st.caption("Grouped bars compare average daily intake against burn for "
                   "each sport; the gap is the mean energy surplus fuelling "
                   "recovery and adaptation.")
    else:
        d = scoped.sort_values("burn_kcal")
        m = d.melt(id_vars="Name", value_vars=["intake_kcal", "burn_kcal"],
                   var_name="Metric", value_name="kcal")
        m["Metric"] = m["Metric"].map({"intake_kcal": "Intake",
                                       "burn_kcal": "Burn"})
        fig = px.bar(m, x="Name", y="kcal", color="Metric", barmode="group",
                     color_discrete_map={"Intake": NAVY, "Burn": GREEN},
                     labels={"kcal": "kcal / day", "Name": ""})
        fig.update_layout(height=440, margin=dict(l=0, r=0, t=6, b=0),
                          xaxis=dict(tickangle=-55),
                          legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, width='stretch')


# =========================================================================== #
#  PAGE 5 — RANKINGS & LEADERBOARD                                            #
# =========================================================================== #
def page_rankings():
    st.markdown(f"<div class='section-title'>{_stt('Within-sport ranking model')}</div>",
                unsafe_allow_html=True)

    # Live weight readout (driven by the model definition).
    _MC = scoring.MODEL_COMPONENTS
    wc = st.columns(len(_MC))
    for i, (col, (label, wkey, _)) in enumerate(zip(wc, _MC)):
        kpi(col, label, f"{norm_w[wkey]*100:.0f}%", t("foot_current_weight"),
            cls=["", "green", "gold"][i % 3])

    with st.expander(t("exp_how_calculated"), expanded=False):
        signal = {
            "fitness": "VO₂ Max (+), Resting HR (−), Body Fat (−)",
            "career": "career win %, medals, national & international ranking",
            "nutrition": f"closeness of Intake/Burn to the ideal (~{scoring.IDEAL_INTAKE_BURN_RATIO:.2f})",
            "attendance": "training attendance %",
            "medical": "availability from the injury-history rubric",
            "coach": "divisional coach evaluation rating",
        }
        table = ("| Component | Signal (higher = better) | Weight |\n|---|---|---|\n"
                 + "\n".join(f"| **{label}** | {signal[wkey]} | {norm_w[wkey]*100:.0f}% |"
                            for label, wkey, _ in _MC))
        st.markdown(f"""
Each athlete gets six components, every one rescaled to **0–100 within their
own sport** (so a swimmer is compared only to swimmers):

{table}

**Overall = Σ (weight × component)**, then within each sport
**Rank** = position by overall score (1 = best) and
**Percentile** = share of same-sport athletes scoring at or below.

Weights are set in `scoring.DEFAULT_WEIGHTS` and can be changed live from the
sidebar. Career sub-weights live in `scoring.DEFAULT_CAREER_WEIGHTS`; fitness
sub-weights in `scoring.DEFAULT_FITNESS_WEIGHTS`.
""")

    # Leaderboard respects the sidebar Sport filter and updates with weights.
    if sport_choice == "All Sports":
        st.info(t("info_top_of_sport"))
        board = (df.sort_values("sport_rank")
                 .groupby("Sport", as_index=False).head(1)
                 .sort_values("overall_score", ascending=False))
        title = t("sport_leaders")
    else:
        board = scoped.sort_values("sport_rank")
        title = f"{sport_choice} leaderboard"

    st.markdown(f"<div class='section-title'>{title} "
                f"({len(board)} athletes)</div>", unsafe_allow_html=True)

    show = board.copy()
    show["Rank"] = show["sport_rank"].astype(int)
    short = {"Fitness": "Fit", "Career": "Career", "Nutrition": "Nutr",
             "Attendance": "Attend", "Medical": "Med", "Coach Eval": "Coach"}
    comp_cols = [short[label] for label, _, _ in _MC]
    base_cols = ["Rank", "Name", "Sport", "tier_label", "overall_score", "sport_percentile"]
    disp = show[base_cols + [col for _, _, col in _MC] + ["injury_status"]].rename(
        columns={"tier_label": "Tier", "overall_score": "Overall",
                 "sport_percentile": "Pctl", "injury_status": "Status",
                 **{col: short[label] for label, _, col in _MC}})

    # --- Styling without matplotlib (hand-rolled gradient) --------------- #
    def _gradient(col: pd.Series, rgb: str) -> list[str]:
        lo, hi = col.min(), col.max()
        span = (hi - lo) or 1.0
        return [f"background-color: rgba({rgb},{0.08 + 0.55 * (0.0 if pd.isna(v) else (float(v)-lo)/span):.2f})"
                for v in col]

    def _highlight(r):
        if r["Name"] == player_choice:
            return ["background-color:#fdf3dc" for _ in r]
        return ["" for _ in r]

    fmt = {"Overall": "{:.1f}", "Pctl": "{:.0f}"}
    fmt.update({c: "{:.0f}" for c in comp_cols})
    styled = (disp.style.format(fmt)
              .apply(_gradient, rgb="27,138,76", subset=["Overall"])
              .apply(_gradient, rgb="11,79,138", subset=comp_cols)
              .apply(_highlight, axis=1))
    st.dataframe(styled, width='stretch', height=min(560, 60 + 35 * len(disp)),
                 hide_index=True)

    st.download_button(
        "⬇️ Download this leaderboard (CSV)",
        disp.to_csv(index=False).encode("utf-8"),
        file_name=f"leaderboard_{sport_choice.replace(' ', '_').lower()}.csv",
        mime="text/csv",
    )

    # Visual: stacked weighted contribution for the visible board (top 12).
    st.markdown(f"<div class='section-title'>{_stt('Weighted score contribution')}</div>",
                unsafe_allow_html=True)
    top = board.nlargest(min(12, len(board)), "overall_score").copy()
    palette = [NAVY, "#1667a8", GREEN, GREEN_LIGHT, GOLD, "#8a6d3b"]
    cmap = {label: palette[i % len(palette)] for i, (label, _, _) in enumerate(_MC)}
    parts = []
    for label, wkey, col in _MC:
        parts.append(pd.DataFrame({
            "Name": top["Name"], "Component": label,
            "Contribution": top[col] * norm_w[wkey]}))
    contrib = pd.concat(parts)
    order = top.sort_values("overall_score")["Name"].tolist()
    fig = px.bar(contrib, x="Contribution", y="Name", color="Component",
                 orientation="h", color_discrete_map=cmap,
                 category_orders={"Name": order})
    fig.update_layout(height=max(320, 30 * len(top)),
                      margin=dict(l=0, r=0, t=6, b=0),
                      legend=dict(orientation="h", y=1.08),
                      xaxis_title="Weighted points toward overall score",
                      yaxis_title="")
    st.plotly_chart(fig, width='stretch')


# --------------------------------------------------------------------------- #
#  PAGE — NOTUN KURI (grassroots talent pipeline)                             #
# --------------------------------------------------------------------------- #
def page_notunkuri():
    import dataset as _ds
    nk = _ds.get_notun_kuri()
    tot = nk["totals"]

    st.markdown(
        "<div class='gov-header' style='background:linear-gradient(120deg,"
        f"{GREEN} 0%, #14663a 60%, {NAVY} 130%)'>"
        "<div class='gh-row'><div style='font-size:2.4rem'>🌱</div>"
        f"<div><h1>{t('page_notunkuri_title')}</h1>"
        f"<div class='sub'>"
        + ("তৃণমূল প্রতিভা অনুসন্ধান · বয়স ১২–১৪ · যুব ও ক্রীড়া মন্ত্রণালয়" if is_bangla()
           else "Grassroots talent hunt · Ages 12–14 · Ministry of Youth &amp; Sports")
        + "</div><div class='flag'></div></div></div></div>", unsafe_allow_html=True)

    st.info(
        ("📊 কর্মসূচির প্রকৃত প্রকাশিত মোট সংখ্যার (১,৬০,৭৭৯ নিবন্ধিত) উপর ভিত্তি করে "
         "**উদাহরণস্বরূপ প্রদর্শনী তথ্য**। বিভাগ ও বিষয়ভিত্তিক বিভাজন কাঠামোগত প্রদর্শনের জন্য।")
        if is_bangla() else
        ("📊 Figures are **illustrative demonstration data** modeled on the "
         "programme's real published totals (160,779 registered). Per-division "
         "and per-discipline breakdowns are for structural demonstration.")
    )

    # Headline tiles.
    tiles = [
        ("📝", f"{tot['registered']:,}", t("kpi_total_registered"), (GREEN, "#14663a")),
        ("👦", f"{tot['boys']:,}", t("kpi_boys"), (NAVY, NAVY_DARK)),
        ("👧", f"{tot['girls']:,}", t("kpi_girls"), ("#b0468a", "#7a2f60")),
        ("🎯", f"{tot['disciplines']}", t("kpi_disciplines"), (GOLD, "#c98f2a")),
    ]
    cols = st.columns(4)
    for col, (icon, val, label, (c1, c2)) in zip(cols, tiles):
        col.markdown(
            f"<div class='glance' style='min-height:120px;"
            f"background:linear-gradient(135deg,{c1},{c2})'>"
            f"<div class='gi' style='font-size:1.5rem'>{icon}</div>"
            f"<div><div class='gv' style='font-size:1.9rem'>{val}</div>"
            f"<div class='gl' style='font-size:.78rem'>{label}</div></div></div>",
            unsafe_allow_html=True)

    st.write("")
    left, right = st.columns([1.15, 1])

    # --- Talent funnel (the core story) ---
    with left:
        st.markdown(f"<div class='section-title'>{_stt('Talent pathway funnel')}</div>",
                    unsafe_allow_html=True)
        stages = nk["stages"]
        fig = go.Figure(go.Funnel(
            y=[s for s, _ in stages], x=[v for _, v in stages],
            textinfo="value+percent initial",
            marker=dict(color=[NAVY, "#1667a8", GREEN, GREEN_LIGHT, GOLD]),
            connector=dict(line=dict(color="#cfe0ef"))))
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=6, b=0))
        st.plotly_chart(fig, width='stretch')
        st.caption("From nationwide registration down to the elite pathway — the "
                   "grassroots feed for the senior athletes tracked elsewhere in "
                   "this platform.")

    # --- Gender split + discipline ---
    with right:
        st.markdown(f"<div class='section-title'>{_stt('Participation by gender')}</div>",
                    unsafe_allow_html=True)
        _boys_lbl = "ছেলে" if is_bangla() else "Boys"
        _girls_lbl = "মেয়ে" if is_bangla() else "Girls"
        gdf = pd.DataFrame({"Gender": [_boys_lbl, _girls_lbl],
                            "Count": [tot["boys"], tot["girls"]]})
        fig = px.pie(gdf, names="Gender", values="Count", hole=0.58,
                     color="Gender",
                     color_discrete_map={_boys_lbl: NAVY, _girls_lbl: "#b0468a"})
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=6, b=0),
                          legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig, width='stretch')
        _equity_caption = (
            f"{tot['girls']/tot['registered']*100:.0f}% মেয়ে — একটি পরিমাপযোগ্য "
            "সমতার ব্যবধান যা কর্মসূচি দূর করতে পারে।"
            if is_bangla() else
            f"{tot['girls']/tot['registered']*100:.0f}% girls — a measurable "
            "equity gap the programme can be steered to close.")
        st.caption(_equity_caption)

    # --- By discipline ---
    st.markdown(f"<div class='section-title'>{_stt('Registrations by discipline')}</div>",
                unsafe_allow_html=True)
    ddf = pd.DataFrame(nk["by_discipline"]).sort_values("participants")
    fig = px.bar(ddf, x="participants", y="sport", orientation="h",
                 color="participants",
                 color_continuous_scale=["#cfe0ef", GREEN_LIGHT, NAVY],
                 text="participants")
    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(height=340, margin=dict(l=0, r=10, t=6, b=0),
                      coloraxis_showscale=False,
                      xaxis_title="Registered participants", yaxis_title="")
    st.plotly_chart(fig, width='stretch')

    # --- By division: map + table ---
    st.markdown(f"<div class='section-title'>{_stt('Grassroots reach across Bangladesh')}</div>",
                unsafe_allow_html=True)
    mcol, tcol = st.columns([1.1, 1])
    bydiv = pd.DataFrame(nk["by_division"])
    with mcol:
        geo = _load_bd_geojson()
        if geo:
            fig = px.choropleth(
                bydiv, geojson=geo, locations="division",
                featureidkey="properties.division", color="registered",
                color_continuous_scale=[[0, "#eaf6ef"], [0.5, GREEN_LIGHT], [1, "#14663a"]],
                hover_name="division")
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=0, b=0),
                              coloraxis_colorbar=dict(title="Registered"))
            st.plotly_chart(fig, width='stretch')
        else:
            st.bar_chart(bydiv.set_index("division")["registered"])
    with tcol:
        disp = bydiv.copy()
        _girls_pct_lbl = "মেয়ে %" if is_bangla() else "Girls %"
        disp["Girls %"] = (disp["girls"] / disp["registered"] * 100).round(0).astype(int).astype(str) + "%"
        if is_bangla():
            disp = disp.rename(columns={"division": "বিভাগ", "registered": "নিবন্ধিত",
                                        "boys": "ছেলে", "girls": "মেয়ে",
                                        "Girls %": _girls_pct_lbl})
            st.dataframe(disp[["বিভাগ", "নিবন্ধিত", "ছেলে", "মেয়ে", _girls_pct_lbl]],
                        width='stretch', hide_index=True, height=340)
        else:
            disp = disp.rename(columns={"division": "Division", "registered": "Registered",
                                        "boys": "Boys", "girls": "Girls"})
            st.dataframe(disp[["Division", "Registered", "Boys", "Girls", "Girls %"]],
                        width='stretch', hide_index=True, height=340)

    st.caption(tot["source_note"])


# --------------------------------------------------------------------------- #
#  PAGE — STIPEND PROGRAM (Notun Kuri stars — payment monitoring)             #
# --------------------------------------------------------------------------- #
STIPEND_STATUS_COLORS = {
    "Paid": GREEN, "Pending": GOLD, "Failed": "#c0563b",
    "Held": MUTED,
}


def page_stipend():
    import dataset as _ds
    prog = _ds.get_stipend_program()
    stars, pay = prog["stars"], prog["payments"]

    _flag_title = t("page_stipend_title")
    _flag_sub = t("page_stipend_sub")
    st.markdown(
        "<div class='gov-header' style='background:linear-gradient(120deg,"
        f"{GOLD} 0%, #a97f2e 55%, {NAVY} 130%)'>"
        "<div class='gh-row'><div style='font-size:2.4rem'>💳</div>"
        f"<div><h1>{_flag_title}</h1>"
        f"<div class='sub'>{_flag_sub}</div>"
        "<div class='flag'></div></div></div></div>", unsafe_allow_html=True)

    if is_bangla():
        st.info(
            f"💡 এটি একটি **পর্যবেক্ষণ ও প্রদর্শনী ব্যবস্থা** — পরিসংখ্যানগুলো "
            f"উদাহরণস্বরূপ (নমুনা উপবৃত্তি: **৳{_ds.STIPEND_AMOUNT:,}/মাস**, "
            f"মন্ত্রণালয় কর্তৃক নিশ্চিত পরিমাণ নয়)। এখানে কোনো প্রকৃত অর্থপ্রদান হয় না। "
            f"নিচের **অর্থপ্রদান প্রক্রিয়া** কর্মপ্রবাহটি প্রদর্শন করে; "
            f"প্রকৃত বিতরণের জন্য মন্ত্রণালয়ের মার্চেন্ট ক্রেডেনশিয়ালসহ একটি লাইসেন্সপ্রাপ্ত "
            f"গেটওয়ে ইন্টিগ্রেশন প্রয়োজন (যেমন SSLCommerz)।"
        )
    else:
        st.info(
            f"💡 This is a **monitoring &amp; demonstration system** — figures are "
            f"illustrative (placeholder stipend: **৳{_ds.STIPEND_AMOUNT:,}/month**, "
            f"not a ministry-confirmed amount). No real payment is processed here. "
            f"The **Process Payment** flow below demonstrates the intended workflow; "
            f"real disbursement requires a licensed gateway integration "
            f"(e.g. SSLCommerz) with the ministry's merchant credentials."
        )

    # ---- Headline KPIs -----------------------------------------------------
    latest_month = pay["month"].max()
    this_month = pay[pay["month"] == latest_month]
    paid_this_month = this_month[this_month["status"] == "Paid"]
    pending_n = (this_month["status"] == "Pending").sum()
    failed_n = (this_month["status"] == "Failed").sum()
    held_n = (this_month["status"] == "Held").sum()
    total_disbursed_all_time = pay[pay["status"] == "Paid"]["amount"].sum()
    active_stars = (stars["status"] == "Active").sum()

    tiles = [
        ("⭐", f"{len(stars):,}", t("kpi_selected_stars"), (NAVY, NAVY_DARK)),
        ("✅", f"{active_stars:,}", t("kpi_active_month"), (GREEN, "#14663a")),
        ("💰", f"৳{paid_this_month['amount'].sum():,.0f}", t("kpi_disbursed_month"), (GOLD, "#a97f2e")),
        ("📊", f"৳{total_disbursed_all_time:,.0f}", t("kpi_disbursed_total"), (NAVY, GREEN)),
    ]
    cols = st.columns(4)
    for col, (icon, val, label, (c1, c2)) in zip(cols, tiles):
        col.markdown(
            f"<div class='glance' style='min-height:120px;"
            f"background:linear-gradient(135deg,{c1},{c2})'>"
            f"<div class='gi'>{icon}</div>"
            f"<div><div class='gv'>{val}</div><div class='gl'>{label}</div></div></div>",
            unsafe_allow_html=True)

    st.write("")
    c1, c2, c3, c4 = st.columns(4)
    _of_due = f"{len(this_month)} " + ("বাকি আছে" if is_bangla() else "due")
    kpi(c1, t("kpi_paid_month"), f"{len(paid_this_month)}", f"{'মোট ' if is_bangla() else 'of '}{_of_due}", cls="green")
    kpi(c2, t("kpi_pending"), f"{pending_n}",
        "নিশ্চিতকরণের অপেক্ষায়" if is_bangla() else "awaiting confirmation", cls="gold")
    kpi(c3, t("kpi_failed"), f"{failed_n}",
        "পুনরায় চেষ্টা প্রয়োজন" if is_bangla() else "needs retry", cls="")
    kpi(c4, t("kpi_on_hold"), f"{held_n}",
        "নিবন্ধন স্থগিত" if is_bangla() else "enrollment paused", cls="")

    st.write("")
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown(f"<div class='section-title'>{_stt('Monthly disbursement trend')}</div>",
                    unsafe_allow_html=True)
        trend = (pay[pay["status"] == "Paid"].groupby("month")["amount"]
                .sum().reset_index())
        _disb_label = "বিতরণকৃত (টাকা)" if is_bangla() else "Disbursed (BDT)"
        fig = px.bar(trend, x="month", y="amount", text="amount",
                     labels={"month": "", "amount": _disb_label})
        fig.update_traces(marker_color=GOLD, texttemplate="৳%{text:,.0f}",
                          textposition="outside")
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=6, b=0))
        st.plotly_chart(fig, width='stretch')
    with right:
        _tms = _stt("This month's status")
        st.markdown(f"<div class='section-title'>{_tms}</div>",
                    unsafe_allow_html=True)
        status_counts = (this_month["status"].value_counts()
                        .rename_axis("Status").reset_index(name="Count"))
        fig = px.pie(status_counts, names="Status", values="Count", hole=0.58,
                     color="Status", color_discrete_map=STIPEND_STATUS_COLORS)
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=6, b=0),
                          legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig, width='stretch')

    l2, r2 = st.columns(2)
    with l2:
        st.markdown(f"<div class='section-title'>{_stt('Stars by division')}</div>",
                    unsafe_allow_html=True)
        by_div = (stars["division"].value_counts()
                 .rename_axis("Division").reset_index(name="Stars")
                 .sort_values("Stars"))
        fig = px.bar(by_div, x="Stars", y="Division", orientation="h",
                     color="Stars", color_continuous_scale=[[0, "#fdf3dc"], [1, GOLD]])
        fig.update_layout(height=320, margin=dict(l=0, r=10, t=6, b=0),
                          coloraxis_showscale=False)
        st.plotly_chart(fig, width='stretch')
    with r2:
        st.markdown(f"<div class='section-title'>{_stt('Stars by disbursement method')}</div>",
                    unsafe_allow_html=True)
        by_method = (stars["disbursement_method"].value_counts()
                    .rename_axis("Method").reset_index(name="Stars"))
        fig = px.pie(by_method, names="Method", values="Stars", hole=0.5,
                     color_discrete_sequence=[NAVY, GREEN, GOLD])
        fig.update_layout(height=320, margin=dict(l=0, r=0, t=6, b=0),
                          legend=dict(orientation="h", y=-0.12))
        st.plotly_chart(fig, width='stretch')

    # ---- Payment register ---------------------------------------------------
    st.markdown(f"<div class='section-title'>{_stt('Payment register — this month')}</div>",
                unsafe_allow_html=True)
    q1, q2, q3 = st.columns([1.6, 1, 1])
    search = q1.text_input(t("search_star"), placeholder=("নাম, আইডি, বিভাগ…" if is_bangla() else "name, ID, division…"),
                           key="stipend_search")
    status_sel = q2.multiselect(t("col_status"),
                                [t("status_paid"), t("status_pending"), t("kpi_failed"), t("status_held")],
                                key="stipend_status")
    div_sel = q3.multiselect(t("col_division"), sorted(stars["division"].unique()),
                             key="stipend_div")

    # Map translated status picks back to the internal English values.
    _status_bn_to_en = {t("status_paid"): "Paid", t("status_pending"): "Pending",
                        t("kpi_failed"): "Failed", t("status_held"): "Held"}
    status_sel = [_status_bn_to_en.get(s, s) for s in status_sel]

    reg = this_month.merge(stars[["star_id", "name", "division", "sport",
                                  "disbursement_method"]], on="star_id", how="left")
    if search:
        s = search.strip().lower()
        hay = (reg["name"].fillna("") + " " + reg["star_id"].fillna("")
               + " " + reg["division"].fillna("")).str.lower()
        reg = reg[hay.str.contains(s, regex=False)]
    if status_sel:
        reg = reg[reg["status"].isin(status_sel)]
    if div_sel:
        reg = reg[reg["division"].isin(div_sel)]

    _shown_caption = (f"{len(this_month):,} জনের মধ্যে {len(reg):,} জন তারকা দেখানো হচ্ছে"
                      if is_bangla() else f"{len(reg):,} of {len(this_month):,} stars shown")
    st.caption(_shown_caption)
    disp = reg[["star_id", "name", "division", "sport", "amount", "method",
               "status", "payment_date", "transaction_ref"]].copy()
    disp["payment_date"] = pd.to_datetime(disp["payment_date"]).dt.strftime("%d %b %Y")
    disp["payment_date"] = disp["payment_date"].fillna("—")
    disp = disp.rename(columns={"star_id": "Star ID", "name": "Name",
                                "division": "Division", "sport": "Sport",
                                "amount": "Amount (BDT)", "method": "Method",
                                "status": "Status", "payment_date": "Paid On",
                                "transaction_ref": "Transaction Ref"})

    def _status_tone(r):
        color = STIPEND_STATUS_COLORS.get(r["Status"], MUTED)
        return [f"background-color:{color}22" if c == "Status" else ""
               for c in r.index]

    styled = (disp.style
              .apply(_status_tone, axis=1)
              .format({"Amount (BDT)": "৳{:,.0f}"}))
    if is_bangla():
        col_cfg = {
            "Star ID": "তারকা আইডি", "Name": "নাম", "Division": "বিভাগ",
            "Sport": "খেলা", "Amount (BDT)": "পরিমাণ (৳)", "Method": "পদ্ধতি",
            "Status": "অবস্থা", "Paid On": "পরিশোধের তারিখ", "Transaction Ref": "লেনদেন নম্বর",
        }
        st.dataframe(styled, width='stretch', height=min(480, 70 + 35 * len(disp)),
                    hide_index=True, column_config={k: st.column_config.Column(v)
                                                    for k, v in col_cfg.items()})
    else:
        st.dataframe(styled, width='stretch', height=min(480, 70 + 35 * len(disp)),
                     hide_index=True)
    st.download_button(
        "⬇️ নিবন্ধন ডাউনলোড করুন (CSV)" if is_bangla() else "⬇️ Download this register (CSV)",
        disp.to_csv(index=False).encode("utf-8"),
        file_name=f"stipend_register_{pd.Timestamp(latest_month).strftime('%Y_%m')}.csv",
        mime="text/csv",
    )

    # ---- Process Payment demonstration flow ---------------------------------
    st.write("")
    _pp_title = "অর্থপ্রদান প্রক্রিয়া" if is_bangla() else "Process payment"
    _pp_sub = "(প্রদর্শনী কর্মপ্রবাহ)" if is_bangla() else "(demonstration workflow)"
    st.markdown(f"<div class='section-title'>{_pp_title} "
               f"<span style='font-size:.7rem;color:#5a6b7b'>"
               f"{_pp_sub}</span></div>", unsafe_allow_html=True)
    unpaid = this_month[this_month["status"].isin(["Pending", "Failed"])].merge(
        stars[["star_id", "name", "division"]], on="star_id", how="left")

    if unpaid.empty:
        st.success("✅ এই চক্রের জন্য সকল তারকার অর্থপ্রদান সম্পন্ন। কোনো পদক্ষেপ প্রয়োজন নেই।"
                   if is_bangla() else
                   "✅ All stars are paid for this cycle. No action needed.")
    else:
        options = (unpaid["name"] + "  ·  " + unpaid["star_id"]
                  + "  ·  " + unpaid["division"]).tolist()
        _select_label = (f"প্রক্রিয়াকরণের জন্য একটি তারকা নির্বাচন করুন ({len(unpaid)} জন অর্থপ্রদানের অপেক্ষায়)"
                         if is_bangla() else
                         f"Select a star to process ({len(unpaid)} awaiting payment)")
        pick = st.selectbox(_select_label, options, key="stipend_process_pick")
        picked_id = pick.split("·")[1].strip()
        picked_row = unpaid[unpaid["star_id"] == picked_id].iloc[0]
        _status_display = t({"Pending": "status_pending", "Failed": "kpi_failed"}
                            .get(picked_row["status"], "status_pending"))

        pc1, pc2 = st.columns([1, 1.4])
        with pc1:
            if is_bangla():
                st.markdown(
                    f"<div class='profile'>"
                    f"<div class='metric-row'><span class='k'>তারকা</span>"
                    f"<span class='v'>{picked_row['name']}</span></div>"
                    f"<div class='metric-row'><span class='k'>বিভাগ</span>"
                    f"<span class='v'>{picked_row['division']}</span></div>"
                    f"<div class='metric-row'><span class='k'>পরিমাণ</span>"
                    f"<span class='v'>৳{picked_row['amount']:,.0f}</span></div>"
                    f"<div class='metric-row'><span class='k'>পদ্ধতি</span>"
                    f"<span class='v'>{picked_row['method']}</span></div>"
                    f"<div class='metric-row'><span class='k'>বর্তমান অবস্থা</span>"
                    f"<span class='v' style='color:{STIPEND_STATUS_COLORS.get(picked_row['status'], MUTED)}'>"
                    f"● {_status_display}</span></div></div>",
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div class='profile'>"
                    f"<div class='metric-row'><span class='k'>Star</span>"
                    f"<span class='v'>{picked_row['name']}</span></div>"
                    f"<div class='metric-row'><span class='k'>Division</span>"
                    f"<span class='v'>{picked_row['division']}</span></div>"
                    f"<div class='metric-row'><span class='k'>Amount</span>"
                    f"<span class='v'>৳{picked_row['amount']:,.0f}</span></div>"
                    f"<div class='metric-row'><span class='k'>Method</span>"
                    f"<span class='v'>{picked_row['method']}</span></div>"
                    f"<div class='metric-row'><span class='k'>Current status</span>"
                    f"<span class='v' style='color:{STIPEND_STATUS_COLORS.get(picked_row['status'], MUTED)}'>"
                    f"● {picked_row['status']}</span></div></div>",
                    unsafe_allow_html=True)
        with pc2:
            if is_bangla():
                st.markdown(
                    f"<div class='profile'>"
                    f"<div style='font-weight:700;color:{NAVY};margin-bottom:8px'>"
                    f"গেটওয়ে ইন্টিগ্রেশন পয়েন্ট</div>"
                    f"<div style='color:{MUTED};font-size:.9rem;line-height:1.5'>"
                    f"এই বাটনটি প্রদর্শন করে যে কোথায় একটি প্রকৃত পেমেন্ট গেটওয়ে "
                    f"(যেমন <b>SSLCommerz</b>) মন্ত্রণালয়ের মার্চেন্ট ক্রেডেনশিয়ালসহ "
                    f"{picked_row['method']} এর মাধ্যমে বিতরণ করতে ব্যবহৃত হবে। "
                    f"এই প্রদর্শনীতে কোনো প্রকৃত লেনদেন সংঘটিত হয় না।</div></div>",
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div class='profile'>"
                    f"<div style='font-weight:700;color:{NAVY};margin-bottom:8px'>"
                    f"Gateway integration point</div>"
                    f"<div style='color:{MUTED};font-size:.9rem;line-height:1.5'>"
                    f"This button demonstrates where a real payment gateway "
                    f"(e.g. <b>SSLCommerz</b>) would be called with the ministry's "
                    f"merchant credentials to disburse via {picked_row['method']}. "
                    f"No real transaction occurs in this demonstration.</div></div>",
                    unsafe_allow_html=True)
            _sim_label = t("simulate_disbursement", amount=f"{picked_row['amount']:,.0f}")
            if st.button(_sim_label, key="stipend_simulate_btn", type="primary"):
                if is_bangla():
                    st.success(
                        f"✅ প্রদর্শনী সম্পন্ন: ৳{picked_row['amount']:,.0f} "
                        f"{picked_row['method']} এর মাধ্যমে {picked_row['name']} কে "
                        f"পাঠানো হবে, লাইভ গেটওয়ে ইন্টিগ্রেশন সাপেক্ষে।"
                    )
                    st.caption("কোনো প্রকৃত অর্থ স্থানান্তরিত হয়নি। এটি মন্ত্রণালয়ের পর্যালোচনার "
                              "জন্য উদ্দেশ্যকৃত ব্যবহারকারী প্রবাহ নিশ্চিত করে।")
                else:
                    st.success(
                        f"✅ Demonstration complete: ৳{picked_row['amount']:,.0f} would be "
                        f"sent to {picked_row['name']} via {picked_row['method']} "
                        f"pending live gateway integration."
                    )
                    st.caption("No real funds were moved. This confirms the intended "
                              "user flow for ministry review.")

    st.caption(
        "এই পৃষ্ঠার সকল তারকা, অভিভাবক এবং অর্থপ্রদানের তথ্য কৃত্রিম প্রদর্শনী তথ্য। "
        "কোনো প্রকৃত নাবালকের আর্থিক তথ্য ব্যবহার বা প্রদর্শন করা হয় না।"
        if is_bangla() else
        "All stars, guardians, and payment details on this page are "
        "synthetic demonstration data. No real minors' financial "
        "information is used or displayed."
    )


@st.cache_data(show_spinner=False)
def _load_bd_geojson():
    import json
    p = APP_DIR / "assets" / "bd_divisions.geojson"
    if p.exists():
        return json.loads(p.read_text())
    return None


def page_glance():
    import dataset as _ds
    coaches = get_coaches(str(DATA_PATH))

    # Big headline tiles (Khelo-India-style "At a Glance").
    tiles = [
        ("👥", f"{len(df):,}", "Registered Athletes", (NAVY, NAVY_DARK)),
        ("🏆", f"{df['Sport'].nunique()}", "Sports Disciplines", (GREEN, "#14663a")),
        ("🗺️", f"{df['division'].nunique()}", "Divisions Covered", ("#1667a8", NAVY)),
        ("🎓", f"{len(coaches):,}", "Coaches & Staff", (GOLD, "#c98f2a")),
        ("💪", f"{df['fitness_rating'].astype(float).mean():.0f}", "Avg Fitness Index", (GREEN_LIGHT, GREEN)),
        ("🏅", f"{int(df['career_medals'].sum()):,}", "Career Medals (cumulative)", (NAVY, GREEN)),
    ]
    cols = st.columns(3)
    for i, (icon, val, label, (c1, c2)) in enumerate(tiles):
        cols[i % 3].markdown(
            f"<div class='glance' style='background:linear-gradient(135deg,{c1},{c2})'>"
            f"<div class='gi'>{icon}</div>"
            f"<div><div class='gv'>{val}</div><div class='gl'>{label}</div></div></div>",
            unsafe_allow_html=True)
        if i % 3 == 2 and i < len(tiles) - 1:
            st.write("")

    st.write("")
    left, right = st.columns([1, 1])

    # --- Bangladesh choropleth: athletes by division ---
    with left:
        st.markdown("<div class='section-title'>Athlete density by division "
                    "<span style='font-size:.72rem;color:#5a6b7b'>(darker = more athletes)</span>"
                    "</div>", unsafe_allow_html=True)
        geo = _load_bd_geojson()
        by_div = (df.groupby("division").size().reset_index(name="Athletes"))
        if geo:
            fig = px.choropleth(
                by_div, geojson=geo, locations="division",
                featureidkey="properties.division", color="Athletes",
                color_continuous_scale=[[0, "#e8f4ec"], [0.5, GREEN_LIGHT], [1, NAVY]],
                hover_name="division")
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(height=440, margin=dict(l=0, r=0, t=0, b=0),
                              coloraxis_colorbar=dict(title="Athletes"))
            st.plotly_chart(fig, width='stretch')
        else:
            st.bar_chart(by_div.set_index("division"))

    # --- Sunburst: Division -> Sport ---
    with right:
        st.markdown(f"<div class='section-title'>{_stt('Division → Sport composition')}</div>",
                    unsafe_allow_html=True)
        sb = df.groupby(["division", "Sport"]).size().reset_index(name="n")
        fig = px.sunburst(sb, path=["division", "Sport"], values="n",
                          color="division", color_discrete_sequence=SEQ)
        fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width='stretch')

    # --- Treemap: Sport -> Tier ---
    st.markdown(f"<div class='section-title'>{_stt('Talent pool by sport &amp; grade')}</div>",
                unsafe_allow_html=True)
    tm = df.groupby(["Sport", "tier_label"]).size().reset_index(name="n")
    fig = px.treemap(tm, path=[px.Constant("All Sports"), "Sport", "tier_label"],
                     values="n", color="Sport", color_discrete_sequence=SEQ)
    fig.update_layout(height=440, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width='stretch')

    st.caption("National Sports Analytics Platform — demonstration build. "
               "Figures are model-derived from the current dataset.")


# --------------------------------------------------------------------------- #
#  PAGE — COACH DIRECTORY                                                      #
# --------------------------------------------------------------------------- #
def page_coaches():
    import dataset as _ds
    DIVISIONS_LIST = _ds.DIVISIONS
    coaches = get_coaches(str(DATA_PATH))
    st.markdown(f"<div class='section-title'>{_stt('Coach Directory')}</div>",
                unsafe_allow_html=True)
    _coach_caption = (
        "প্রতি খেলায় ১০ জন কোচ (জাতীয় প্রধান + সহকারী + ৮ বিভাগীয়)। যাচাইকৃত জাতীয় "
        "কোচদের চিহ্নিত করা হয়েছে; পাবলিক রেকর্ড অনুপলব্ধ ক্ষেত্রে বিভাগীয় প্রোফাইল উদাহরণস্বরূপ।"
        if is_bangla() else
        "10 coaches per sport (National Head + Assistant + 8 divisional). "
        "Verified national coaches are labelled; divisional profiles are "
        "illustrative where public records are unavailable.")
    st.caption(_coach_caption)

    f1, f2, f3 = st.columns([1.4, 1, 1])
    coach_search = f1.text_input(t("coach_search"), placeholder=t("coach_search_placeholder"),
                                 key="coach_search")
    sport_sel = f2.multiselect(t("col_sport"), sorted(coaches["sport"].unique()), key="coach_sport")
    div_sel = f3.multiselect(t("filter_division"), ["National"] + DIVISIONS_LIST, key="coach_div")

    view = coaches.copy()
    if coach_search:
        s = coach_search.strip().lower()
        hay = (view["name"].fillna("") + " " + view["specialization"].fillna("")
               + " " + view["role"].fillna("")).str.lower()
        view = view[hay.str.contains(s, regex=False)]
    if sport_sel:
        view = view[view["sport"].isin(sport_sel)]
    if div_sel:
        view = view[view["division"].isin(div_sel)]

    _n_coaches_lbl = f"{len(view)} " + ("জন কোচ" if is_bangla() else "coach(es)")
    st.caption(_n_coaches_lbl)
    if view.empty:
        st.info("ফিল্টারের সাথে কোনো কোচ মেলেনি।" if is_bangla() else "No coaches match the filters.")
        return

    # National coaches first, then divisional.
    view = view.assign(_natfirst=view["division"].eq("National").map({True: 0, False: 1}))
    view = view.sort_values(["sport", "_natfirst", "division"])

    cols = st.columns(2)
    for i, (_, c) in enumerate(view.iterrows()):
        verified = c.get("data_source") == "verified"
        badge = ("<span style='background:%s;color:#fff;font-size:.66rem;font-weight:700;"
                 "padding:2px 8px;border-radius:999px'>%s</span>" % (
                     (GREEN, t("coach_verified")) if verified else (MUTED, t("coach_illustrative"))))
        if verified:
            # Real person: show only verified facts, no fabricated stats/details.
            card = (
                f"<div class='profile' style='margin-bottom:14px'>"
                f"<div style='display:flex;gap:14px;align-items:center'>"
                f"<div class='avatar'>{initials(c['name'])}</div>"
                f"<div style='flex:1'><div class='pname' style='font-size:1.1rem'>{c['name']}</div>"
                f"<div class='prole'>{c['role']} · {c['sport']}</div>"
                f"<div style='margin-top:3px'>{badge}</div></div></div>"
                f"<div style='margin-top:10px'>"
                f"<div class='metric-row'><span class='k'>{'ভূমিকা' if is_bangla() else 'Role'}</span>"
                f"<span class='v'>{c['role']}</span></div>"
                f"<div class='metric-row'><span class='k'>{t('col_sport')}</span>"
                f"<span class='v'>{c['sport']}</span></div>"
                f"<div class='metric-row'><span class='k'>{'প্রোফাইল' if is_bangla() else 'Profile'}</span>"
                f"<span class='v'>{'জাতীয় ফেডারেশন দ্বারা রক্ষণাবেক্ষিত' if is_bangla() else 'Maintained by national federation'}</span></div>"
                f"</div>"
                f"<div style='margin-top:10px;color:{MUTED};font-size:.82rem'>"
                + ("যাচাইকৃত নিয়োগ। এই প্রদর্শনী ব্যবস্থায় বিস্তারিত ব্যক্তিগত তথ্য নেই।"
                   if is_bangla() else
                   "Verified appointment. Detailed personnel data not held in this "
                   "demonstration system.") + "</div></div>"
            )
        else:
            certs = " ".join(f"<span class='chip navy'>{gt(x)}</span>" for x in (c.get("certificates") or [])[:3])
            achs = "".join(f"<div style='color:{MUTED};font-size:.85rem'>• {gt(x)}</div>"
                           for x in (c.get("achievements") or [])[:2])
            _yrs_word = "বছর" if is_bangla() else "yrs"
            _rating_word = "রেটিং" if is_bangla() else "Rating"
            _spec_lbl = "বিশেষত্ব" if is_bangla() else "Specialization"
            _lic_lbl = "লাইসেন্স" if is_bangla() else "License"
            _edu_lbl = "শিক্ষাগত যোগ্যতা" if is_bangla() else "Education"
            _cur_ath_lbl = "বর্তমান অ্যাথলিট" if is_bangla() else "Current athletes"
            _contact_lbl = "যোগাযোগ" if is_bangla() else "Contact"
            _achievements_lbl = "অর্জন" if is_bangla() else "Achievements"
            card = (
                f"<div class='profile' style='margin-bottom:14px'>"
                f"<div style='display:flex;gap:14px;align-items:center'>"
                f"<div class='avatar'>{initials(c['name'])}</div>"
                f"<div style='flex:1'><div class='pname' style='font-size:1.1rem'>{c['name']}</div>"
                f"<div class='prole'>{c['role']} · {c['sport']}</div>"
                f"<div style='margin-top:3px'>{badge}"
                f"<span class='chip green'>{c['experience_years']} {_yrs_word}</span>"
                f"<span class='chip gold'>{_rating_word} {c['performance_rating']}</span></div></div></div>"
                f"<div style='margin-top:10px'>{certs}</div>"
                f"<div style='margin-top:8px'>"
                f"<div class='metric-row'><span class='k'>{_spec_lbl}</span><span class='v'>{gt(c['specialization'])}</span></div>"
                f"<div class='metric-row'><span class='k'>{_lic_lbl}</span><span class='v'>{gt(c['license'])}</span></div>"
                f"<div class='metric-row'><span class='k'>{_edu_lbl}</span><span class='v'>{c['education']}</span></div>"
                f"<div class='metric-row'><span class='k'>{_cur_ath_lbl}</span><span class='v'>{c['current_athletes']}</span></div>"
                f"<div class='metric-row'><span class='k'>{_contact_lbl}</span><span class='v'>{c['email']}</span></div>"
                f"</div><div style='margin-top:8px'><b style='color:{NAVY};font-size:.85rem'>{_achievements_lbl}</b>{achs}</div>"
                f"</div>"
            )
        cols[i % 2].markdown(card, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
#  PAGE — RULE BOOK                                                            #
# --------------------------------------------------------------------------- #
def page_rules():
    import dataset as _ds
    st.markdown(f"<div class='section-title'>{_stt('Sport Rule Books')}</div>",
                unsafe_allow_html=True)
    st.caption("Official governing body and rulebook link for each sport. "
               "Key rules are brief orientation summaries; the official link is "
               "the authoritative source.")

    all_sports = sorted(_ds.RULEBOOK.keys())
    # Default to the sidebar-selected sport when one is chosen.
    default_idx = all_sports.index(sport_choice) if sport_choice in all_sports else 0
    sport = st.selectbox(t("choose_sport"), all_sports, index=default_idx)
    rb = _ds.get_rulebook(sport)
    if not rb:
        st.info("এই খেলার জন্য কোনো নিয়মাবলী রেকর্ডে নেই।" if is_bangla()
               else "No rulebook on record for this sport.")
        return

    rules_html = "".join(
        f"<div style='display:flex;gap:10px;margin:8px 0'>"
        f"<div style='color:{GREEN};font-weight:800'>{i+1}.</div>"
        f"<div style='color:{INK};font-size:.94rem'>{r}</div></div>"
        for i, r in enumerate(rb["rules"]))

    st.markdown(
        f"<div class='profile'>"
        f"<div style='display:flex;gap:16px;align-items:center'>"
        f"<div style='font-size:2.6rem'>📖</div>"
        f"<div><div class='pname'>{sport}</div>"
        f"<div class='prole'>{rb['body']}</div></div></div>"
        f"<div style='margin-top:10px;color:{MUTED};font-size:.95rem'>{rb['summary']}</div>"
        f"<div class='section-title' style='margin-top:16px'>{t('key_rules')}</div>{rules_html}"
        f"</div>", unsafe_allow_html=True)

    st.link_button(t("open_official", sport=sport), rb["url"])
    _source_lbl = "উৎস" if is_bangla() else "Source"
    st.caption(f"{_source_lbl}: {rb['body']} — {rb['url']}")


# --------------------------------------------------------------------------- #
#  PAGE — NEWS CENTER                                                          #
# --------------------------------------------------------------------------- #
def page_news():
    import dataset as _ds
    st.markdown(f"<div class='section-title'>{_stt('Sports News Center')}</div>",
                unsafe_allow_html=True)
    _news_caption = (
        "প্রথম আলো থেকে সংগৃহীত শিরোনাম। প্রতিটি কার্ড একটি প্রকৃত, প্রকাশিত নিবন্ধের "
        "সংক্ষিপ্তসার, উৎস ও তারিখসহ; কিছুই বানানো হয়নি।"
        if is_bangla() else
        "Headlines sourced from Prothom Alo. Each card summarises a real, "
        "published article with its source and date; nothing is fabricated.")
    st.caption(_news_caption)

    news = _ds.get_news()
    cats = sorted({n["category"] for n in news})
    prios = ["High", "Medium", "Low"]
    fc, fp = st.columns(2)
    cat_sel = fc.multiselect(t("filter_category"), cats, key="news_cat")
    pri_sel = fp.multiselect(t("filter_priority"), prios, key="news_pri")
    if cat_sel:
        news = [n for n in news if n["category"] in cat_sel]
    if pri_sel:
        news = [n for n in news if n["priority"] in pri_sel]

    pri_color = {"High": "#c0563b", "Medium": GOLD, "Low": GREEN}
    cat_grad = {
        "Governance": (NAVY, NAVY_DARK), "Development": (GREEN, "#14663a"),
        "Infrastructure": ("#1667a8", NAVY), "Youth": (GREEN_LIGHT, GREEN),
        "Football": (NAVY, GREEN), "Other": (MUTED, INK),
    }
    if not news:
        st.info("নির্বাচিত ফিল্টারের সাথে কোনো সংবাদ মেলেনি।" if is_bangla()
               else "No news matches the selected filters.")
        return

    # Two-column card grid. Images stay uncropped (object-fit:contain, full
    # picture visible) but at a smaller cap suited to a half-width column,
    # rather than the earlier full-width single-column layout.
    cols = st.columns(2)
    for i, n in enumerate(news):
        g1, g2 = cat_grad.get(n["category"], cat_grad["Other"])
        pc = pri_color.get(n["priority"], MUTED)
        date_fmt = pd.to_datetime(n["date"]).strftime("%d %b %Y")
        if n.get("image_url"):
            banner = (f"<div style='position:relative;background:#eef2f6'>"
                      f"<img src='{n['image_url']}' "
                      f"style='width:100%;height:auto;max-height:210px;"
                      f"object-fit:contain;display:block;border-radius:14px 14px 0 0' "
                      f"onerror=\"this.style.display='none';"
                      f"this.nextElementSibling.style.display='flex'\"/>"
                      f"<div style='display:none;width:100%;height:170px;"
                      f"border-radius:14px 14px 0 0;align-items:center;"
                      f"justify-content:center;color:#fff;font-weight:700;"
                      f"background:linear-gradient(135deg,{g1},{g2})'>"
                      f"{n['category']}</div></div>")
        else:
            banner = (f"<div style='width:100%;height:170px;display:flex;"
                      f"align-items:center;justify-content:center;color:#fff;"
                      f"font-weight:700;font-size:1.05rem;letter-spacing:.02em;"
                      f"border-radius:14px 14px 0 0;"
                      f"background:linear-gradient(135deg,{g1},{g2})'>"
                      f"📰 {n['category']}</div>")

        card = (
            f"<div style='background:#fff;border:1px solid #e4edf5;border-radius:14px;"
            f"overflow:hidden;box-shadow:0 3px 12px rgba(18,40,58,.07);"
            f"margin-bottom:16px;height:100%'>{banner}"
            f"<div style='padding:14px 16px'>"
            f"<div style='display:flex;gap:8px;align-items:center;margin-bottom:8px'>"
            f"<span style='background:{pc};color:#fff;font-size:.68rem;font-weight:700;"
            f"padding:2px 9px;border-radius:999px'>{n['priority'].upper()}</span>"
            f"<span style='color:{MUTED};font-size:.78rem'>{date_fmt} · {n['source']}</span>"
            f"</div>"
            f"<div style='font-weight:750;color:{INK};font-size:1.02rem;line-height:1.25;"
            f"margin-bottom:8px'>{n['headline']}</div>"
            f"<div style='color:{MUTED};font-size:.9rem;line-height:1.45;margin-bottom:10px'>"
            f"{n['summary']}</div>"
            f"<a href='{n['url']}' target='_blank' rel='noopener' "
            f"style='display:inline-block;color:{NAVY};font-weight:700;font-size:.85rem;"
            f"text-decoration:none;border:1px solid #cfe0ef;background:{BG_SOFT};"
            f"padding:5px 12px;border-radius:8px'>Read full article ↗</a>"
            f"</div></div>"
        )
        cols[i % 2].markdown(card, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
#  ROUTER                                                                      #
# --------------------------------------------------------------------------- #
PAGES = {
    "At a Glance": page_glance,
    "Notun Kuri": page_notunkuri,
    "Stipend Program": page_stipend,
    "Executive Summary": page_summary,
    "Player Profile": page_profile,
    "Performance & Fitness": page_fitness,
    "Injury & Training": page_injury,
    "Rankings & Leaderboard": page_rankings,
    "Coach Directory": page_coaches,
    "Rule Book": page_rules,
    "News Center": page_news,
}
PAGES[page]()

st.divider()
st.caption(
    "Demonstration build · Data read directly from the source workbook "
    "(unmodified). Scores are model-derived from the supplied fields; no values "
    "were fabricated. Injury severity is inferred from free-text notes via a "
    "documented keyword rubric in scoring.py."
)
