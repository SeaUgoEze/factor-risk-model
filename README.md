# Factor-Based Risk & Optimization Model

An end-to-end quantitative portfolio framework - from raw market data to a factor-tilted
portfolio, a full risk autopsy, a machine-learning anomaly lens - wrapped in a
**professional interactive application** a portfolio manager could actually drive:

```
data → factor exposures → factor analysis → optimization → performance & risk → anomaly detection
```

Two layers, one pipeline:

- **`src/` - the engine** (v0.1): tested, headless model library. One module per step,
  heavily commented, real market data (Yahoo Finance prices + Kenneth French factor
  library) over a clean 2015–2019 window.
- **`factor_risk_model/` - the application** (v0.2): an interactive dashboard and a CLI that
  call the same `run_pipeline()`, so every interface reports identical numbers. Users
  pick tickers, set a mandate with sliders, hit Run, and export CSV / Excel / PDF / HTML.

The project mirrors how institutional asset managers build portfolios: a **mandate** sets
target factor exposures, an **optimizer** realizes them at minimum risk, and a **risk
engine** stress-tests the result - with the caveats written down (see *Limitations*).

---

## Quick start

```bash
# 1. create and activate a virtual environment (Python 3.10+)
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. install dependencies
python -m pip install -r requirements.txt

# 3a. interactive web dashboard (the flagship interface)
streamlit run factor_risk_model/interface/streamlit_app.py
#     or: python -m streamlit run factor_risk_model/interface/streamlit_app.py

# 3b. command line (reproducible, scriptable)
python main.py --stocks AAPL MSFT JPM --target_hml 0.7 --no-shorts
python main.py --help                # every option

# 4. static portfolio site (SEO-ready, no JS required to read it)
python scripts/build_site.py          # regenerates docs/ (HTML + robots.txt + sitemap.xml)
```

First run downloads + caches the market data under `data/`; afterwards everything is
instant and offline. Run the original step scripts (`python scripts/step1_fetch.py` …)
for the engine's printed walkthrough.

---

## The interactive app

### Interactive dashboard

