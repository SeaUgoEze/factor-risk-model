"""User-facing interfaces - built in Step 6.

    streamlit_app.py  interactive web dashboard: ticker picker, date range,
                      factor mandate sliders, constraints, run button,
                      tabbed results, and CSV / Excel / PDF downloads.
    cli.py            argparse command-line interface for scripted runs
                      (``python main.py --stocks AAPL MSFT --target_value 0.7``).

Both interfaces call the same ``run_pipeline()`` orchestration, so every
interface produces identical numbers.
"""
