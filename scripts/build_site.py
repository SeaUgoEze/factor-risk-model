#!/usr/bin/env python
"""Static Site Generator for the project page (docs/index.html).

Why SSG?  The previous page injected every section (model factors,
pipeline, builds, findings) with JavaScript, so search engines saw an
empty shell.  This builder pre-renders ALL content into static HTML at
build time - crawlers read the finished page, no JavaScript required -
and adds the SEO layer (meta/OpenGraph/Twitter/JSON-LD), robots.txt and
a sitemap.xml.

    python scripts/build_site.py

The figures in ``figures/`` are base64-embedded so the page stays a
single self-contained file that works on any static host (GitHub Pages,
S3, nginx...).
"""
from __future__ import annotations

import base64
import datetime
import html
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FIGURES_DIR = ROOT / "figures"

# Site identity
# Update REPO if the repo name differs; SITE_URL is the future GitHub Pages
# address (docs/ is served from the Pages root, so the page lives at the
# repo's root URL).
REPO = "https://github.com/SeaUgoEze/factor-risk-model"
SITE_URL = "https://seaugoeze.github.io/factor-risk-model/"
AUTHOR = "Sean Ezeocha"
GITHUB = "https://github.com/SeaUgoEze"
LINKEDIN = "https://www.linkedin.com/in/sean-ezeocha-424382276/"
EMAIL = "seanezeocha@gmail.com"

TITLE = "Factor Risk Model - Quantitative Portfolio Construction"
DESCRIPTION = (
    "An end-to-end factor-based risk and optimization model: Fama-French "
    "factor exposures with confidence intervals, mandate-driven portfolio "
    "optimization, VaR/CVaR risk analytics, stress tests and autoencoder "
    "anomaly detection - built with Python, pandas and scipy, with an "
    "interactive dashboard and CLI."
)
KEYWORDS = (
    "factor risk model, quantitative finance, Fama-French, portfolio "
    "optimization, factor investing, value at risk, CVaR, anomaly detection, "
    "autoencoder, python"
)

# Content (single source of truth for the page)
FACTORS = [
    ("f1", "Market - Mkt−RF",
     "The whole market's excess return over T-bills. Every stock carries "
     "this exposure; it is the price of being invested at all.", "market"),
    ("f2", "Size - SMB",
     "Small Minus Big: small-cap returns minus large-cap returns. A positive "
     "beta means the stock behaves like a small company.", "ff-3 factor"),
    ("f3", "Value - HML",
     "High Minus Low: cheap (high book-to-market) minus expensive. Positive "
     "beta → value stock; negative → growth stock.", "ff-3 factor"),
    ("f4", "Profitability - RMW",
     "Robust Minus Weak: firms with high operating profitability minus low. "
     "Positive beta → earnings strength drives the stock.", "ff-5 factor"),
    ("f5", "Investment - CMA",
     "Conservative Minus Aggressive: firms that invest little minus heavy "
     "spenders. Positive beta → disciplined capital allocator.", "ff-5 factor"),
]

PIPELINE = [
    ("01", "Data acquisition",
     "Daily prices from Yahoo, Fama-French factors from Ken French's library, "
     "aligned to 59 clean monthly observations."),
    ("02", "Factor exposures",
     "Estimated: betas, t-stats and R² for all 26 stocks under the 3- and "
     "5-factor models."),
    ("03", "Factor analysis",
     "Done: exposure heatmap, factor covariance structure, and a plain-English "
     "profile for all 26 stocks."),
    ("04", "Optimization",
     "Done: long-only can't satisfy the mandate (HML stuck at 0.70) - limited "
     "shorts hits every target at 17.3% vol."),
    ("05", "Performance & risk",
     "Done: backtest vs SPY - the mandate paid 2.8%/yr (arith.) at 15.3% vol; "
     "value/size dragged in 2015-19, so SPY won. VaR 6.5%, CVaR 8.1%, "
     "attribution R² 0.75."),
    ("06", "Anomaly detection",
     "Done: numpy autoencoder (26→3→26) flags 11/59 months - 2018 Q4, the "
     "Jan-2019 rebound, May/Aug-2019. Anomaly ≠ loss: sharp rebounds break "
     "co-movement structure too."),
    ("07", "Docs & notebook",
     "Done: README + notebook (25 cells, 10 pedagogy + 15 runnable, all "
     "verified) and the limitations documented."),
]

