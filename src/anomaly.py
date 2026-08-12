"""
Step 6 - Anomaly detection with autoencoders
=============================================
The factor model (Steps 2-5) explains "normal" return co-movement through
five factors.  This step asks the complementary question: *which months
do not look normal at all?*  We train a tiny autoencoder - a neural
network that learns to reproduce its input through a narrow bottleneck -
on the monthly cross-section of stock returns, and use its
reconstruction error as an anomaly score.

Why an autoencoder works as a novelty detector:

    A month that follows the usual co-movement patterns (the learned
    "normal" structure) is easy to compress and rebuild faithfully, so
    its reconstruction error is small.  A month where the usual
    relationships break down - a crash, a sector shock, a liquidity
    event - does not fit the learned manifold, so the network struggles
    to rebuild it and the error spikes.

Why the bottleneck matters:

    With only 59 monthly observations and 26 features, the network would
    otherwise just memorize every month (reconstruction error -> 0
    everywhere, no signal).  The tiny latent layer (3 units) *forces*
    compression: the model can only keep the dominant co-movement modes,
    so only genuinely unusual months are hard to rebuild.  In practice
    you would train on daily data (thousands of samples) where this is
    far less delicate; here it is a controlled demonstration.

The autoencoder is implemented from scratch in numpy (explicit forward
pass, backpropagation, Adam updates) so the mechanics are fully visible
- no black-box neural-network library involved.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")          # headless-safe backend (no GUI needed)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from src.analysis import apply_style
from src.config import FIGURES_DIR

ACCENT = "#F8F8F8"
NEG = "#E5484D"
YELLOW = "#B4B4B4"


# ----------------------------------------------------------------------
# The autoencoder
# ----------------------------------------------------------------------
class Autoencoder:
    """Fully-connected autoencoder with explicit numpy backpropagation.

    Architecture:  input -> tanh hidden -> tanh latent(3) -> tanh hidden -> linear output.
    The latent layer is the "bottleneck" that forces compression.

    Adam optimizer with L2 weight decay; early stopping on a validation
    split so the model generalizes instead of memorizing.
    """

    def __init__(self, input_dim, hidden_dim=10, latent_dim=3, seed=0):
        rng = np.random.default_rng(seed)
        # Xavier/Glorot initialization: scale by 1/sqrt(fan_in) keeps the
        # pre-activation variances stable across layers during backprop.
        def layer(fan_in, fan_out):
            return rng.normal(0.0, np.sqrt(2.0 / (fan_in + fan_out)),
                              size=(fan_in, fan_out))

        self.W1 = layer(input_dim, hidden_dim)
        self.b1 = np.zeros(hidden_dim)
        self.W2 = layer(hidden_dim, latent_dim)
        self.b2 = np.zeros(latent_dim)
        self.W3 = layer(latent_dim, hidden_dim)
        self.b3 = np.zeros(hidden_dim)
        self.W4 = layer(hidden_dim, input_dim)
        self.b4 = np.zeros(input_dim)

        self.train_loss = []
        self.val_loss = []
        self.best_val = None

    # -- forward ----------------------------------------------------------
    def _forward(self, X):
        """Propagate input through the network, caching activations for backprop."""
        z1 = X @ self.W1 + self.b1
        a1 = np.tanh(z1)
        z2 = a1 @ self.W2 + self.b2
        a2 = np.tanh(z2)                 # latent representation (bottleneck)
        z3 = a2 @ self.W3 + self.b3
        a3 = np.tanh(z3)
        out = a3 @ self.W4 + self.b4     # linear output layer (no squash)
        return out, {"X": X, "z1": z1, "a1": a1, "z2": z2, "a2": a2,
                     "z3": z3, "a3": a3}

    # -- backward ---------------------------------------------------------
    def _backward(self, X, cache, dout):
        """Backpropagate the reconstruction gradient, returning parameter grads."""
        grads = {}
        a3, a2, a1, z3, z2, z1 = (cache["a3"], cache["a2"], cache["a1"],
                                  cache["z3"], cache["z2"], cache["z1"])

        dz4 = dout                                        # dL/d(out)
        grads["W4"] = a3.T @ dz4 / len(X)
        grads["b4"] = dz4.mean(axis=0)
        da3 = dz4 @ self.W4.T
        dz3 = da3 * (1.0 - np.tanh(z3) ** 2)              # tanh' (z)
        grads["W3"] = a2.T @ dz3 / len(X)
        grads["b3"] = dz3.mean(axis=0)
        da2 = dz3 @ self.W3.T
        dz2 = da2 * (1.0 - np.tanh(z2) ** 2)
        grads["W2"] = a1.T @ dz2 / len(X)
        grads["b2"] = dz2.mean(axis=0)
        da1 = dz2 @ self.W2.T
        dz1 = da1 * (1.0 - np.tanh(z1) ** 2)
        grads["W1"] = X.T @ dz1 / len(X)
        grads["b1"] = dz1.mean(axis=0)
        return grads

    # -- training ---------------------------------------------------------
    def train(self, X, val_X=None, epochs=4000, lr=0.02,
              weight_decay=1e-3, patience=200, seed=0):
        """Adam-optimized training with early stopping on validation loss.

        weight_decay shrinks weights toward zero every step - a gentle
        regularizer that, together with the tiny bottleneck, prevents
        the model from memorizing all 59 months.
        """
        rng = np.random.default_rng(seed)
        # Adam moment accumulators
        m = {k: np.zeros_like(v) for k, v in self._params().items()}
        v = {k: np.zeros_like(v) for k, v in self._params().items()}
        beta1, beta2, eps = 0.9, 0.999, 1e-8

        best_val = np.inf
        best_weights = None
        patience_left = patience

        for epoch in range(1, epochs + 1):
            out, cache = self._forward(X)
            loss = 0.5 * float(np.mean((out - X) ** 2))
            # Gradient of the loss w.r.t. the output layer.  The 1/N batch
            # averaging happens in _backward (each weight gradient divides
            # by len(X)), so this is the plain residual - no extra /N here,
            # otherwise every gradient would be N times too small.
            dout = out - X

            grads = self._backward(X, cache, dout)
            t = epoch
            for k in self._params():
                g = grads[k] + weight_decay * self._params()[k]   # L2 term
                m[k] = beta1 * m[k] + (1 - beta1) * g
                v[k] = beta2 * v[k] + (1 - beta2) * g ** 2
                m_hat = m[k] / (1 - beta1 ** t)
                v_hat = v[k] / (1 - beta2 ** t)
                self.__dict__[k] -= lr * m_hat / (np.sqrt(v_hat) + eps)

            self.train_loss.append(loss)
            if val_X is not None:
                vloss = 0.5 * float(np.mean((self._forward(val_X)[0] - val_X) ** 2))
                self.val_loss.append(vloss)
                if vloss < best_val - 1e-6:
                    best_val = vloss
                    best_weights = {k: self.__dict__[k].copy() for k in self._params()}
                    patience_left = patience
                else:
                    patience_left -= 1
                    if patience_left <= 0:
                        break                                # early stop
            else:
                best_weights = {k: self.__dict__[k].copy() for k in self._params()}

        if best_weights is not None:
            for k, w in best_weights.items():
                self.__dict__[k] = w
        self.best_val = best_val
        return self

    def _params(self):
        return {k: self.__dict__[k] for k in
                ("W1", "b1", "W2", "b2", "W3", "b3", "W4", "b4")}

    def reconstruct(self, X):
        return self._forward(X)[0]

    def errors(self, X):
        """Per-sample reconstruction error (MSE over features)."""
        out = self.reconstruct(X)
        return np.mean((out - X) ** 2, axis=1)


# ----------------------------------------------------------------------
# PCA baseline (a *linear* autoencoder)
# ----------------------------------------------------------------------
def pca_reconstruction_errors(X, n_components=3, fit_X=None):
    """Reconstruction errors of PCA with n_components latent dims.

    PCA is the linear special case of an autoencoder: project onto the
    top-k principal components and project back.  Comparing its flagged
    months to the nonlinear autoencoder's shows whether the nonlinear
    structure adds anything over plain linear compression.

    fit_X lets the caller fit the PCA on the training months only, so the
    baseline has no validation leakage (defaults to fitting on X itself).
    """
    fit = X if fit_X is None else fit_X
    pca = PCA(n_components=n_components)
    pca.fit(fit)
    scores = pca.transform(X)
    rebuilt = pca.inverse_transform(scores)
    return np.mean((rebuilt - X) ** 2, axis=1)


# ----------------------------------------------------------------------
# Anomaly scoring
# ----------------------------------------------------------------------
def detect_anomalies(errors, reference=None, threshold_sigma=2.0):
    """Flag samples whose error exceeds mean + k*sigma of the reference.

    The threshold is set by the *reference* errors - pass the training
    ("normal") months so anomalies cannot inflate their own bar.
    Returns (flags, threshold).
    """
    ref = (np.asarray(reference, dtype=float) if reference is not None
           else np.asarray(errors, dtype=float))
    err = np.asarray(errors, dtype=float)
    threshold = float(np.mean(ref) + threshold_sigma * np.std(ref))
    flags = err > threshold
    return flags, threshold


# ----------------------------------------------------------------------
# Chart
# ----------------------------------------------------------------------
def plot_anomalies(portfolio_cum, recon_errors, flags, threshold, months,
                   path=None, threshold_sigma=2.0,
                   title="Autoencoder anomaly detection - monthly cross-section"):
    """Two-panel chart: reconstruction error (lens) above the portfolio
    wealth path (context) with flagged months shaded in both."""
    apply_style()
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 7), sharex=True,
        gridspec_kw={"height_ratios": [1.6, 1.0]})

    err = np.asarray(recon_errors, dtype=float)
    # Panel 1: reconstruction error with the anomaly threshold
    ax1.plot(months, err, color=ACCENT, lw=1.6, label="reconstruction error")
    ax1.axhline(threshold, color=NEG, ls="--", lw=1.2,
                label=f"threshold (mean + {threshold_sigma:g}σ = {threshold:.4f})")
    for i, m in enumerate(months):
        if flags[i]:
            ax1.scatter(m, err[i], color=NEG, s=46, zorder=5, edgecolor="none")
    ax1.set_ylabel("reconstruction error (MSE)")
    ax1.set_title(title)
    ax1.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax1.grid(True, alpha=0.3)

    # Panel 2: portfolio wealth path, flagged months shaded
    ax2.plot(months, portfolio_cum, color=YELLOW, lw=1.8, label="optimal portfolio")
    for i, m in enumerate(months):
        if flags[i]:
            ax2.axvspan(m - pd.Timedelta(days=14), m + pd.Timedelta(days=14),
                        color=NEG, alpha=0.22)
    ax2.set_ylabel("growth of $1")
    ax2.set_xlabel("")
    ax2.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    if path is None:
        path = FIGURES_DIR / "anomaly_detection.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[anomaly] saved {path.name}")
    return path
