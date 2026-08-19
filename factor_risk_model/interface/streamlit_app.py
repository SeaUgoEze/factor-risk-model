"""Interactive dashboard - the user-facing face of the model.

    streamlit run factor_risk_model/interface/streamlit_app.py

Sidebar: pick tickers, window, factor model, target exposures, short
constraints.  Run -> the whole pipeline executes and the results appear
in tabs (Exposures / Optimization / Risk / Stress / Anomaly / Export).

Design notes
------------
* The data fetch is memoized with ``st.cache_data`` keyed on
  (tickers, window, model), so tweaking a slider never re-downloads
  market data - the engine's on-disk cache handles the first hit.
* Everything downstream (regressions, optimization, risk, anomaly) is
  fast enough to run on every "Run" click.
* ``run_pipeline`` is shared with the CLI, so both interfaces report
  identical numbers by construction.
"""
from __future__ import annotations

import os
import sys

# Streamlit Cloud launches this file directly, which puts only the
# script's directory on sys.path - so add the repository root (three
# levels up) to make the `factor_risk_model` and `src` packages
# importable no matter where the app is started from.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import io
from datetime import date

import pandas as pd
import streamlit as st

from factor_risk_model.config import (DEFAULT_FACTOR_MODEL, DEFAULT_TICKERS,
                                      END_DATE, EXPOSURE_LIMITS,
                                      RISK_TOLERANCE_DEFAULT,
                                      RISK_TOLERANCE_RANGE, SHORT_FLOOR,
                                      START_DATE, TARGET_DEFAULTS,
                                      TICKER_NAMES)
from factor_risk_model.data.data_fetcher import CURATED, fetch_app_data
from factor_risk_model.pipeline import run_pipeline
from factor_risk_model.utils.export import export_excel, export_html, export_pdf
from factor_risk_model.utils.helpers import fmt_pct

st.set_page_config(page_title="Factor Risk Model",
                   page_icon=":material/bar_chart:", layout="wide")