BUILDS = [
    ("s1", "Data engine",
     "Resilient fetch + cache + alignment layer. Survived real Yahoo "
     "rate-limits and a pandas-datareader index quirk.",
     "#F8F8F8", "scripts/step1_fetch.py", "src/data.py"),
    ("s2", "Factor regressions",
     "Done: 26 stock-level OLS runs - betas, t-stats, 95% confidence "
     "intervals, fit diagnostics. SPY validates at β≈0.99, R²≈0.997.",
     "#F8F8F8", "scripts/step2_regressions.py", "src/regressions.py"),
    ("s3", "Factor analysis",
     "Done: exposure heatmap, factor correlations (HML↔CMA +0.61), "
     "plain-English profiles.",
     "#F8F8F8", "scripts/step3_analysis.py", "src/analysis.py"),
    ("s4", "Portfolio optimizer",
     "Done: SLSQP/trust-constr minimize variance under a factor mandate. "
     "Limited shorts beat long-only (17.3% vs 23.0% vol).",
     "#F8F8F8", "scripts/step4_optimization.py", "src/optimization.py"),
    ("s5", "Risk lab",
     "Done: backtest vs SPY and equal weight, max drawdown 20.9%, historical "
     "VaR 6.5% / CVaR 8.1%, factor attribution R² 0.75.",
     "#F8F8F8", "scripts/step5_performance.py", "src/risk.py"),
    ("s6", "Anomaly detection",
     "Done: hand-rolled numpy autoencoder + PCA baseline. Flags 2018 Q4, "
     "Jan-2019 rebound, May/Aug-2019; 5/11 months shared with the linear "
     "baseline.",
     "#F8F8F8", "scripts/step6_anomaly.py", "src/anomaly.py"),
    ("s7", "Docs & notebook",
     "Done: README.md, notebooks/factor_risk_model.ipynb (15 code cells "
     "dry-run verified end-to-end), and the key findings below.",
     "#F8F8F8", "scripts/make_notebook.py", "README.md"),
    ("s8", "Interactive app",
     "Done: interactive dashboard + CLI over the same run_pipeline() - ticker "
     "picker, mandate sliders, 95% CIs, stress tests, windowed autoencoder, "
     "and CSV/Excel/PDF/HTML export. 32 offline pytest checks green.",
     "#F8F8F8", "factor_risk_model/interface/streamlit_app.py",
     "factor_risk_model/pipeline.py"),
]

FINDINGS = [
    ("f1", "Factor investing: the core mechanics",
     "Factors are the data compression that makes portfolio risk estimable "
     "at all - 5×5 factor covariance instead of a noise-dominated 26×26, "
     "~100× fewer parameters. And a mandate is a bet, not a guarantee: the "
     "optimizer hit every target exactly, yet the value/size bet lost in "
     "2015-19. Optimization executes conviction; it doesn't create it."),
    ("f2", "The institutional mandate → optimizer → risk loop",
     "This is the mandate → optimizer → risk-autopsy loop used by pension "
     "funds and asset managers: the committee sets the factor risk budget, "
     "the optimizer allocates at minimum risk (with feasibility: "
     "'long-only can't do it' is a weekly PM conversation), and the risk "
     "engine measures VaR/CVaR, drawdowns and attribution. The HML↔CMA +0.61 "
     "overlap and CVaR > VaR are institutional-grade talking points."),
    ("f3", "Limitations",
     "In-sample everywhere (betas fit and portfolio optimized on the same 59 "
     "months - vol is optimistic); one regime with no crisis; static, "
     "non-rolling betas; 26 mega-caps is a small universe; residuals assumed "
     "uncorrelated (diagonal D); no transaction costs, turnover constraints "
     "or short-borrow costs."),
]

