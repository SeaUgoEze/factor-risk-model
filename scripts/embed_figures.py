"""
Embed generated figures into docs/index.html as base64 data URIs.
==================================================================
The Preview tab serves docs/index.html as a single file, so <img>
tags pointing at ../figures/... would 404.  Embedding keeps the page
fully self-contained.  Run after any step that regenerates figures:

    python scripts/embed_figures.py
"""
import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "docs" / "index.html"

# marker in the HTML -> (PNG file, <img> id) to embed
MAPPING = {
    "PLACEHOLDER_HEATMAP": (ROOT / "figures" / "factor_exposures_heatmap.png", "fig-heatmap"),
    "PLACEHOLDER_CORR": (ROOT / "figures" / "factor_correlation_heatmap.png", "fig-corr"),
    "PLACEHOLDER_WEIGHTS": (ROOT / "figures" / "portfolio_weights.png", "fig-weights"),
    "PLACEHOLDER_CUMRET": (ROOT / "figures" / "cumulative_returns.png", "fig-cumret"),
    "PLACEHOLDER_DRAWDOWN": (ROOT / "figures" / "drawdowns.png", "fig-drawdown"),
    "PLACEHOLDER_ATTRIB": (ROOT / "figures" / "factor_attribution.png", "fig-attrib"),
    "PLACEHOLDER_HOLDCORR": (ROOT / "figures" / "holdings_correlation.png", "fig-holdcorr"),
    "PLACEHOLDER_ANOMALY": (ROOT / "figures" / "anomaly_detection.png", "fig-anomaly"),
}


def main():
    if not HTML.exists():
        raise SystemExit(f"not found: {HTML}")
    html = HTML.read_text(encoding="utf-8")

    for marker, (png, img_id) in MAPPING.items():
        # Reset any previously embedded data URI back to the placeholder so
        # re-running always refreshes figures that changed on disk.
        html = re.sub(
            rf'(<img id="{img_id}" src=")data:image/png;base64,[^"]*(")',
            rf"\1{marker}\2",
            html,
        )
        if marker not in html:
            print(f"[embed] skip {marker} (img not present in HTML)")
            continue
        if not png.exists():
            print(f"[embed] WARNING: {png} missing - leaving placeholder")
            continue
        b64 = base64.b64encode(png.read_bytes()).decode("ascii")
        html = html.replace(f'src="{marker}"', f'src="data:image/png;base64,{b64}"')
        print(f"[embed] {png.name}: {len(b64) // 1024} KB embedded")

    HTML.write_text(html, encoding="utf-8")
    print("[embed] docs/index.html updated")


if __name__ == "__main__":
    main()
