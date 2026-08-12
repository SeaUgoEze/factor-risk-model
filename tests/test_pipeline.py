"""End-to-end pipeline tests: full run on cached data, <30s (spec Phase 5)."""
from __future__ import annotations

import time

import pytest

from factor_risk_model.pipeline import run_pipeline


def test_full_pipeline_runs_and_has_all_outputs():
    """Default 10-stock config: every deliverable table + figure present."""
    res = run_pipeline(["AAPL", "MSFT", "JPM", "XOM", "JNJ", "PG",
                        "AMZN", "META", "CAT", "BA"],
                       "2015-01-01", "2019-12-31")

    assert len(res.weights) == 10
    assert abs(res.weights.sum() - 1.0) < 1e-6
    assert "Optimal" in res.risk_summary.index
    assert "SPY" in res.risk_summary.index
    assert set(res.stress.index) == {"COVID crash (Mar-2020 style)",
                                     "GFC crisis (2008 style)",
                                     "Rate-shock selloff (2022 style)",
                                     "Tech-bubble pop (2000 style)"}
    assert res.attribution["R2"] > 0.3
    assert res.anomaly is not None
    assert res.anomaly.threshold > 0
    for key in ("exposures", "weights", "cumulative", "drawdowns",
                "attribution", "stress", "anomaly", "ci"):
        assert res.figures[key].exists(), f"missing figure {key}"
    assert len(res.interpretation()) >= 5


def test_pipeline_completes_under_30_seconds():
    """Performance budget (spec: < 30s for ~30 stocks, 5 years)."""
    t0 = time.perf_counter()
    run_pipeline(["AAPL", "MSFT", "JPM", "XOM", "JNJ", "PG",
                  "AMZN", "META", "CAT", "BA"],
                 "2015-01-01", "2019-12-31")
    elapsed = time.perf_counter() - t0
    assert elapsed < 30, f"pipeline took {elapsed:.1f}s"


def test_pipeline_rejects_bad_tickers():
    with pytest.raises(ValueError, match="No usable price data"):
        run_pipeline(["ZZZZ"], "2015-01-01", "2019-12-31")


def test_heatmap_survives_many_sectors(tmp_path):
    """Regression: >9 sectors (custom tickers -> 'Other', plus SPY) used to
    truncate the color palette and KeyError on 'Benchmark'. The engine now
    cycles colors, so this must render."""
    from src.analysis import exposure_heatmap
    res = run_pipeline(["AAPL", "MSFT", "JPM"], "2015-01-01", "2019-12-31")
    # 10 distinct fake sectors + the implicit Benchmark = 11 > 9 colors
    sector_map = {t: f"S{i}" for i, t in enumerate(res.tickers)}
    path = exposure_heatmap(res.exposures, ["Mkt-RF", "SMB", "HML", "RMW",
                                            "CMA"],
                            sector_map, tmp_path / "many_sectors.png")
    assert path.exists() and path.stat().st_size > 1000


def test_exports_produce_files(tmp_path):
    from factor_risk_model.utils.export import (export_csv, export_excel,
                                                export_html, export_pdf)
    res = run_pipeline(["AAPL", "MSFT", "JPM"], "2015-01-01", "2019-12-31")

    csvs = export_csv(res, tmp_path)
    assert len(csvs) == 6 and all(p.exists() for p in csvs)

    xl = export_excel(res, tmp_path / "report.xlsx")
    assert xl.exists() and xl.stat().st_size > 0

    pdf = export_pdf(res, res.figures, tmp_path / "report.pdf")
    assert pdf.exists() and pdf.stat().st_size > 1000

    html = export_html(res, tmp_path / "report.html")
    text = html.read_text(encoding="utf-8")
    assert "Factor risk report" in text
    assert "Times New Roman" in text


def test_pdf_cover_text_is_actually_visible(tmp_path):
    """Regression: transAxes rules used to autoscale the cover axes to a
    tiny range, silently pushing every data-coordinate text (title, meta,
    Contents, key findings) off-page - the PDF looked empty yet passed the
    size check. Extract the rendered text and assert the cover content is
    really there, including the Contents page numbers."""
    pdfium = pytest.importorskip("pypdfium2")
    from factor_risk_model.utils.export import export_pdf
    res = run_pipeline(["AAPL", "MSFT", "JPM"], "2015-01-01", "2019-12-31")

    pdf = export_pdf(res, res.figures, tmp_path / "report.pdf")
    doc = pdfium.PdfDocument(str(pdf))
    # 1 cover + one page per chart (incl. the 95%-CI chart)
    assert len(doc) == 9, f"expected 9 pages, got {len(doc)}"
    text = doc[0].get_textpage().get_text_bounded()
    for needle in ("Factor risk report", "Contents", "Key findings",
                   "Factor exposures", "Anomaly detection"):
        assert needle in text, f"cover text missing: {needle!r}"
    # the Contents section must carry true page numbers
    assert "Exposures with 95% CI 3" in text
    assert "Anomaly detection 9" in text
    # and the last page must carry its own footer stamp
    last = doc[len(doc) - 1].get_textpage().get_text_bounded()
    assert "Report generated" in last