# (png file, img id, alt text, caption)
FIGURES = [
    ("factor_exposures_heatmap.png", "fig-heatmap",
     "Factor exposure heatmap of every stock's five betas, grouped by sector",
     "fig 01 - every stock's five betas, rows grouped by sector. Light "
     "loads positive, dark negative; tickers are labeled by sector."),
    ("factor_correlation_heatmap.png", "fig-corr",
     "Fama-French factor correlation heatmap",
     "fig 02 - factor correlations. HML ↔ CMA at +0.61 is the big one: value "
     "and conservative-investment stocks move together."),
    ("portfolio_weights.png", "fig-weights",
     "Optimal portfolio weights hitting the factor mandate",
     "fig 03 - optimal weights meeting the value + size mandate (limited "
     "shorts, −10% floor). Light = long, dark = short; the mandate is hit "
     "exactly at 17.3% annualized vol."),
    ("cumulative_returns.png", "fig-cumulative",
     "Cumulative growth of the optimized portfolio vs SPY vs equal weight",
     "fig 04 - growth of $1. The optimized portfolio is engineered for the "
     "*mandate*, not for raw return: in 2015-19 the value + size factors it "
     "targets actually lost money, so it trails both SPY and the equal-weight "
     "universe."),
    ("drawdowns.png", "fig-drawdowns",
     "Drawdown paths of the optimized portfolio vs SPY",
     "fig 05 - drawdowns. Max depth 20.9% (optimal) vs 13.5% (SPY); the "
     "factor-concentrated book gives up some drawdown protection for its "
     "targeted exposures."),
    ("factor_attribution.png", "fig-attribution",
     "Factor attribution of the optimal portfolio's returns",
     "fig 06 - factor attribution, annualized. Market +7.7%, then the style "
     "bets: HML −3.1% and SMB −0.9% (value/size didn't pay in this window), "
     "alpha −1.3%. Factors explain 75% of portfolio variance."),
    ("holdings_correlation.png", "fig-holdcorr",
     "Correlation heatmap of the 12 largest holdings",
     "fig 07 - correlation of the 12 largest holdings. The bank block (GS, "
     "JPM, WFC) sits at 0.6-0.8 - the value tilt concentrates correlated, "
     "economically sensitive risk."),
    ("anomaly_detection.png", "fig-anomaly",
     "Autoencoder reconstruction error over time with flagged months",
     "fig 08 - autoencoder anomaly lens. Top: monthly reconstruction error "
     "vs the 2σ threshold. Bottom: portfolio wealth with flagged months "
     "shaded. The lens flags 2018 Q4's selloff, the Jan-2019 rebound, and "
     "May/Aug-2019 - structure-breaks in both directions."),
]


def esc(s: str) -> str:
    """HTML-escape text content."""
    return html.escape(s, quote=False)


def data_uri(name: str) -> str:
    path = FIGURES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"missing figure: {path} (run the step scripts)")
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def png_size(path: pathlib.Path) -> tuple[int, int]:
    """Return (width, height) of a PNG by reading its IHDR chunk (no deps)."""
    with path.open("rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", head[16:24])


# Rendering helpers
def render_model_rows() -> str:
    rows = []
    for no, name, d, tag in FACTORS:
        rows.append(
            f'<div class="row"><span class="no">{no}</span>'
            f'<div class="main"><div class="t">{esc(name)}</div>'
            f'<div class="d">{esc(d)}</div></div>'
            f'<div class="right">{tag}</div></div>')
    return "".join(rows)


def render_pipeline_rows() -> str:
    rows = []
    for no, t, d in PIPELINE:
        rows.append(
            f'<div class="row"><span class="no">{no}</span>'
            f'<div class="main"><div class="t">{esc(t)}</div>'
            f'<div class="d">{esc(d)}</div></div>'
            f'<div class="right status">'
            f'<span class="stat-pill"><span class="dot done"></span> done</span>'
            f'</div></div>')
    return "".join(rows)


def render_build_cards() -> str:
    cards = []
    for icon, t, d, color, code, src in BUILDS:
        cards.append(
            f'<div class="card" style="--flood:{color}">'
            f'<div class="flood"></div>'
            f'<div class="top"><div class="icon">{icon}</div>'
            f'<div><h3>{esc(t)}</h3><div class="sub">{esc(d)}</div></div></div>'
            f'<div class="mono-line" style="margin-top:14px">'
            f'<span class="stat-pill"><span class="dot done"></span> done</span>'
            f'</div>'
            f'<div class="links">'
            f'<a href="{REPO}/blob/HEAD/{code}" target="_blank" rel="noopener" '
            f'style="--link:{color}">code →</a>'
            f'<a href="{REPO}/blob/HEAD/{src}" target="_blank" rel="noopener" '
            f'style="--link:{color}">src →</a>'
            f'</div></div>')
    return "".join(cards)


