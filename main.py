#!/usr/bin/env python
"""Entry point for the command-line interface.

    python main.py --stocks AAPL MSFT JPM --target_hml 0.7
    python main.py --help

The interactive web dashboard lives in
``factor_risk_model/interface/streamlit_app.py`` (run with
``streamlit run factor_risk_model/interface/streamlit_app.py``).
"""
from factor_risk_model.interface.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