st.markdown("""
<style>
 /* Monochrome "graph paper" dashboard: flat near-black canvas, hairline
    gray rules, perfectly rectangular borders (zero border-radius)
    everywhere, light gray (#F8F8F8) as the single functional accent.
    Pure grayscale palette extracted from the reference. */
 @import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@300;400;500&display=swap');

 :root { --gp-bg:#101018; --gp-panel:#181820; --gp-raised:#282830;
         --gp-line:#202028; --gp-rule:rgba(248,248,248,.10);
         --gp-ink:#F8F8F8; --gp-muted:#8A8A92; --gp-faint:#626262; }

 .block-container { padding-top: 1.8rem; padding-bottom: 72px; }

 /* flat near-black canvas - no gradients, no glows */
 [data-testid="stAppViewContainer"] {
   background: var(--gp-bg) !important; }

 /* Geist everywhere; tight, bold headings. The framework's bundled CSS sets
    its own font on content containers, so force it at the app root. */
 [data-testid="stAppViewContainer"] *,
 [data-testid="stAppViewContainer"] {
   font-family: 'Geist', 'Helvetica Neue', Arial, sans-serif !important; }
 /* Material icon spans carry their font inline - keep the ligature font
    so :material/ icons render as icons, not literal text. */
 [style*="Material Symbols"] {
   font-family: "Material Symbols Rounded" !important; }
 /* Some icon components (expander chevrons, sidebar collapse/expand
    arrows) apply the icon font via emotion classes with no inline style
    - the universal override above would otherwise degrade them to
    literal text, so re-apply the icon font AND the ligature feature
    (Material Symbols draws its glyphs via ligatures: without 'liga'
    the span renders the raw icon-name string instead of the glyph). */
 [data-testid="stExpander"] span,
 [data-testid="stSidebarCollapseButton"] span,
 [data-testid="stExpandSidebarButton"] span,
 [data-testid="stBaseButton-headerNoPadding"] span {
   font-family: "Material Symbols Rounded" !important;
   font-feature-settings: "liga" !important;
   -webkit-font-feature-settings: "liga" !important;
   -moz-font-feature-settings: "liga" !important; }
 [data-testid="stAppViewContainer"] h1 {
   font-family: 'Times New Roman', Times, Georgia, serif !important;
   font-weight: 700; letter-spacing: -0.01em;
   color: var(--gp-ink) !important; }
 h2, h3 { font-family: 'Geist', 'Helvetica Neue', Arial, sans-serif
   !important; letter-spacing: -0.02em; color: var(--gp-ink) !important; }
 h1 { font-size: clamp(2.1rem, 4.2vw, 3.1rem);
      line-height: 1.05; }
 code, pre, [data-testid="stMetricLabel"], .frm-footer span,
 [class*="mono"] {
   font-family: 'Geist Mono', monospace !important; }
 .stCaption, [data-testid="stCaptionContainer"] { color: var(--gp-muted); }

 /* rectangular metric cards - flat raised panel, hairline rule, no
    rounding, no shadow */
 [data-testid="stMetric"] { background: var(--gp-panel);
   border: 1px solid var(--gp-raised); border-radius: 0;
   padding: 12px 16px; }
 [data-testid="stMetricLabel"] { color: var(--gp-muted);
   font-size: 10.5px; letter-spacing: .10em; text-transform: uppercase; }
 [data-testid="stMetricValue"] { color: var(--gp-ink);
   font-weight: 600; font-size: 1.45rem; }
 [data-testid="stMetricDelta"] { color: var(--gp-muted); }

 /* rectangular tabs - selected tab is a solid light-gray block
    (this Streamlit version renders tabs with role="tab" semantics) */
 .stTabs [role="tablist"] { gap: 0; }
 .stTabs [role="tab"] { background: transparent;
   color: var(--gp-muted); border-radius: 0; padding: 8px 16px;
   border: 1px solid transparent; }
 .stTabs [role="tab"]:hover { color: var(--gp-ink); }
 .stTabs [role="tab"][aria-selected="true"] {
   background: var(--gp-ink); color: var(--gp-bg) !important;
   font-weight: 600; border-color: var(--gp-ink); }

 /* flat sidebar panel with a hairline rule */
 [data-testid="stSidebar"] {
   background: var(--gp-panel);
   border-right: 1px solid var(--gp-raised); }

 /* primary (Run) button - solid light-gray block, dark label. The
    testid sits on the <button> itself in this Streamlit version. */
 [data-testid="stBaseButton-primary"] {
   background: var(--gp-ink) !important;
   color: var(--gp-bg) !important; font-weight: 600;
   border: 1px solid var(--gp-ink) !important;
   border-radius: 0 !important; }
 [data-testid="stBaseButton-primary"]:hover {
   background: #E8E8E8 !important; border-color: #E8E8E8 !important;
   color: var(--gp-bg) !important; }

 /* Framework default chrome that does not belong on a public demo:
    the header Deploy button (a cloud launcher) and the
    "Made with" attribution footer inside the main-menu
    popover (the block that follows the menu list). The menu itself
    keeps Rerun / Settings / Print. */
 [data-testid="stAppDeployButton"] { display: none !important; }
 [data-testid="stMainMenuPopover"] [data-testid="stMainMenuList"] + * {
   display: none !important; }

 /* ticker chips: flat panel with a raised rule, sharp corners. The chip
    body is the span that directly contains the remove button (React
    Aria tag markup), so :has() reaches it without depending on hashed
    emotion classes. */
 [data-testid="stMultiSelect"] span:has(> [aria-label^="Remove"]) {
   background: var(--gp-panel) !important;
   border: 1px solid var(--gp-raised) !important;
   border-radius: 0 !important;
   color: var(--gp-ink) !important; }
 [data-testid="stMultiSelect"] span:has(> [aria-label^="Remove"]) > span,
 [data-testid="stMultiSelect"] [aria-label^="Remove"] {
   color: var(--gp-ink) !important; }
 [data-testid="stMultiSelect"] [aria-label^="Remove"]:hover {
   background: var(--gp-raised) !important; }

 /* hard-edged input shells - the framework rounds the date picker,
    text input and multiselect control to 8px; zero them so every
    input matches the rectangular ticker chips. Colors untouched. */
 [data-testid="stTextInputRootElement"] { border-radius: 0 !important; }
 [data-testid="stDateInput"] [data-baseweb="input"] {
   border-radius: 0 !important; }
 [data-testid="stMultiSelect"] [role="group"] {
   border-radius: 0 !important; }
 [data-testid="stMultiSelect"] [aria-label="Clear all"] {
   border-radius: 0 !important; }

 /* framework alert boxes (info/warning/success/error) carry light-theme
    tints - neutralize them into the same flat panel + ink text as
    everything else; the icon keeps the neutral light gray. */
 [data-testid="stAlert"] { background: var(--gp-panel) !important;
   border: 1px solid var(--gp-raised) !important; border-radius: 0;
   color: var(--gp-ink) !important; }
 [data-testid="stAlertContainer"] { background: transparent !important; }
 [data-testid="stAlert"] p, [data-testid="stAlert"] div,
 [data-testid="stAlert"] span { color: var(--gp-ink) !important; }
 [data-testid="stAlert"] svg { color: var(--gp-muted) !important; }

 /* Chart figures fade up as they mount after a run - a single, subtle
    reveal that stops the results block from teleporting in.  Pure CSS
    @starting-style (mount-only, no JS state): unsupported engines just
    show the image instantly, so there is no stuck-invisible risk.
    transform + opacity only; strong ease-out, 300ms. */
 [data-testid="stImageContainer"] img {
   transition: opacity .3s cubic-bezier(0.23, 1, 0.32, 1),
               transform .3s cubic-bezier(0.23, 1, 0.32, 1); }
 @starting-style {
   [data-testid="stImageContainer"] img {
     opacity: 0; transform: translateY(8px); } }
 @media (prefers-reduced-motion: reduce) {
   [data-testid="stImageContainer"] img {
     transition: opacity .2s ease; transform: none; } }

 /* Metric cards fade up with the figures so the whole results block
    arrives as one system - same recipe as the figure entrance:
    @starting-style mount-only, strong ease-out, 300ms, with a 40ms
    cascade across the four cards.  The :has() guard keeps the stagger
    off other column rows (tables, export buttons). */
 [data-testid="stMetric"] {
   transition: opacity .3s cubic-bezier(0.23, 1, 0.32, 1),
               transform .3s cubic-bezier(0.23, 1, 0.32, 1); }
 @starting-style {
   [data-testid="stMetric"] {
     opacity: 0; transform: translateY(8px); } }
 @media (prefers-reduced-motion: no-preference) {
   [data-testid="stColumn"]:nth-of-type(2):has([data-testid="stMetric"])
     [data-testid="stMetric"] { transition-delay: .04s; }
   [data-testid="stColumn"]:nth-of-type(3):has([data-testid="stMetric"])
     [data-testid="stMetric"] { transition-delay: .08s; }
   [data-testid="stColumn"]:nth-of-type(4):has([data-testid="stMetric"])
     [data-testid="stMetric"] { transition-delay: .12s; } }
 @media (prefers-reduced-motion: reduce) {
   [data-testid="stMetric"] {
     transition: opacity .2s ease; transform: none; transition-delay: 0s; } }

 /* Run button press feedback - a 2% settle on :active so the click that
    starts the pipeline feels acknowledged.  Fast and subtle: 160ms strong
    ease-out.  The transform channel is new; the background channel keeps
    the framework's hover color transition alive (the emotion base sets
    transition: all, which this overrides).  :active is a press, not a
    hover, so no pointer gating is needed. */
 [data-testid="stBaseButton-primary"] {
   transition: transform 160ms cubic-bezier(0.23, 1, 0.32, 1),
               background .2s ease; }
 [data-testid="stBaseButton-primary"]:active { transform: scale(0.98); }
 @media (prefers-reduced-motion: reduce) {
   [data-testid="stBaseButton-primary"] { transition: background .2s ease; }
   [data-testid="stBaseButton-primary"]:active { transform: none; } }

 /* Info box (and post-run warning banners) fade in on mount - an
    opacity-only 200ms strong ease-out so the first screen composes
    with the empty-state graph instead of snapping.  st.info and
    st.warning share the stAlert testid; both mount occasionally and
    the fade is uniform.  Opacity-only, so reduced motion keeps it
    as-is (aids comprehension, no movement). */
 [data-testid="stAlert"] {
   transition: opacity .2s cubic-bezier(0.23, 1, 0.32, 1); }
 @starting-style {
   [data-testid="stAlert"] { opacity: 0; } }
</style>""", unsafe_allow_html=True)