def render_findings_rows() -> str:
    rows = []
    for no, q, a in FINDINGS:
        rows.append(
            f'<div class="row"><span class="no">{no}</span>'
            f'<div class="main"><div class="t">{esc(q)}</div>'
            f'<div class="d">{esc(a)}</div></div></div>')
    return "".join(rows)


def render_figures(ids: list[str]) -> str:
    out = []
    for name, fid, alt, caption in FIGURES:
        if fid not in ids:
            continue
        w, h = png_size(FIGURES_DIR / name)
        out.append(
            f"<figure><img id=\"{fid}\" src=\"{data_uri(name)}\" "
            f"alt=\"{esc(alt)}\" width=\"{w}\" height=\"{h}\" "
            f"loading=\"lazy\" decoding=\"async\">"
            f"<figcaption>{esc(caption)}</figcaption></figure>")
    return "".join(out)


def seo_head() -> str:
    return f"""
<meta name="description" content="{esc(DESCRIPTION)}">
<meta name="keywords" content="{esc(KEYWORDS)}">
<meta name="author" content="{AUTHOR}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{SITE_URL}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Factor Risk Model">
<meta property="og:title" content="{esc(TITLE)}">
<meta property="og:description" content="{esc(DESCRIPTION)}">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:image" content="{SITE_URL}og-image.png">
<meta property="og:image:alt" content="{esc(DESCRIPTION)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE_URL}og-image.png">
<meta name="twitter:title" content="{esc(TITLE)}">
<meta name="twitter:description" content="{esc(DESCRIPTION)}">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "WebSite",
      "name": "Factor Risk Model",
      "url": "{SITE_URL}",
      "description": "{esc(DESCRIPTION)}"
    }},
    {{
      "@type": "Person",
      "name": "{AUTHOR}",
      "url": "{GITHUB}",
      "sameAs": ["{LINKEDIN}"]
    }}
  ]
}}
</script>
"""


