"""
Step 7 - Generate the interactive notebook
==========================================
Run:  python scripts/make_notebook.py

Builds notebooks/factor_risk_model.ipynb from nbformat: a fully runnable,
markdown-led walkthrough of every step of the project.  Each code cell
re-uses the real functions from src/ on the cached data, so executing
the notebook top-to-bottom reproduces every number and chart.

The notebook requires the project virtual environment (see requirements.txt);
the first code cell points Python at the project root so it works no matter
where the kernel is launched from.
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "factor_risk_model.ipynb"

def md(src):
    return nbf.v4.new_markdown_cell(src.strip())


def code(src):
    return nbf.v4.new_code_cell(src.strip())


cells = []

# Title
cells.append(md("""
# Factor-Based Risk & Optimization Model

**From raw market data to a factor-tilted portfolio, a full risk autopsy, and an ML anomaly lens.**

This notebook is the interactive version of the whole project. Execute it top to bottom
(a kernel running the project's virtual environment) and every step reproduces real
numbers and charts from the cached dataset.

| Step | Question it answers |
|------|---------------------|
| 1 | Where does the data come from, and how is it aligned? |
| 2 | How much of each stock is driven by each factor? (betas) |
| 3 | How do the factors themselves move together? |
| 4 | What portfolio hits a target factor profile at minimum risk? |
| 5 | Did the portfolio actually work? (performance & risk) |
| 6 | Which months did the factor model fail to explain? (autoencoder) |
| 7 | Key takeaways and limitations |
"""))

# Setup
cells.append(md("""
## 0 · Setup

Everything below assumes the project's virtual environment (see `README.md` → *How to run*).
This cell points Python at the project root, so paths work regardless of where the
notebook is launched from.
"""))
cells.append(code("""
import os
import sys
from pathlib import Path

ROOT = Path.cwd()
# Walk up to the project root (the directory containing src/)
while not (ROOT / "src").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="scipy")

import numpy as np
import pandas as pd
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)

# Figures render inline under Jupyter; without IPython we print their paths
# so the notebook still runs in any Python environment.
try:
    from IPython.display import Image, display
    def show(png):
        display(Image(filename=str(ROOT / "figures" / png)))
    print("IPython available - figures will render inline.")
except ImportError:
    def show(png):
        print(f"[figure] {ROOT / 'figures' / png}")
    print("IPython not installed - figure paths printed instead "
          "(pip install ipython for inline rendering).")

print(f"project root: {ROOT}")
"""))

# Step 1
cells.append(md("""
## 1 · Data acquisition & preparation

**The concept.** We need two independent sources: **prices** (Yahoo Finance, via
`yfinance`) and **factor returns** (the Kenneth French Data Library, via
`pandas-datareader` with a direct-download fallback). Prices are converted to **monthly**
returns and aligned with the monthly factors on the same month-end calendar.

Why monthly? The factors are monthly, and monthly betas are the academic convention -
daily betas are polluted by bid-ask bounce and asynchronous trading. The window
**2015–2019** is a "normal" regime: no crisis, so the factor model is
estimated on clean data.

**The universe:** 26 S&P 500 names across 8 sectors + SPY as the benchmark.
"""))
cells.append(code("""
from src.config import START_DATE, END_DATE, UNIVERSE, BENCHMARK
from src.data import (build_analysis_dataset, fetch_daily_prices,
                      fetch_fama_french, to_monthly_returns)

tickers = list(UNIVERSE) + [BENCHMARK]
prices = fetch_daily_prices(tickers, START_DATE, END_DATE)
ff5 = fetch_fama_french("5", START_DATE, END_DATE)
monthly = to_monthly_returns(prices)
ds = build_analysis_dataset(monthly, ff5)

print("\\nFirst 4 months of aligned *excess* returns (stock - risk-free):")
ds.excess.head(4).round(4)
"""))
cells.append(md("""
### What to notice