# Footer - privacy line pinned to the bottom of the viewport, emitted
# before any st.stop() so it is visible in every state.
st.markdown("""
<style>
 .frm-footer { position: fixed; left: 0; right: 0; bottom: 0; z-index: 999;
   background: #101018; border-top: 1px solid #282830;
   padding: 9px 0; text-align: center; }
 .frm-footer span { font-size: 12px; color: #8A8A92;
   font-family: "Geist Mono", monospace; letter-spacing: .02em; }
</style>
<div class="frm-footer"><span>© 2026 Sean Ezeocha · Factor Risk Model · runs
 fully locally · data: Yahoo Finance &amp; Kenneth French Data Library</span></div>
""", unsafe_allow_html=True)

# Back-to-top floating button.  A component iframe (scripts run inside
# it; they do NOT run inside st.markdown) is pinned via parent CSS to
# the bottom-right, just above the footer bar.  Its script watches the
# parent's scroll container (capture-phase scroll listener survives
# framework re-renders) and reveals the button once the user scrolls
# past the header, with smooth scroll-to-top on click.
st.markdown("""
<style>
 iframe[title="st.iframe"] { position: fixed; right: 20px; bottom: 52px;
   width: 48px !important; height: 48px !important; z-index: 997;
   border: 0; opacity: 0; visibility: hidden; pointer-events: none;
   transition: opacity .25s ease, visibility .25s ease; }
 iframe[title="st.iframe"].frm-btt-show {
   opacity: 1; visibility: visible; pointer-events: auto; }
</style>""", unsafe_allow_html=True)