# The page
CSS = """
  :root {
    --bg: #101018; --fg: #F8F8F8; --grid-line: rgba(248,248,248,0.05);
    --t-90: rgba(248,248,248,.90); --t-70: rgba(248,248,248,.70);
    --t-60: rgba(248,248,248,.60); --t-50: rgba(248,248,248,.55);
    --t-40: rgba(248,248,248,.45); --t-30: rgba(248,248,248,.30);
    --card-bg: #181820; --card-border: #282830;
    --card-border-hover: #3A3A42; --card-bg-hover: #1E1E28;
    --green: #2EA043; --red: #E5484D; --ink: #F8F8F8;
    --sans: "Geist", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Arial, sans-serif;
    --mono: "Geist Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body { background: var(--bg); color: var(--fg); font-family: var(--sans);
    font-weight: 400; line-height: 1.6; overflow-x: hidden; -webkit-font-smoothing: antialiased; }
  ::selection { background: var(--ink); color: var(--bg); }
  .grid-layer { position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image: repeating-linear-gradient(to right, var(--grid-line) 0,
    var(--grid-line) 1px, transparent 1px, transparent 2vw); }
  .glow { position: fixed; z-index: 0; pointer-events: none; border-radius: 50%;
    filter: blur(90px); opacity: .07; }
  .glow.a { width: 480px; height: 480px; top: -140px; left: -120px; background: var(--ink); }
  .glow.b { width: 420px; height: 420px; bottom: 8%; right: -140px; background: var(--ink); }
  nav { position: fixed; top: 0; left: 0; right: 0; z-index: 60;
    display: flex; align-items: center; justify-content: space-between; padding: 18px 24px;
    background: rgba(16,16,24,.80); backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--card-border); }
  nav .brand { font-family: var(--mono); font-size: 13px; letter-spacing: .02em; color: var(--fg); }
  nav .links { display: flex; gap: 26px; }
  nav .links a { font-family: var(--mono); font-size: 12px; letter-spacing: .06em;
    color: var(--t-60); text-transform: lowercase; text-decoration: none; transition: color .25s; }
  nav .links a:hover { color: var(--fg); }
  .wrap { max-width: 54rem; margin: 0 auto; padding: 0 24px; }
  section { position: relative; z-index: 1; margin-bottom: 96px; }
  /* section headers are VISIBLE by default (SSG/no-JS) - the reveal script
     hides them and animates them in only when JS is available. */
  .sec-head { display: flex; align-items: center; gap: 14px; margin-bottom: 40px; }
  .sec-head::before { content: ""; height: 1px; flex: 1;
    background: linear-gradient(to left, rgba(0,0,0,.30), transparent);
    transform-origin: right; }
  .sec-head h2 { font-size: clamp(1.25rem, 3vw, 1.5rem); font-weight: 400;
    color: var(--t-90); white-space: nowrap; }
  .sec-head .rule { height: 1px; flex: 1;
    background: linear-gradient(to right, rgba(0,0,0,.30), transparent);
    transform-origin: left; }
  header.hero { padding: 170px 24px 40px; }
  .hero-row { display: flex; align-items: center; justify-content: flex-start;
    gap: 48px; margin-top: 32px; flex-wrap: wrap; }
  .badge-wrap { width: 132px; height: 132px; flex-shrink: 0; animation: spin 18s linear infinite; }
  .badge-wrap svg { width: 100%; height: 100%; display: block; }
  .badge-text { font-family: var(--mono); font-size: 6.2px; letter-spacing: .08em;
    fill: var(--t-50); text-transform: uppercase; }
  .badge-core { font-family: var(--mono); font-size: 15px; letter-spacing: .1em; fill: var(--t-70); }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .badge-wrap { animation: none; } }
  header.hero h1 { font-family: "Times New Roman", Times, Georgia, serif;
    font-size: clamp(2.6rem, 9vw, 4.5rem); font-weight: 400; line-height: 1.1; color: var(--fg); }
  header.hero h1 .ch { display: inline-block; }
  header.hero .tagline { margin: 0; max-width: 32rem; text-align: left;
    font-size: 16px; color: var(--t-60); }
  header.hero .tagline a { color: var(--fg); text-decoration: underline;
    text-decoration-color: var(--ink); text-underline-offset: 3px; }
  header.hero .meta { margin-top: 34px; font-family: var(--mono); font-size: 12px;
    letter-spacing: .08em; text-transform: uppercase; color: var(--t-40); }
  header.hero .meta b { color: var(--t-70); font-weight: 400; }
  .card { position: relative; overflow: hidden; border: 1px solid var(--card-border);
    background: var(--card-bg);
    backdrop-filter: blur(10px); padding: 26px;
    transition: border-color .3s, background .3s, transform .3s; }
  .card:hover { border-color: var(--card-border-hover); background: var(--card-bg-hover); }
  .card .flood { position: absolute; inset: -30%;
    background: radial-gradient(circle at 30% 20%, var(--flood, var(--ink)), transparent 60%);
    opacity: 0; transition: opacity .5s; pointer-events: none; }
  .card:hover .flood { opacity: .10; }
  .card .top { position: relative; display: flex; align-items: center; gap: 12px; }
  .card .icon { width: 44px; height: 44px; flex-shrink: 0;
    border: 1px solid var(--card-border); background: var(--bg);
    display: grid; place-items: center; font-family: var(--mono); font-size: 13px; color: var(--t-70); }
  .card h3 { position: relative; font-size: 17px; font-weight: 500; color: var(--fg); }
  .card .sub { position: relative; color: var(--t-50); font-size: 13.5px; margin-top: 3px; }
  .card p { position: relative; margin-top: 14px; font-size: 14.5px; color: var(--t-60); }
  .card .mono-line { position: relative; margin-left: auto; text-align: right;
    font-family: var(--mono); font-size: 12px; color: var(--t-40); white-space: nowrap; }
  .card .links { position: relative; margin-top: 18px; display: flex; gap: 22px;
    font-family: var(--mono); font-size: 13px; }
  .card .links a { color: var(--t-70); text-decoration: none;
    border-bottom: 1px solid transparent; padding-bottom: 1px; transition: color .2s; }
  .card .links a:hover { color: var(--fg); border-bottom-color: var(--link, var(--ink)); }
  .dot { width: 8px; height: 8px; display: inline-block; }
  .dot.done { background: var(--green); }
  .dot.next { background: var(--t-40); }
  .dot.todo { background: rgba(248,248,248,.15); }
  .stat-pill { display: inline-flex; align-items: center; gap: 8px;
    font-family: var(--mono); font-size: 11.5px; letter-spacing: .08em;
    text-transform: uppercase; color: var(--t-50); }
  .rows { border-top: 1px solid rgba(248,248,248,.08); }
  .row { display: flex; align-items: baseline; gap: 18px; padding: 17px 4px;
    border-bottom: 1px solid rgba(248,248,248,.08); transition: background .25s; }
  .row:hover { background: rgba(248,248,248,.03); }
  .row .no { font-family: var(--mono); font-size: 12px; color: var(--t-30);
    width: 34px; flex-shrink: 0; }
  .row .main { flex: 1; min-width: 0; }
  .row .main .t { color: var(--t-90); font-size: 15.5px; }
  .row .main .d { color: var(--t-50); font-size: 13.5px; margin-top: 2px; }
  .row .right { font-family: var(--mono); font-size: 12px; color: var(--t-40);
    text-align: right; flex-shrink: 0; }
  .row .status { display: flex; align-items: center; gap: 8px; }
  figure { margin: 0 0 44px; }
  figure img { width: 100%; border: 1px solid var(--card-border); }
  figcaption { margin-top: 10px; font-family: var(--mono); font-size: 12px; color: var(--t-40); }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 720px) { .grid { grid-template-columns: 1fr; } }
  footer { position: relative; z-index: 1; border-top: 1px solid var(--card-border);
    padding: 72px 0 84px; text-align: center; }
  footer h2 { font-weight: 400; font-size: clamp(1.5rem, 4vw, 2rem); color: var(--t-90); }
  footer .mono-line { font-family: var(--mono); font-size: 13px; color: var(--t-40); margin-top: 10px; }
  footer .socials { margin-top: 26px; display: flex; gap: 30px; justify-content: center;
    font-family: var(--mono); font-size: 14px; }
  footer .socials a { color: var(--t-70); text-decoration: none; padding-bottom: 2px;
    border-bottom: 1px solid transparent; transition: color .2s, border-color .2s; }
  footer .socials a:hover { color: var(--fg); border-bottom-color: var(--ink); }
  .privacy-badge { margin-top: 36px; display: inline-flex; align-items: center;
    justify-content: center; gap: 9px; max-width: 36rem; font-family: var(--mono);
    font-size: 11px; letter-spacing: .04em; line-height: 1.55; color: var(--t-50);
    border: 1px solid var(--card-border); padding: 9px 18px; }
  .privacy-badge svg { flex-shrink: 0; }
  /* live-dashboard call to action - rectangular, like the app's Run button */
  .cta { display: inline-block; margin-top: 30px; padding: 13px 24px;
    background: var(--ink); color: var(--bg); font-family: var(--mono);
    font-size: 13px; letter-spacing: .08em; text-transform: uppercase;
    text-decoration: none; border: 1px solid var(--ink); transition: all .2s; }
  .cta:hover { background: transparent; color: var(--ink); }
  nav .links a.cta-nav { color: var(--fg); border: 1px solid var(--card-border);
    padding: 6px 12px; }
  nav .links a.cta-nav:hover { border-color: var(--fg); }
  footer .foot { margin-top: 56px; font-family: var(--mono); font-size: 11px; color: var(--t-30); }
  a.anchor { scroll-margin-top: 90px; }
"""

