"""Data layer of the interactive app - built in Step 2.

Wraps the engine's fetching/alignment (``src.data``) so the interface never
touches API details. Planned modules:

    data_fetcher.py    yfinance prices + Kenneth French factors, with
                       caching, date alignment, and friendly error
                       messages on API failures or unknown tickers.
"""
