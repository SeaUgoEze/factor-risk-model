"""Command-line interface (Mode B).

Reproducible, scriptable runs:

    python main.py --stocks AAPL MSFT JPM --target_hml 0.7 --no-shorts
    python main.py --stocks AAPL MSFT --model 3-factor --export all

Every run writes tables + reports under ``outputs/reports/<stamp>/`` and
prints a condensed summary to the terminal - the same numbers the
interactive app shows, because both call ``run_pipeline``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from factor_risk_model.config import (DEFAULT_FACTOR_MODEL,
                                      DEFAULT_TICKERS, END_DATE, SHORT_FLOOR,
                                      START_DATE, TARGET_DEFAULTS)
from factor_risk_model.pipeline import run_pipeline
from factor_risk_model.utils.export import (export_csv, export_excel,
                                            export_html, export_pdf)
from factor_risk_model.utils.helpers import report_stamp

_OUT = Path(__file__).resolve().parents[2] / "outputs" / "reports"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="factor-risk-model",
        description="Factor-based risk & optimization model - CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--stocks", "-s", nargs="+", default=DEFAULT_TICKERS,
                   help="Stock tickers (space separated)")
    p.add_argument("--start", default=START_DATE, help="Window start YYYY-MM-DD")
    p.add_argument("--end", default=END_DATE, help="Window end YYYY-MM-DD")
    p.add_argument("--model", choices=["3-factor", "5-factor"],
                   default=DEFAULT_FACTOR_MODEL, help="Fama-French model")
    p.add_argument("--tolerance", type=float, default=0.10,
                   help="Max |achieved - target| per factor")
    p.add_argument("--no-shorts", action="store_true",
                   help="Long-only portfolio (may be infeasible)")
    p.add_argument("--short-floor", type=float, default=SHORT_FLOOR,
                   help="Min weight when shorts are allowed")
    p.add_argument("--max-vol", type=float, default=None,
                   help="Vol budget warning threshold (e.g. 0.20)")
    p.add_argument("--export", choices=["none", "csv", "excel", "pdf",
                                        "html", "all"],
                   default="all", help="Report artifacts to write")
    p.add_argument("--out", type=Path, default=_OUT, help="Report directory")
    for k, v in TARGET_DEFAULTS.items():
        p.add_argument(f"--target-{k.lower().replace('-', '_')}", type=float,
                       default=v, help=f"Target loading on {k}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    targets = {k: getattr(args, f"target_{k.lower().replace('-', '_')}")
               for k in TARGET_DEFAULTS}
    if args.model == "3-factor":
        targets = {k: v for k, v in targets.items() if k in
                   ("Mkt-RF", "SMB", "HML")}

    print(f"\nFACTOR RISK MODEL - {args.model} | {args.stocks}")
    print(f"window {args.start}..{args.end} | mandate {targets} | "
          f"shorts={'yes' if not args.no_shorts else 'no'}\n")

    try:
        result = run_pipeline(
            args.stocks, args.start, args.end, factor_model=args.model,
            targets=targets, tolerance=args.tolerance,
            allow_shorts=not args.no_shorts, short_floor=args.short_floor,
            max_vol=args.max_vol)
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Terminal summary
    print("EXPOSURES (beta [95% CI]):")
    print(result.exposures[["alpha"] +
                           [f"beta_{k}" for k in
                            ("Mkt-RF", "SMB", "HML", "RMW", "CMA")
                            if f"beta_{k}" in result.exposures]].
          round(3).to_string())
    print("\nTARGET vs ACHIEVED:")
    print(result.optimizer["comparison"].to_string())
    print(f"\nPORTFOLIO VOL: {result.optimizer['total_vol_ann']:.1f}% "
          f"(factor {result.optimizer['factor_vol_ann']:.1f}% + idio "
          f"{result.optimizer['idio_vol_ann']:.1f}%)")
    print("\nRISK SUMMARY:")
    print(result.risk_summary.round(2).to_string())
    print("\nSTRESS (one-month impact %):")
    print(result.stress.to_string())
    print("\nINTERPRETATION:")
    for b in result.interpretation():
        print(f"  - {b}")

    for w in result.optimization_warnings:
        print(f"\nWARNING: {w}")

    # Exports
    if args.export != "none":
        out_dir = args.out / report_stamp()
        if args.export in ("csv", "all"):
            paths = export_csv(result, out_dir)
            print(f"\n[export] CSV -> {out_dir}")
        if args.export in ("excel", "all"):
            xl = export_excel(result, out_dir / "report.xlsx")
            print(f"[export] Excel -> {xl}")
        if args.export in ("pdf", "all"):
            pdf = export_pdf(result, result.figures, out_dir / "report.pdf")
            print(f"[export] PDF   -> {pdf}")
        if args.export in ("html", "all"):
            html = export_html(result, out_dir / "report.html")
            print(f"[export] HTML  -> {html}")

    print("\ndone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