JS = """
  /* ============ hero: per-letter reveal (progressive enhancement - the h1
     is real text; without JS it stays fully readable) ============ */
  (function () {
    var title = document.getElementById("hero-title");
    if (!title) return;
    var words = title.textContent.trim().split(/\\s+/);
    title.innerHTML = words.map(function (w, i) {
      var chs = w.split("").map(function (c) {
        return '<span class="ch" style="opacity:0;transform:translateY(-22px);'
          + 'transition:opacity .5s ease,transform .5s cubic-bezier(.2,.7,.3,1)">'
          + c + "</span>";
      }).join("");
      return '<span class="word">' + chs + "</span>"
        + (i < words.length - 1 ? "&nbsp;" : "");
    }).join("");
    var i = 0;
    title.querySelectorAll(".ch").forEach(function (ch) {
      setTimeout(function () {
        ch.style.opacity = 1; ch.style.transform = "translateY(0)";
      }, 120 + i * 22);
      i += 1;
    });
  })();

  /* ============ scroll reveals (kennywu motion language) ============ */
  (function () {
    if (!("IntersectionObserver" in window)) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var t = e.target;
        t.style.transition = "opacity .6s ease, transform .6s ease";
        t.style.opacity = 1; t.style.transform = "none";
        if (t.classList.contains("sec-head")) t.classList.add("in");
        io.unobserve(t);
      });
    }, { threshold: 0.12 });

    document.querySelectorAll("section, footer, .sec-head").forEach(function (s) {
      s.style.opacity = 0; s.style.transform = "translateY(30px)"; io.observe(s);
    });
    document.querySelectorAll(".card").forEach(function (c) {
      c.style.opacity = 0; c.style.transform = "translateX(40px)"; io.observe(c);
    });
  })();
"""