st.iframe(
    """
<style>
  html, body { margin: 0; height: 100%; }
  #frm-btt { position: absolute; inset: 0; width: 100%; height: 100%;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; border: none; border-radius: 0;
    background: #181820;
    color: #F8F8F8;
    box-shadow: 0 0 0 1px #282830;
    transform: translateY(12px);
    transition: transform .25s ease, background .2s ease; }
  #frm-btt.show { transform: translateY(0); }
  @media (hover: hover) and (pointer: fine) {
    #frm-btt:hover { transform: translateY(-2px);
      background: #282830; } }
  #frm-btt svg { width: 20px; height: 20px; }
</style>
<button id="frm-btt" aria-label="Back to top" title="Back to top">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
       aria-hidden="true">
    <path d="M12 19V5"/><path d="m5 12 7-7 7 7"/>
  </svg>
</button>
<script>
  (function () {
    var parent = window.parent, doc = parent.document;
    var frame = window.frameElement;
    var btn = document.getElementById('frm-btt');
    if (!frame || !btn) return;

    // Re-query every call: the framework replaces DOM nodes on reruns, so a
    // cached array can point at detached elements and silently break the
    // reveal (querySelector is trivially cheap per scroll event).
    function scrollers() {
      return [
        doc.querySelector('[data-testid="stAppViewContainer"]'),
        doc.querySelector('[data-testid="stMainBlockContainer"]'),
        doc.querySelector('[data-testid="stMain"]')
      ].filter(Boolean);
    }

    function topNow() {
      var t = parent.scrollY || 0;
      scrollers().forEach(function (s) {
        if (s.scrollTop > t) t = s.scrollTop;
      });
      return t;
    }

    function update() {
      var show = topNow() > 160;
      frame.classList.toggle('frm-btt-show', show);
      btn.classList.toggle('show', show);
    }

    function goTop() {
      var sc = scrollers(), start = topNow();
      sc.forEach(function (s) {
        s.scrollTo({ top: 0, behavior: 'smooth' });
      });
      parent.scrollTo({ top: 0, behavior: 'smooth' });
      // Fallback: some embedded webviews never run smooth-scroll
      // animations (no compositor ticks). If nothing moved shortly
      // after, snap to the top so the button always works.
      setTimeout(function () {
        if (start > 0 && topNow() >= start) {
          sc.forEach(function (s) { s.scrollTop = 0; });
          parent.scrollTo(0, 0);
          update();
        }
      }, 700);
    }

    doc.addEventListener('scroll', update, true);
    window.addEventListener('resize', update);
    btn.addEventListener('click', goTop);
    update();
  })();
</script>
""",
    height="content",
)