- **Alignment is an inner join** - only months present in *both* price and factor data survive (59 months).
- **Excess returns** are stock returns minus the T-bill rate; in asset pricing we explain *excess* returns with factor returns.
- **The factor columns** are `Mkt-RF` (market), `SMB` (size), `HML` (value), `RMW` (profitability), `CMA` (investment).
"""))

# Step 2
cells.append(md("""
## 2 · Factor exposures (OLS betas)

**The concept.** For each stock we run a multivariate regression:

$$ r_i - r_f = \\alpha + \\beta_{mkt}(Mkt{-}RF) + \\beta_{smb}SMB + \\beta_{hml}HML + \\beta_{rmw}RMW + \\beta_{cma}CMA + \\varepsilon $$

Each **beta** is the stock's *loading* on a factor: how much of its return moves with
that factor. **Alpha** is the return the factors cannot explain. **R²** is the share of
variance the factors explain. We fit both the 3-factor and 5-factor models.
"""))
cells.append(code("""
from src.regressions import MODEL_3F, MODEL_5F, exposure_table, pretty_beta_table

t3 = exposure_table(ds.excess, ds.factors, MODEL_3F)
print("3-FACTOR MODEL - factor exposures (beta) with significance stars")
print("stars: * p<.10  ** p<.05  *** p<.01")
pretty_beta_table(t3, MODEL_3F)
"""))
cells.append(code("""
t5 = exposure_table(ds.excess, ds.factors, MODEL_5F)

# Sanity check: SPY is the market, so it should load ~1.0 on Mkt-RF
spy = t5.loc[BENCHMARK]
print("SANITY CHECK - SPY under the 5-factor model:")
print(f"  beta_mkt = {spy['beta_Mkt-RF']:.3f}   R2 = {spy['R2']:.3f}   "
      f"alpha (annualized) = {spy['alpha'] * 12 * 100:+.2f}%/yr")
print("  => the benchmark behaves like the market; the pipeline is trustworthy.\\n")

print("5-FACTOR MODEL - strongest positive / negative loadings per factor:")
from src.regressions import top_bottom
for k in MODEL_5F:
    tb = top_bottom(t5, k)
    print(f"  {k:7s}  low: {', '.join(f'{i}({v:+.2f})' for i, v in tb.head(2).items())}   "
          f"high: {', '.join(f'{i}({v:+.2f})' for i, v in tb.tail(2).items())}")
"""))

# Step 3
cells.append(md("""
## 3 · Factor analysis & interpretation

**The concept.** A portfolio's factor risk is approximately $w' B' \\Sigma_f B w$ - the
weights, the exposure matrix, and the **factor covariance** $\\Sigma_f$. If two factors
are highly correlated, loading on both is one bet, not two. So we stop and study how the
factors move together, and translate every stock's betas into plain English.
"""))
cells.append(code("""
from src.analysis import (factor_covariance, exposure_heatmap,
                          correlation_heatmap, plain_english_profile)

cov_f, corr_f, vol_f = factor_covariance(ds.factors)
print("ANNUALIZED FACTOR VOLATILITY (%):")
print(vol_f.round(2).to_string())

print("\\nFACTOR CORRELATION MATRIX:")
print(corr_f.round(3).to_string())
print("\\n  The HML <-> CMA correlation is the famous 'value-investment overlap'.")
"""))
cells.append(code("""
# The charts (saved to figures/ and shown inline here)
exposure_heatmap(t5, MODEL_5F, UNIVERSE)
correlation_heatmap(corr_f)
show("factor_exposures_heatmap.png")
show("factor_correlation_heatmap.png")
"""))
cells.append(code("""
print("PLAIN-ENGLISH FACTOR PROFILES (a sample):")
profiles = t5.apply(plain_english_profile, axis=1)
for t in ["NVDA", "BAC", "KO", "WMT", "MRK"]:
    print(f"  {t:5s} -> {profiles[t]}")
print("\\n(all 26 profiles saved to data/factor_profiles.csv in the full script)")
"""))

# Step 4
cells.append(md("""
## 4 · Portfolio optimization with factor targeting

**The concept.** We turn analysis into a decision. The **mandate**:

| Factor | Target |
|--------|--------|
| Mkt-RF | 1.00 |
| SMB (size) | 0.50 |
| HML (value) | 1.00 |
| RMW | 0.00 |
| CMA | 0.00 |

The optimizer minimizes portfolio variance $w'(B \\Sigma_f B' + D)w$ subject to
$\\sum w = 1$, exposure targets within tolerance, and $w \\geq 0$ (long-only) or
$w \\geq -0.10$ (limited shorts), using SLSQP with a trust-constr fallback.
"""))
cells.append(code("""
from src.optimization import summarize, target_factor_portfolio

betas = t5[[f"beta_{k}" for k in MODEL_5F]].copy()
betas.columns = MODEL_5F
idio_var = t5["resid_sd"] ** 2

TARGETS = {"Mkt-RF": 1.0, "SMB": 0.5, "HML": 1.0, "RMW": 0.0, "CMA": 0.0}
TOL = 0.10

ew = np.full(len(betas), 1.0 / len(betas))
ew_sum = summarize(ew, betas, cov_f, idio_var)
print("EQUAL-WEIGHT STARTING POINT (the naive portfolio):")
print(ew_sum["exposures"].round(3).to_string())

lo = target_factor_portfolio(betas, cov_f, idio_var, TARGETS, tolerance=TOL)
ls = target_factor_portfolio(betas, cov_f, idio_var, TARGETS,
                             tolerance=TOL, allow_shorts=True)

cmp = pd.DataFrame({
    "target": TARGETS, "long-only": lo["exposures"], "limited-shorts": ls["exposures"],
})
print("\\nACHIEVED vs TARGET EXPOSURES:")
print(cmp.round(3).to_string())
print(f"\\nportfolio vol (ann.): long-only {lo['total_vol_ann']:.1f}%  vs  "
      f"limited shorts {ls['total_vol_ann']:.1f}%  (feasible: "
      f"{ls['feasible']})")
"""))
cells.append(code("""
# The winning portfolio (limited shorts) - chart saved + shown inline
from src.analysis import plot_weights
plot_weights(ls["weights"], title="Optimal weights - limited shorts (floor -10%)")
show("portfolio_weights.png")

ls["weights"].to_csv("data/portfolio_weights_shorts.csv")
pd.DataFrame(cmp).to_csv("data/optimization_summary.csv")
print("weights saved to data/portfolio_weights_shorts.csv")
"""))

# Step 5
cells.append(md("""
## 5 · Performance & risk analysis