def page() -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(TITLE)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@200;300;400;500;600&family=Geist+Mono:wght@300;400;500&display=swap" rel="stylesheet">
{seo_head()}
<style>{CSS}</style>
</head>
<body>

<div class="grid-layer"></div>
<div class="glow a"></div>
<div class="glow b"></div>

<nav>
  <span class="brand">factor risk model</span>
  <div class="links">
    <a href="#about">about</a>
    <a href="#model">model</a>
    <a href="#pipeline">pipeline</a>
    <a href="#builds">builds</a>
    <a href="#exposures">exposures</a>
    <a href="#performance">performance</a>
    <a href="#findings">findings</a>
    <a class="cta-nav" href="https://sean-ezeocha-factor-risk-model.streamlit.app"
       target="_blank" rel="noopener">live app</a>
  </div>
</nav>

<header class="hero wrap">
  <h1 id="hero-title">Factor Risk Model</h1>
  <div class="hero-row">
    <p class="tagline">
      A factor-based risk &amp; optimization framework: 26 US large-caps priced against the
      Fama-French factor library, an optimized portfolio engineered to hit a target factor
      profile, and a full risk autopsy. Modeled on the
      <a href="#pipeline">factor-based frameworks</a> used by institutional asset managers
      and pension funds.
    </p>
    <div class="badge-wrap" aria-hidden="true">
      <svg viewBox="0 0 120 120">
        <defs>
          <path id="badge-circle" d="M60,60 m-44,0 a44,44 0 1,1 88,0 a44,44 0 1,1 -88,0"/>
        </defs>
        <text class="badge-text">
          <textPath href="#badge-circle" xlink:href="#badge-circle">quantitative models · applied research · portfolio construction ·</textPath>
        </text>
        <text class="badge-core" x="60" y="60" text-anchor="middle" dominant-baseline="central">FRM</text>
      </svg>
    </div>
  </div>
  <p class="meta"><b>26</b> stocks · <b>8</b> sectors · <b>59</b> months · <b>5</b> factors · <b>1</b> optimized portfolio</p>
  <div>
    <a class="cta" href="https://sean-ezeocha-factor-risk-model.streamlit.app"
       target="_blank" rel="noopener">launch the live dashboard →</a>
  </div>
</header>