# Empty-state graph - a self-drawing equity curve shown under the
# "Run analysis" hint before the pipeline has run.  One-shot CSS animation
# on an inline SVG, built from the monochrome tokens.  It only renders in
# the pre-run branch, so it plays at most once per session.
_EMPTY_STATE_GRAPH = """
<style>
 .frm-empty-graph { display: block; width: 100%; max-width: 620px;
   height: auto; margin: 1.25rem auto 0.25rem; }
 .frm-empty-graph .axis { stroke: var(--gp-raised); }
 .frm-empty-graph .grid { stroke: var(--gp-line); stroke-dasharray: 2 7; }
 .frm-empty-graph .axis, .frm-empty-graph .grid { opacity: 0;
   animation: frm-fade .35s cubic-bezier(0.23, 1, 0.32, 1) .1s forwards; }
 .frm-empty-graph .curve {
   fill: none; stroke: var(--gp-ink); stroke-width: 2.5;
   stroke-linecap: round; stroke-linejoin: round;
   stroke-dasharray: 100; stroke-dashoffset: 100;
   filter: url(#frm-glow);
   animation: frm-draw 1.8s cubic-bezier(0.77, 0, 0.175, 1) .35s forwards; }
 .frm-empty-graph .end-dot { fill: var(--gp-ink);
   opacity: 0; transform-box: fill-box; transform-origin: center;
   animation: frm-pop .35s cubic-bezier(0.23, 1, 0.32, 1) 2.2s forwards; }
 @keyframes frm-draw { to { stroke-dashoffset: 0; } }
 @keyframes frm-fade { to { opacity: 1; } }
 @keyframes frm-pop { from { opacity: 0; transform: scale(.9); }
   to { opacity: 1; transform: scale(1); } }
 @media (prefers-reduced-motion: reduce) {
   .frm-empty-graph .axis, .frm-empty-graph .grid,
   .frm-empty-graph .curve, .frm-empty-graph .end-dot {
     opacity: 1; animation: none; }
   .frm-empty-graph .curve { stroke-dashoffset: 0; } }
</style>
<div class="frm-empty-graph" role="img"
     aria-label="Animated factor return curve">
  <svg viewBox="0 0 900 240" preserveAspectRatio="xMidYMid meet">
    <defs>
      <filter id="frm-glow" x="-60%" y="-60%" width="220%" height="220%">
        <feGaussianBlur stdDeviation="3" result="blur"/>
        <feMerge>
          <feMergeNode in="blur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    <g class="grid">
      <line x1="150" y1="35" x2="150" y2="205"/>
      <line x1="300" y1="35" x2="300" y2="205"/>
      <line x1="450" y1="35" x2="450" y2="205"/>
      <line x1="600" y1="35" x2="600" y2="205"/>
      <line x1="750" y1="35" x2="750" y2="205"/>
      <line x1="40" y1="60" x2="860" y2="60"/>
      <line x1="40" y1="100" x2="860" y2="100"/>
      <line x1="40" y1="140" x2="860" y2="140"/>
      <line x1="40" y1="180" x2="860" y2="180"/>
    </g>
    <g class="axis">
      <line x1="40" y1="205" x2="862" y2="205"/>
      <line x1="40" y1="205" x2="40" y2="35"/>
    </g>
    <path class="curve" pathLength="100"
      d="M40 192 C72 176 104 140 130 120 C150 105 168 134 180 148
         C192 161 208 145 225 143 C242 141 250 151 265 146
         C283 141 290 160 305 162 C322 165 330 142 345 134
         C362 125 372 148 385 150 C405 154 428 176 455 186
         C484 197 494 158 515 140 C536 121 546 170 560 178
         C577 187 590 128 625 108 C646 96 656 120 670 118
         C689 115 697 100 715 92 C735 82 742 100 755 100
         C772 100 778 84 795 76 C812 68 820 86 830 84
         C846 81 851 66 862 58"/>
    <circle class="end-dot" cx="862" cy="58" r="4"/>
  </svg>
</div>
"""