**Try it live: [sean-ezeocha-factor-risk-model.streamlit.app](https://sean-ezeocha-factor-risk-model.streamlit.app)** - hosted on Streamlit Cloud, no download or install needed; runs in your browser.

Sidebar (every control maps to `factor_risk_model/config.py`):

| Control | What it does |
|---|---|
| **Stocks** | multi-select from the curated 26-stock universe + free-text extra tickers |
| **Start / End date** | window (validated: ≥ 24 overlapping months) |
| **Factor model** | 3-factor or 5-factor Fama-French |
| **Target exposures** | slider per factor (−1.0 … 2.0) - the *mandate* |
| **Constraints** | allow shorts (default on, −10% floor), exposure tolerance |
| **Vol budget** | a *warning threshold* - see the note below |

Tabs after **▶ Run analysis**:

- **Exposures** - beta table with **95% confidence intervals**, sector heatmap, CI
  whisker chart, rolling-exposure paths, plain-English factor profiles.
- **Optimization** - target vs achieved, weight chart + table, and the vol breakdown
  (factor risk + idiosyncratic risk).
- **Risk & performance** - optimal vs SPY vs equal weight: return/vol/Sharpe/max
  drawdown, historical + parametric VaR, CVaR, cumulative growth, drawdown paths,
  factor attribution.
- **Stress test** - one-month impact of stylized shocks (COVID, GFC, 2022 rate shock,
  tech-bubble) computed directly from the factor model.
- **Anomaly** - windowed autoencoder on daily returns, flagged periods, the
  "anomaly ≠ loss" interpretation.
- **Export** - one-click CSV per table, multi-sheet Excel workbook, a **PDF report**,
  and a printable HTML report.

### Theme & chart colours

The dashboard uses a flat monochrome theme with perfectly rectangular borders
(zero border-radius anywhere):

| Token | Hex | Used for |
|---|---|---|
| Canvas | `#101018` | app background |
| Panels | `#181820` | cards, sidebar surfaces |
| Hairlines | `#282830` | borders, rules, grid lines |
| Ink / accent | `#F8F8F8` | text, sliders, Run button, selected tab |
| Muted / faint | `#8A8A92` / `#626262` | labels, secondary text |
| Downside red | `#E5484D` | losses, negatives, flagged windows |

A **Chart colour** toggle in the sidebar controls only the figures (the UI
chrome stays grayscale in both modes):

- **Monochrome** (default) - every chart is grayscale.
- **Semantic** - colour is added only where it carries meaning: muted deep
  green `#2EA043` for gains/positive loadings, the downside red `#E5484D` for
  losses, amber `#D29922` for the equal-weight comparison series, and a
  red-to-neutral-to-green ramp on the exposure/correlation heatmaps so
  positive vs negative loadings read at a glance. No blue appears anywhere
  in semantic mode; the monochrome heatmaps annotate sign in red/blue.

> **Why "vol budget" is a warning, not a constraint.** The optimizer *minimizes*
> variance for a fixed mandate, so achieved volatility is an output, not an input. A
> budget above the minimum is automatically satisfied; below it is mathematically
> impossible while still hitting the mandate. So the app reports the conflict
> instead of pretending to control an output.

### CLI

```bash
python main.py --stocks AAPL MSFT JPM XOM JNJ PG --model 3-factor \
               --target_hml 0.7 --target_smb 0.3 --no-shorts --export all
```

Prints the exposure table, mandate comparison, vol decomposition, risk summary, stress
table and the plain-English interpretation; writes CSV/Excel/PDF/HTML to
`outputs/reports/<timestamp>/`. Exits non-zero with a friendly message on bad input.

---

## Architecture

```
factor_risk_model/                the application layer (owns the *experience*)
├── config.py                     UI defaults; imports engine constants (never duplicates)
├── pipeline.py                   run_pipeline() - the ONE function both interfaces call
├── data/data_fetcher.py          fetch + align + friendly errors (wraps src.data)
├── models/factor_model.py        FactorModel - exposures + 95% CIs + rolling betas
├── models/optimizer.py           PortfolioOptimizer - mandate → weights + warnings
├── analytics/risk_metrics.py     RiskAnalyzer - metrics, attribution, stress tests
├── analytics/anomaly_detection.py windowed autoencoder on daily returns
├── visualization/plots.py        CI, stress, rolling, anomaly charts (dark theme)
├── interface/streamlit_app.py    web dashboard
├── interface/cli.py              argparse CLI
└── utils/                        helpers.py (parsing/formatting) · export.py (reports)

src/                              the engine (owns the *math*)
├── config.py · data.py · regressions.py · analysis.py
└── optimization.py · risk.py · anomaly.py

tests/                            pytest suite - all offline (uses the data cache)
main.py                           CLI entry point
docs/index.html                   the live project page
```

---

## The pipeline (engine steps)

| # | Step | What it produces |
|---|------|------------------|
| 1 | **Data acquisition** | Daily prices for 26 S&P 500 names across 8 sectors + SPY (Yahoo Finance, cached); monthly Fama-French 3- or 5-factor returns (Kenneth French library, direct-download fallback). Aligned to 59 clean monthly observations. |
| 2 | **Factor exposures** | OLS of every stock's excess returns on the factors → betas, t-stats, **95% CIs**, R², residual vol. SPY validates the pipeline (β_mkt ≈ 0.99, R² ≈ 0.997). |
| 3 | **Factor analysis** | Exposure heatmap, factor covariance/correlation, annualized factor vols, plain-English profiles. |
| 4 | **Portfolio optimization** | Variance-minimizing portfolio hitting a target factor profile via `scipy.optimize` (SLSQP + trust-constr fallback). Long-only vs limited-shorts with feasibility. |
| 5 | **Performance & risk** | Backtest vs SPY and equal weight: return/vol/Sharpe, max drawdown, historical + parametric VaR, CVaR, factor attribution. |
| 6 | **Anomaly detection** | Hand-rolled numpy autoencoder (explicit backprop, Adam, early stopping) scores co-movement structure; reconstruction error flags unexplained months. |
| 7 | **Docs & notebook** | README + `notebooks/factor_risk_model.ipynb`, a fully runnable version of every step. |

---

## Tests

```bash
python -m pytest tests/ -q        # 30 tests, all offline (uses the data cache)
```

Covers the spec's Phase-5 checklist: data quality + alignment, exposure sanity
(betas in bounds, R² ∈ [0,1], CI contains the estimate, SPY β ≈ 1), **optimizer
constraints** (sum(w)=1, no shorts when disabled, short floor respected, infeasibility
for aggressive long-only mandates), edge cases (single stock, unknown ticker, short
window, empty selection), and a <30 s performance budget on the full pipeline.

---

## Key findings

1. **The pipeline validates itself.** SPY loads at β_mkt = 0.989 with R² = 0.997 - the
   benchmark behaves exactly like the market, so downstream numbers are believable.
2. **The optimizer does its job; the mandate is another question.** Long-only *cannot*
   satisfy "value +1.0, size +0.5" (best effort stalls at HML 0.70). Limited shorts
   (floor −10%) hit every target exactly at **17.3% vol** vs 23.0% long-only.
3. **Factor targeting ≠ return targeting.** In 2015–19 the optimized portfolio trailed
   both SPY and equal weight (Sharpe 0.11 vs 0.96 and 1.40). Attribution shows why: the
   value/size bets it was engineered to hold lost money (HML −3.1%/yr, SMB −0.9%/yr).
   An optimizer executes conviction; it does not create it.
4. **Anomaly ≠ loss.** Flagged months average the same return as all months
   (+0.32% vs +0.31%): the lens detects breaks in co-movement, not simply bad returns.

---

## Limitations (read before trusting any number)

- **One regime, one window.** 2015–2019 is a "normal" market; the model says nothing
  about crises. Extending to 2020+ would re-estimate under COVID.
- **Static betas in the engine.** Exposures are estimated once (in-sample); the app's
  rolling-exposure chart is the first step toward the monthly-updating betas real desks use.
- **Optimization is in-sample.** No walk-forward or holdout; vol figures are optimistic.
- **Small universe, small sample.** 26 mega-caps, 59 months. The factor structure is what
  makes risk estimation possible at all.
- **No costs, no turnover constraints.** Shorts assume −10% floors only.
- **Residuals assumed uncorrelated.** Idiosyncratic covariance is diagonal (BVB′ + D).

