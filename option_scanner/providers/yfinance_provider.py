"""Yahoo Finance provider. Good US coverage; Yahoo returns no chains for most .HK tickers."""
import time
from datetime import date, datetime

import pandas as pd

from .base import CHAIN_COLUMNS, OptionDataProvider


class YFinanceProvider(OptionDataProvider):
    name = "yfinance"

    def __init__(self, request_delay=0.5):
        import yfinance as yf  # imported lazily so tests don't need network libs
        self._yf = yf
        self.request_delay = request_delay
        self._tickers = {}

    def _ticker(self, symbol):
        if symbol not in self._tickers:
            self._tickers[symbol] = self._yf.Ticker(symbol)
        return self._tickers[symbol]

    def _pause(self):
        if self.request_delay:
            time.sleep(self.request_delay)

    def get_price_history(self, ticker, period):
        hist = self._ticker(ticker).history(period=period, auto_adjust=False)
        self._pause()
        return hist["Close"] if not hist.empty else pd.Series(dtype=float)

    def get_expiries(self, ticker):
        return [datetime.strptime(s, "%Y-%m-%d").date() for s in self._ticker(ticker).options]

    def get_chain(self, ticker, expiry: date):
        chain = self._ticker(ticker).option_chain(expiry.strftime("%Y-%m-%d"))
        self._pause()
        frames = []
        for option_type, df in (("call", chain.calls), ("put", chain.puts)):
            if df is None or df.empty:
                continue
            frames.append(pd.DataFrame({
                "type": option_type,
                "strike": df["strike"],
                "bid": df["bid"],
                "ask": df["ask"],
                "last": df["lastPrice"],
                "volume": df["volume"].fillna(0),
                "open_interest": df["openInterest"].fillna(0),
                "contract": df.get("contractSymbol"),
            }))
        if not frames:
            return pd.DataFrame(columns=CHAIN_COLUMNS)
        return pd.concat(frames, ignore_index=True)

    def get_dividend_yield(self, ticker):
        try:
            # trailingAnnualDividendYield is a fraction; 'dividendYield' changed units across versions.
            value = self._ticker(ticker).info.get("trailingAnnualDividendYield")
            return float(value) if value else 0.0
        except Exception:
            return 0.0