# Cached data layer
@st.cache_data(show_spinner="Fetching / aligning market data (cached)...")
def _load(tickers, start, end, model):
    return fetch_app_data(list(tickers), start, end, model)


# Sidebar - all user inputs
with st.sidebar:
    st.header(":material/tune: Configuration")
    st.caption("Every control maps to a parameter in "
               "`factor_risk_model/config.py`.")

    def label(t: str) -> str:
        """Dropdown label: 'AAPL - Apple'; unknown tickers show bare."""
        name = TICKER_NAMES.get(t)
        return f"{t} - {name}" if name else t

    stocks = st.multiselect(
        "Stocks", CURATED, default=DEFAULT_TICKERS,
        format_func=label,
        help="The curated 26-stock universe. Add custom tickers below.")
    extra = st.text_input(
        "Extra tickers (comma separated)", "",
        help="Any US-listed symbol works, e.g. TSLA, GOOGL, COST.")
    if extra.strip():
        stocks += [t.strip().upper() for t in extra.split(",")
                   if t.strip() and t.strip().upper() not in stocks]

    start_d = st.date_input(
        "Start date", date.fromisoformat(START_DATE),
        min_value=date(1990, 1, 1),
        max_value=date.today(),
        help="Pick a start from the calendar. Keep at least 24 months of "
             "overlap with the factor library.")
    end_d = st.date_input(
        "End date", date.fromisoformat(END_DATE),
        min_value=start_d,
        max_value=date.today(),
        help="Pick an end from the calendar. The Fama-French library "
             "updates monthly, so the last 1-2 months may be trimmed.")
    start = start_d.isoformat()   # 'YYYY-MM-DD' for the pipeline
    end = end_d.isoformat()

    model = st.radio("Factor model", ["5-factor", "3-factor"],
                     index=0 if DEFAULT_FACTOR_MODEL == "5-factor" else 1,
                     horizontal=True,
                     help="3-factor: Mkt-RF/SMB/HML. 5-factor adds "
                          "profitability (RMW) and investment (CMA).")

    chart_colour = st.radio(
        "Chart colour", ["Monochrome", "Semantic"], horizontal=True,
        index=0,
        help="Monochrome keeps every figure grayscale. Semantic adds "
             "muted green for gains/positive, red for losses/negative "
             "and amber for the benchmark - the UI chrome stays "
             "grayscale either way.")

    st.subheader(":material/track_changes: Target exposures")
    active = ["Mkt-RF", "SMB", "HML"] if model == "3-factor" else list(TARGET_DEFAULTS)
    lo, hi, step = (EXPOSURE_LIMITS["min"], EXPOSURE_LIMITS["max"],
                    EXPOSURE_LIMITS["step"])
    targets = {}
    for k in active:
        targets[k] = st.slider(
            k, lo, hi, float(TARGET_DEFAULTS.get(k, 0.0)), step,
            key=f"tgt_{k}",
            help=f"Target portfolio loading on {k}.")

    st.subheader(":material/lock_outline: Constraints")
    allow_shorts = st.checkbox("Allow short selling", value=True,
                               help="Long-only often cannot reach a "
                                    "strong value mandate (HML ~1.0).")
    short_floor = st.slider("Short floor", -0.50, 0.0, float(SHORT_FLOOR),
                            0.05, disabled=not allow_shorts,
                            help="Min weight per name when shorts are on.")
    tolerance = st.slider("Exposure tolerance", 0.02, 0.30, 0.10, 0.01,
                          help="Max |achieved - target| the optimizer may "
                               "leave per factor.")
    max_vol = st.slider(
        "Vol budget (warning)", RISK_TOLERANCE_RANGE[0],
        RISK_TOLERANCE_RANGE[1], float(RISK_TOLERANCE_DEFAULT), 0.01,
        help="Achieved vol is an OUTPUT of min-variance optimization, so "
             "this is a warning threshold, not a hard constraint.")

    run = st.button(":material/play_arrow: Run analysis", type="primary",
                    width="stretch")

