"""
Step 6 - Anomaly detection with autoencoders
=============================================
Run:  python scripts/step6_anomaly.py

Trains a small numpy autoencoder on the monthly cross-section of the 26
stocks' returns (59 months x 26 features), then uses reconstruction
error as an anomaly score.  Months the network struggles to rebuild are
flagged and cross-checked against the portfolio's own worst months.

Outputs:
  * anomaly flags + table under outputs/
  * two-panel chart under figures/anomaly_detection.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

pd.set_option("display.width", 210)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 80)

from src.config import (START_DATE, END_DATE, UNIVERSE, BENCHMARK,
                        DATA_DIR, FIGURES_DIR, OUTPUTS_DIR)
from src.data import (build_analysis_dataset, fetch_daily_prices,
                      fetch_fama_french, to_monthly_returns)
from src.anomaly import (Autoencoder, detect_anomalies,
                         pca_reconstruction_errors, plot_anomalies)


def main():
    print("=" * 92)
    print("STEP 6 - ANOMALY DETECTION WITH AUTOENCODERS")
    print(f"window {START_DATE} -> {END_DATE} | "
          f"{len(UNIVERSE)} stocks | 59 monthly cross-sections")
    print("=" * 92)

    # ---- data: the monthly cross-section of stock returns ----------------
    tickers = list(UNIVERSE) + [BENCHMARK]
    prices = fetch_daily_prices(tickers, START_DATE, END_DATE)
    ff5 = fetch_fama_french("5", START_DATE, END_DATE)
    monthly = to_monthly_returns(prices)
    ds = build_analysis_dataset(monthly, ff5)

    stocks = [c for c in ds.returns.columns if c in UNIVERSE]
    X = ds.returns[stocks].copy()

    # Standardize per stock (z-score).  Fit the scaler on the TRAIN months
    # only so test/validation months don't leak their statistics in.
    n_train = int(0.7 * len(X))
    mu, sd = X.iloc[:n_train].mean(), X.iloc[:n_train].std(ddof=0)
    Xs = (X - mu) / sd
    X_train, X_val = Xs.iloc[:n_train], Xs.iloc[n_train:]

    # ---- train the autoencoder -------------------------------------------
    print(f"\n1) TRAINING autoencoder ({X.shape[1]} -> 10 -> 3 -> 10 -> "
          f"{X.shape[1]}), early stopping on the last {len(X_val)} months")
    ae = Autoencoder(input_dim=X.shape[1], hidden_dim=10, latent_dim=3, seed=0)
    ae.train(X_train.values, X_val.values, epochs=4000, lr=0.02,
             weight_decay=1e-3, patience=250)
    print(f"   train loss (final) = {ae.train_loss[-1]:.5f}  |  "
          f"best val loss = {ae.best_val:.5f}  |  "
          f"epochs used = {len(ae.train_loss)}")

    # ---- reconstruction errors + anomaly flags -----------------------------
    errors = ae.errors(Xs.values)
    flags, threshold = detect_anomalies(errors, reference=errors[:n_train])
    flagged_months = Xs.index[flags]
    print(f"\n2) ANOMALY SCORES: threshold (train mean + 2 std) = {threshold:.4f}")
    print(f"   flagged {int(flags.sum())}/{len(Xs)} months: "
          f"{[m.strftime('%b %Y') for m in flagged_months]}")

    # ---- cross-check with the portfolio's own worst months -----------------
    # Optimal portfolio monthly returns from the Step-4 weights
    w = pd.read_csv(DATA_DIR / "portfolio_weights_shorts.csv",
                    index_col=0).iloc[:, 0].reindex(stocks).fillna(0.0)
    r_opt = ds.returns[stocks].dot(w)

    print("\n3) CROSS-CHECK - flagged months vs the portfolio's returns:")
    if len(flagged_months):
        tbl = pd.DataFrame({
            "portfolio_ret_%": r_opt[flagged_months] * 100,
            "recon_error": errors[flags],
        }).round(3)
        print(tbl.to_string())
        print(f"   mean flagged-month return = "
              f"{r_opt[flagged_months].mean() * 100:+.2f}%  vs  all months "
              f"{r_opt.mean() * 100:+.2f}%")
    else:
        print("   (none flagged - the model found every month 'normal')")

    # ---- PCA baseline: a LINEAR autoencoder ---------------------------------
    pca_err = pca_reconstruction_errors(Xs.values, n_components=3,
                                        fit_X=X_train.values)
    pca_flags, _ = detect_anomalies(pca_err, reference=pca_err[:n_train])
    overlap = int((flags & pca_flags).sum())
    print(f"\n4) LINEAR BASELINE (PCA, 3 components): flags "
          f"{int(pca_flags.sum())} months, {overlap} shared with the "
          f"autoencoder -> the nonlinear model adds "
          f"{int(flags.sum()) - overlap} month(s) the linear one missed")

    # ---- figure: error lens above portfolio wealth path ---------------------
    cum = (1.0 + r_opt).cumprod()
    plot_anomalies(cum, errors, flags, threshold, Xs.index,
                   FIGURES_DIR / "anomaly_detection.png", threshold_sigma=2.0)

    # ---- persistence ---------------------------------------------------------
    summary = pd.DataFrame({
        "recon_error": errors,
        "flagged": flags,
        "portfolio_ret": r_opt,
    }, index=Xs.index)
    summary.round(5).to_csv(OUTPUTS_DIR / "anomaly_summary.csv")
    print("\n[done] figure under figures/anomaly_detection.png ; "
          "table under outputs/anomaly_summary.csv")


if __name__ == "__main__":
    main()
