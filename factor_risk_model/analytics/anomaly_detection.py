"""Windowed anomaly detection on the portfolio's own daily returns.

The spec's architecture: feed *10-day rolling windows* of portfolio
returns through a narrow autoencoder (10 -> 4 -> 2 -> 4 -> 10), train on
normal periods, and flag windows whose reconstruction error clears the
95th percentile of training error.

A single daily return is mostly noise; a sequence of returns encodes the
co-movement pattern, and a period where that pattern breaks (a crash, a
violent rally, a regime shift) reconstructs poorly.

The network is the engine's hand-rolled numpy ``Autoencoder`` (tanh MLP,
explicit backprop, Adam).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.anomaly import Autoencoder

DEFAULT_WINDOW = 10
DEFAULT_ENCODING_DIM = 2
TRAIN_FRACTION = 0.8
THRESHOLD_PERCENTILE = 95.0


@dataclass
class AnomalyResult:
    """Output of the windowed detector."""

    errors: np.ndarray          # reconstruction error per window
    flags: np.ndarray           # bool mask of anomalous windows
    window_end_dates: pd.DatetimeIndex
    threshold: float            # error above which a window is anomalous
    train_errors: np.ndarray    # errors on the training (normal) windows
    flagged_windows: pd.DataFrame  # date / error / mean daily return table


class PortfolioAnomalyDetector:
    """Detect structure-breaks in a portfolio's daily return stream."""

    def __init__(self, window_size: int = DEFAULT_WINDOW,
                 encoding_dim: int = DEFAULT_ENCODING_DIM, seed: int = 0):
        self.window_size = window_size
        self.encoding_dim = encoding_dim
        self.seed = seed
        self.model: Autoencoder | None = None
        self.threshold: float | None = None

    @staticmethod
    def build_windows(returns: pd.Series, window: int) -> tuple[np.ndarray,
                                                                pd.DatetimeIndex]:
        """Rolling windows -> (n_windows x window) array + end dates.

        Windows are *overlapping* (stride 1) so no short event slips
        between two non-overlapping buckets.
        """
        vals = returns.to_numpy(dtype=float)
        if len(vals) < window:
            raise ValueError(
                f"Need at least {window} daily returns for anomaly windows "
                f"(got {len(vals)}).")
        rows = np.lib.stride_tricks.sliding_window_view(vals, window)
        ends = returns.index[window - 1:]
        return rows, pd.DatetimeIndex(ends)

    def fit(self, returns: pd.Series, train_fraction: float = TRAIN_FRACTION):
        """Train on the first ``train_fraction`` of windows (normal period)
        and set the 95th-percentile error threshold from them."""
        X, ends = self.build_windows(returns, self.window_size)
        n_train = max(1, int(len(X) * train_fraction))
        X_train, X_val = X[:n_train], X[n_train:]

        self.model = Autoencoder(input_dim=self.window_size,
                                 hidden_dim=4, latent_dim=self.encoding_dim,
                                 seed=self.seed)
        self.model.train(X_train, val_X=X_val if len(X_val) else None,
                         epochs=2000, lr=0.02, patience=150)

        self.train_errors = self.model.errors(X_train)
        self.threshold = float(np.percentile(self.train_errors,
                                             THRESHOLD_PERCENTILE))
        return self

    def detect(self, returns: pd.Series) -> AnomalyResult:
        """Score every window and flag those above the threshold."""
        if self.model is None or self.threshold is None:
            raise RuntimeError("Call fit() before detect().")
        X, ends = self.build_windows(returns, self.window_size)
        errors = self.model.errors(X)
        flags = errors > self.threshold

        # Mean daily return inside each window (to show anomaly != loss).
        daily = returns.to_numpy(dtype=float)
        win_means = np.array([daily[i:i + self.window_size].mean()
                              for i in range(len(daily) - self.window_size + 1)])

        flagged = pd.DataFrame({
            "window_end": ends,
            "recon_error": errors,
            "window_mean_daily_%": win_means * 100,
        }, index=ends)[flags]
        flagged = flagged.sort_index()

        return AnomalyResult(
            errors=errors, flags=flags, window_end_dates=ends,
            threshold=self.threshold, train_errors=self.train_errors,
            flagged_windows=flagged,
        )

    def interpretation(self, result: AnomalyResult,
                       all_returns: pd.Series) -> list[str]:
        """Plain-English takeaway from a detection run."""
        n_all = int(result.flags.sum())
        frac = n_all / len(result.flags) * 100
        all_avg = all_returns.mean() * 100
        bullets = [
            f"Model: {self.window_size}-day windows through a "
            f"{self.window_size}->4->{self.encoding_dim}->4->{self.window_size} "
            f"autoencoder; {n_all}/{len(result.flags)} windows flagged "
            f"({frac:.0f}%) at the {THRESHOLD_PERCENTILE:.0f}th-percentile "
            "error threshold.",
        ]
        if n_all:
            flag_avg = result.flagged_windows["window_mean_daily_%"].mean()
            bullets.append(
                f"Mean daily return of flagged windows: {flag_avg:+.2f}% vs "
                f"{all_avg:+.2f}% for all days - an anomaly is a *structure "
                "break*, not necessarily a loss.")
        if len(result.flagged_windows):
            dates = result.flagged_windows.index.strftime("%Y-%m")
            bullets.append("Flagged periods: " + ", ".join(dates[:8])
                           + ("..." if len(dates) > 8 else "") + ".")
        return bullets