# Header
st.title("Factor-Based Risk & Optimization Model")
st.caption("Interactive Fama-French factor analysis, mandate-driven portfolio "
           "optimization, risk & stress testing, and anomaly detection. "
           "Engine: `src/` · App: `factor_risk_model/`")

if not run:
    st.info("Set the configuration in the sidebar, then press **▶ Run "
            "analysis**.")
    st.markdown(_EMPTY_STATE_GRAPH, unsafe_allow_html=True)
    st.stop()

# Execute
try:
    with st.spinner("Running the pipeline (fetch → regressions → optimize "
                    "→ risk → anomaly)..."):
        app_data = _load(tuple(stocks), start, end, model)
        result = run_pipeline(stocks, start, end, factor_model=model,
                              targets=targets, tolerance=tolerance,
                              allow_shorts=allow_shorts,
                              short_floor=short_floor, max_vol=max_vol,
                              app_data=app_data,
                              chart_mode="semantic"
                              if chart_colour == "Semantic" else "mono")
except (ValueError, RuntimeError) as exc:
    st.error(f"**Unable to complete the analysis.** {exc}")
    st.stop()

st.session_state["result"] = result

# Overview + tabs
m = result.risk_summary.loc["Optimal"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Annualized return", fmt_pct(m["ann_return_%"] / 100))
c2.metric("Annualized vol", fmt_pct(m["ann_vol_%"] / 100))
c3.metric("Sharpe ratio", f"{m['sharpe']:.2f}")
c4.metric("Max drawdown", fmt_pct(m["max_drawdown_%"] / 100))

for w in result.optimization_warnings:
    st.warning(w)

st.markdown("**What this says, in plain English:**")
for b in result.interpretation():
    st.markdown(f"- {b}")

tab_exp, tab_opt, tab_risk, tab_str, tab_an, tab_out = st.tabs(
    ["Exposures", "Optimization", "Risk & performance", "Stress test",
     "Anomaly", "Export"])

# Exposures
with tab_exp:
    st.subheader("Factor exposures - beta [95% CI]")
    st.caption("Each cell shows the point estimate with its 95% confidence "
               "interval; SPY (bottom) is the sanity check - market beta "
               "near 1.0, R² near 1.")
    st.dataframe(result.exposures_pretty,
                 width="stretch", height=420)
    with st.expander("Full statistics (t-stats, p-values, residual vol)"):
        st.dataframe(result.exposures.round(3),
                     width="stretch", height=360)
    colA, colB = st.columns(2)
    with colA:
        st.image(str(result.figures["exposures"]), width="stretch")
    with colB:
        st.image(str(result.figures["ci"]), width="stretch")
    if "rolling" in result.figures:
        st.image(str(result.figures["rolling"]), width="stretch")
    with st.expander("Plain-English factor profiles"):
        st.write(pd.DataFrame({"profile": result.profiles}))

# Optimization
with tab_opt:
    st.subheader("Mandate vs achieved")
    st.dataframe(result.optimizer["comparison"].round(3),
                 width="stretch")
    st.caption(f"Total vol {result.optimizer['total_vol_ann']:.1f}% = factor "
               f"{result.optimizer['factor_vol_ann']:.1f}% + idiosyncratic "
               f"{result.optimizer['idio_vol_ann']:.1f}%. "
               f"Factor share of variance: "
               f"{result.optimizer['factor_share'] * 100:.0f}%.")
    colW, _ = st.columns([1.4, 1])
    with colW:
        st.image(str(result.figures["weights"]), width="stretch")
    st.subheader("Weights")
    st.dataframe(pd.DataFrame(
        {"weight_%": (result.weights * 100).round(2)}),
        width="stretch")

# Risk
with tab_risk:
    st.subheader("Headline metrics - optimal vs SPY vs equal weight")
    st.dataframe(result.risk_summary.round(2), width="stretch")
    t = result.tail
    c1, c2, c3 = st.columns(3)
    c1.metric("95% VaR (historical)", fmt_pct(t["var_historical_%"] / 100))
    c2.metric("95% VaR (normal)", fmt_pct(t["var_normal_%"] / 100))
    c3.metric("95% CVaR / expected shortfall", fmt_pct(t["cvar_%"] / 100))
    st.image(str(result.figures["cumulative"]), width="stretch")
    st.image(str(result.figures["drawdowns"]), width="stretch")
    st.image(str(result.figures["attribution"]), width="stretch")

# Stress
with tab_str:
    st.subheader("Stylized one-month factor shocks")
    st.caption("Scenario impact = alpha + Σ β_k · shock_k - the factor "
               "model itself predicts the damage; no simulation needed.")
    st.dataframe(result.stress.round(2), width="stretch")
    st.image(str(result.figures["stress"]), width="stretch")

# Anomaly
with tab_an:
    st.subheader("Windowed autoencoder on portfolio daily returns")
    for b in result.anomaly_interpretation:
        st.markdown(f"- {b}")
    st.image(str(result.figures["anomaly"]), width="stretch")
    flagged = result.anomaly.flagged_windows
    if len(flagged):
        st.markdown(f"**{len(flagged)} flagged windows:**")
        # .round() on the whole frame would choke on the datetime
        # 'window_end' column - round only the numeric columns.
        shown = flagged.copy()
        for col in shown.select_dtypes(include="number"):
            shown[col] = shown[col].round(4)
        st.dataframe(shown, width="stretch")

# Export
with tab_out:
    st.subheader("Download results")
    st.caption("CSV/Excel contain the tables; the PDF and HTML reports are "
               "the shareable artifacts. The HTML report can be "
               "printed to PDF from any browser.")

    cols = st.columns(4)
    for name, col in zip(["exposures", "weights", "risk_summary", "stress"],
                         cols):
        frame = getattr(result, name)
        if isinstance(frame, pd.Series):
            frame = frame.to_frame()
        buf = io.StringIO()
        frame.to_csv(buf)
        col.download_button(f":material/download: {name}.csv", buf.getvalue(),
                            file_name=f"{name}.csv", mime="text/csv",
                            key=f"csv_{name}")

    xl = io.BytesIO()
    export_excel(result, xl)
    st.download_button(":material/table_view: Excel workbook",
                       xl.getvalue(), file_name="factor_risk_report.xlsx",
                       mime="application/vnd.openxmlformats-officedocument"
                            ".spreadsheetml.sheet",
                       key="xl", width="stretch")

    pdf = io.BytesIO()
    export_pdf(result, result.figures, pdf)
    st.download_button(":material/picture_as_pdf: PDF report", pdf.getvalue(),
                       file_name="factor_risk_report.pdf",
                       mime="application/pdf", key="pdf",
                       width="stretch")

    html = io.BytesIO()
    export_html(result, html)
    st.download_button(":material/language: HTML report", html.getvalue(),
                       file_name="factor_risk_report.html",
                       mime="text/html", key="html", width="stretch")