<main class="wrap">

  <section id="about" class="anchor">
    <div class="sec-head"><h2>currently</h2><div class="rule"></div></div>
    <div class="card" style="--flood:#F8F8F8">
      <div class="flood"></div>
      <div class="top">
        <div class="icon">fr</div>
        <div>
          <h3>Complete - Factor Risk Model</h3>
          <div class="sub">seven steps, end to end - data → exposures → analysis → optimization → risk → anomalies → docs</div>
        </div>
        <div class="mono-line">2015 - 2019</div>
      </div>
      <p>
        All seven engine steps are done, and the whole thing now ships as a
        professional tool: an interactive dashboard and a CLI - both driving the same
        pipeline - plus a notebook, 32 offline tests, and this page. Set a mandate
        with sliders, hit Run, export CSV/Excel/PDF/HTML.
      </p>
      <div class="links" style="margin-top:20px">
        <a class="cta" href="https://sean-ezeocha-factor-risk-model.streamlit.app"
           target="_blank" rel="noopener">launch the live dashboard →</a>
      </div>
      <div class="links" style="margin-top:20px">
        <span class="stat-pill"><span class="dot done"></span> step 07 · done</span>
        <span class="stat-pill"><span class="dot done"></span> project complete</span>
      </div>
    </div>
  </section>

  <section id="model" class="anchor">
    <div class="sec-head"><h2>the model</h2><div class="rule"></div></div>
    <div class="rows" id="model-rows">{render_model_rows()}</div>
  </section>

  <section id="pipeline" class="anchor">
    <div class="sec-head"><h2>the pipeline</h2><div class="rule"></div></div>
    <div class="rows" id="pipeline-rows">{render_pipeline_rows()}</div>
  </section>

  <section id="builds" class="anchor">
    <div class="sec-head"><h2>the builds</h2><div class="rule"></div></div>
    <div class="grid" id="builds-grid">{render_build_cards()}</div>
  </section>

  <section id="exposures" class="anchor">
    <div class="sec-head"><h2>exposures</h2><div class="rule"></div></div>
    {render_figures(["fig-heatmap", "fig-corr", "fig-weights"])}
  </section>

  <section id="performance" class="anchor">
    <div class="sec-head"><h2>performance &amp; risk</h2><div class="rule"></div></div>
    {render_figures(["fig-cumulative", "fig-drawdowns", "fig-attribution",
                     "fig-holdcorr", "fig-anomaly"])}
  </section>

  <section id="findings" class="anchor">
    <div class="sec-head"><h2>findings</h2><div class="rule"></div></div>
    <div class="rows" id="findings-rows">{render_findings_rows()}</div>
  </section>

</main>

<footer>
  <h2>get in touch</h2>
  <p class="mono-line">always open to discussing quantitative models and interesting problems.</p>
  <div class="socials">
    <a href="{GITHUB}" target="_blank" rel="noopener">github →</a>
    <a href="{LINKEDIN}" target="_blank" rel="noopener">linkedin →</a>
    <a href="mailto:{EMAIL}">email →</a>
  </div>
  <p class="privacy-badge">
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
    privacy - the live dashboard runs on Streamlit Cloud · market data from public sources (Yahoo Finance, Kenneth French Data Library) · nothing personal is stored
  </p>
  <p class="foot">© 2026 {AUTHOR} · factor risk model · python · pandas · statsmodels · scipy · matplotlib</p>
</footer>

<script>{JS}</script>
</body>
</html>
"""


def robots_txt() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"\nSitemap: {SITE_URL}sitemap.xml\n"
    )


def sitemap_xml() -> str:
    lastmod = datetime.date.today().isoformat()
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{SITE_URL}</loc>"
        f"<lastmod>{lastmod}</lastmod>"
        "<changefreq>monthly</changefreq><priority>1.0</priority></url>\n"
        "</urlset>\n"
    )


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.html").write_text(page(), encoding="utf-8")
    (DOCS / "robots.txt").write_text(robots_txt(), encoding="utf-8")
    (DOCS / "sitemap.xml").write_text(sitemap_xml(), encoding="utf-8")
    # og:image must be a real reachable file, not a data URI - copy the most
    # visual figure to docs/ so social crawlers can fetch it at SITE_URL/og-image.png
    og_src = FIGURES_DIR / "factor_exposures_heatmap.png"
    if og_src.exists():
        (DOCS / "og-image.png").write_bytes(og_src.read_bytes())
    print(f"[build_site] docs/index.html ({len(page()):,} bytes) - content pre-rendered, SEO ready")
    print("[build_site] docs/robots.txt + docs/sitemap.xml + og-image.png written")


if __name__ == "__main__":
    main()