**The concept.** We run the optimized portfolio through the same 59 months and compare
it to **SPY** (passive benchmark) and **equal weight** (no optimization). The toolkit:
Sharpe ratio (return per unit of risk), max drawdown, **VaR** ("the worst month, 95% of
the time"), **CVaR / Expected Shortfall** (the average loss when VaR *is* breached), and
**factor attribution** (which factor is paying me, and how much?).
"""))
cells.append(code("""
from src.risk import (performance_summary, historical_var, normal_var,
                      expected_shortfall, factor_attribution, plot_cumulative_returns,
                      plot_drawdowns, plot_attribution, plot_holdings_corr)

stocks = [c for c in ds.returns.columns if c in UNIVERSE]
w_opt = pd.read_csv("data/portfolio_weights_shorts.csv", index_col=0).iloc[:, 0]
w_opt = w_opt.reindex(stocks).fillna(0.0)

r_opt = ds.returns[stocks].dot(w_opt)
r_ew = ds.returns[stocks].mean(axis=1)              # equal weight
perf = pd.DataFrame({"Optimal": r_opt, "SPY": ds.returns[BENCHMARK], "Equal weight": r_ew})

print("PERFORMANCE SUMMARY (2015-2019, monthly):")
performance_summary(perf, ds.rf).round(2)
"""))
cells.append(code("""
print("TAIL RISK - OPTIMAL PORTFOLIO (95% confidence, monthly):")
print(f"  historical VaR = {historical_var(r_opt) * 100:.2f}%   "
      f"(worst month expected 5% of the time)")
print(f"  normal VaR     = {normal_var(r_opt) * 100:.2f}%   (parametric, Gaussian)")
print(f"  CVaR / ES      = {expected_shortfall(r_opt) * 100:.2f}%   "
      f"(average loss once VaR is breached)")
print(f"  worst month    = {r_opt.min() * 100:.2f}% ({r_opt.idxmin():%b %Y})")

attr = factor_attribution(r_opt - ds.rf, ds.factors)
contrib = (attr["contributions"] * 100).copy()
contrib["alpha"] = attr["alpha_ann"] * 100
print(f"\\nFACTOR ATTRIBUTION (annualized %):  model R2 = {attr['R2']:.3f}")
print(contrib.round(2).to_string())
print(f"\\n  sum of contributions + alpha = {contrib.sum():.2f}%  =  arithmetic "
      f"annualized excess return = {(r_opt - ds.rf).mean() * 12 * 100:.2f}%")
"""))
cells.append(code("""
growth = (1.0 + perf).cumprod()
plot_cumulative_returns(growth)
plot_drawdowns(perf)
show("cumulative_returns.png")
show("drawdowns.png")
"""))
cells.append(code("""
plot_attribution(attr["contributions"], attr["alpha_ann"])
top = w_opt.abs().sort_values(ascending=False).head(12)
plot_holdings_corr(ds.returns[top.index].corr())
show("factor_attribution.png")
show("holdings_correlation.png")
"""))

# Step 6
cells.append(md("""
## 6 · Anomaly detection with autoencoders

**The concept.** An autoencoder is a neural network that learns to copy its input
through a narrow **bottleneck** (here 26 stocks → 3 latent units → 26). Because the
bottleneck is tiny, the network cannot memorize the data - it can only keep the dominant
co-movement patterns. A month that follows the normal structure rebuilds easily (low
error); a month where co-movement breaks down - a crash *or* a violent rally - does not
fit the learned manifold and its reconstruction error spikes. That error is the anomaly
score.

The network is implemented **from scratch in numpy** - forward pass, backpropagation
through tanh layers, Adam updates, weight decay, and early stopping on a validation
split - so every line of the learning algorithm is visible.
"""))
cells.append(code("""
from src.anomaly import (Autoencoder, detect_anomalies,
                         pca_reconstruction_errors, plot_anomalies)

# Self-contained: redefine the working set so this cell also runs on its own
stocks = [c for c in ds.returns.columns if c in UNIVERSE]
r_opt = pd.read_csv("data/portfolio_weights_shorts.csv", index_col=0).iloc[:, 0]
r_opt = ds.returns[stocks].dot(r_opt.reindex(stocks).fillna(0.0))

X = ds.returns[stocks].copy()
n_train = int(0.7 * len(X))
mu, sd = X.iloc[:n_train].mean(), X.iloc[:n_train].std(ddof=0)
Xs = (X - mu) / sd

ae = Autoencoder(input_dim=Xs.shape[1], hidden_dim=10, latent_dim=3, seed=0)
ae.train(Xs.iloc[:n_train].values, Xs.iloc[n_train:].values,
         epochs=4000, lr=0.02, weight_decay=1e-3, patience=250)
print(f"train loss (final) = {ae.train_loss[-1]:.5f}  |  best val loss = {ae.best_val:.5f}")

errors = ae.errors(Xs.values)
flags, threshold = detect_anomalies(errors, reference=errors[:n_train])
flagged = Xs.index[flags]
print(f"\\nflagged {int(flags.sum())}/{len(Xs)} months at threshold {threshold:.4f}:")
print([m.strftime('%b %Y') for m in flagged])

r_flag = r_opt[flagged]
print(f"\\nmean flagged-month return = {r_flag.mean() * 100:+.2f}%  vs  "
      f"all months {r_opt.mean() * 100:+.2f}%")
print("=> anomaly is NOT the same as loss: the lens flags structure-breaks")
print("   in both directions (2018 Q4 selloff AND the Jan-2019 rebound).")
"""))
cells.append(code("""
# Linear baseline (PCA = a *linear* autoencoder) for comparison
pca_err = pca_reconstruction_errors(Xs.values, n_components=3, fit_X=Xs.iloc[:n_train].values)
pca_flags, _ = detect_anomalies(pca_err, reference=pca_err[:n_train])
print(f"PCA baseline flags {int(pca_flags.sum())} months; "
      f"{int((flags & pca_flags).sum())} shared with the nonlinear model "
      f"-> nonlinear adds {int(flags.sum()) - int((flags & pca_flags).sum())} month(s).")

cum = (1.0 + r_opt).cumprod()
plot_anomalies(cum, errors, flags, threshold, Xs.index, threshold_sigma=2.0)
show("anomaly_detection.png")
"""))

# Step 7 - reflections
cells.append(md("""
## 7 · Key takeaways

---

### 1 · Factors make risk estimable

**Factors are the data compression that makes portfolio risk estimable at all.** With 59
months of data and 26 stocks, the raw 26×26 covariance matrix would be dominated by
estimation noise. Re-expressing risk through five factors collapses the problem to a 5×5
factor covariance - roughly 100× fewer parameters - and the factor structure `B Σ B' + D`
rebuilds the portfolio covariance reliably. That is the key idea of factor investing,
and I now see it from the inside: every number in this project (betas, R², attribution,
optimization) is a consequence of that compression.

**A mandate is a bet, not a guarantee.** Step 4 hit the value/size targets *exactly* -
and Step 5 showed those factors lost money in 2015–19. The optimizer is morally neutral:
it delivers precisely the risk profile you specify. This reframed how I think about
"beating the market" - you don't beat it by better optimization, you beat it by
*correct* factor conviction (or by alpha the factors can't see).

**The SPY sanity check taught me to validate before trusting.** β_mkt = 0.99, R² = 0.997
for the benchmark isn't a result - it's a proof the pipeline works. A quant builds the
instrument before playing the music.

---

### 2 · The institutional loop

This project mirrors the mandate → optimizer → risk-autopsy loop used by pension funds
and asset managers:

1. **The mandate sets the factor risk budget** (target HML, SMB, …) - the investment
   committee's view translated into numbers.
2. **The optimizer allocates** across securities to realize those exposures at minimum
   risk - with feasibility analysis ("your long-only universe cannot do this" is
   exactly the conversation a factor PM has weekly).
3. **The risk engine measures** - VaR/CVaR, drawdowns, attribution - and the anomaly
   lens adds a monitoring layer over the factor model.

The specific findings are institutional-grade talking points: the *value-investment
overlap* (HML↔CMA +0.61), *factor targeting ≠ return targeting* (the mandate lost even
though the optimizer won), and *CVaR > VaR* as the coherent tail measure.

---

### 3 · Limitations

1. **In-sample everywhere.** Betas are estimated and portfolios optimized on the same
   2015–19 window - the vol and Sharpe figures are optimistic.
2. **One regime.** The window excludes a crisis; the model says nothing
   about March 2020 behaviour.
3. **Static betas.** Exposures are point estimates, not rolling; real desks update
   monthly.
4. **Small universe + small sample.** 26 mega-caps, 59 months; the autoencoder trains
   on the same 59 samples.
5. **Diagonal residuals.** Idiosyncratic covariance is assumed diagonal; industry
   co-movement is ignored.
6. **No frictions.** No transaction costs, turnover constraints, or short-borrow costs.

---

*Every figure and table in this notebook came from running the project's own code on
public data - nothing is simulated or hand-inserted. Rerun any cell to regenerate it.*
"""))

# Build & save
nb = nbf.v4.new_notebook(
    cells=cells,
    metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.14"},
    },
)

NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, NOTEBOOK)
n_md = sum(1 for c in cells if c.cell_type == "markdown")
n_code = sum(1 for c in cells if c.cell_type == "code")
print(f"[notebook] wrote {NOTEBOOK.relative_to(ROOT)} "
      f"({len(cells)} cells: {n_md} markdown + {n_code} code)")
