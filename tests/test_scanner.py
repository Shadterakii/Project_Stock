import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from option_scanner.config import load_config, load_tickers, market_settings
from option_scanner.pricing import bs_price, historical_vol, hv_window_for_dte, implied_vol
from option_scanner.providers import OptionDataProvider
from option_scanner.report import write_report
from option_scanner.scanner import passes_liquidity, run_scan

AS_OF = date(2026, 1, 5)
SETTINGS = {
    "min_dte": 7, "max_dte": 90, "moneyness": 0.2, "option_types": ["call", "put"],
    "min_bid": 0.01, "min_volume": 10, "min_open_interest": 100, "max_spread_pct": 0.2,
    "risk_free_rate": 0.04, "history_period": "1y", "min_hv_window": 20,
    "use_dividend_yield": False, "min_fair_time_value": 0.05, "mispricing_threshold": 0.3,
}


def test_bs_reference_value_and_put_call_parity():
    call = bs_price("call", 100, 100, 1.0, 0.05, 0.2)
    put = bs_price("put", 100, 100, 1.0, 0.05, 0.2)
    assert call == pytest.approx(10.4506, abs=1e-3)
    assert call - put == pytest.approx(100 - 100 * math.exp(-0.05), abs=1e-9)


def test_implied_vol_round_trip():
    price = bs_price("put", 50, 55, 0.25, 0.03, 0.37, 0.01)
    assert implied_vol("put", price, 50, 55, 0.25, 0.03, 0.01) == pytest.approx(0.37, abs=1e-4)
    assert math.isnan(implied_vol("call", 0.0, 50, 55, 0.25, 0.03))


def test_historical_vol_and_window():
    rng = np.random.default_rng(0)
    returns = rng.normal(0, 0.25 / math.sqrt(252), 5000)
    closes = pd.Series(100 * np.exp(np.cumsum(returns)))
    assert historical_vol(closes, 4999) == pytest.approx(0.25, rel=0.05)
    assert math.isnan(historical_vol(closes.iloc[:10], 20))
    assert hv_window_for_dte(7, 20) == 20
    assert hv_window_for_dte(90, 20) == 62


class FakeProvider(OptionDataProvider):
    """One ticker, 30% HV, one expiry; the 100 call is quoted at double its fair time value."""

    def __init__(self):
        rng = np.random.default_rng(1)
        returns = rng.normal(0, 0.30 / math.sqrt(252), 300)
        closes = 100 * np.exp(np.cumsum(returns))
        self.closes = pd.Series(closes * 100 / closes[-1])  # spot = 100
        self.expiry = AS_OF + timedelta(days=30)

    def get_price_history(self, ticker, period):
        return self.closes if ticker == "FAKE" else pd.Series(dtype=float)

    def get_expiries(self, ticker):
        return [AS_OF + timedelta(days=3), self.expiry, AS_OF + timedelta(days=200)]

    def get_chain(self, ticker, expiry):
        hv = historical_vol(self.closes, hv_window_for_dte(30, 20))
        fair = lambda typ, k: bs_price(typ, 100, k, 30 / 365, 0.04, hv)
        rows = []
        for typ, k, mid in [
            ("call", 100, 2 * fair("call", 100)),   # RICH
            ("put", 95, 0.5 * fair("put", 95)),     # CHEAP
            ("call", 105, fair("call", 105)),       # fair
            ("call", 150, 0.5),                     # outside moneyness band
        ]:
            rows.append({"type": typ, "strike": k, "bid": mid * 0.98, "ask": mid * 1.02,
                         "last": mid, "volume": 50, "open_interest": 500,
                         "contract": f"FAKE{typ[0].upper()}{k}"})
        return pd.DataFrame(rows)


def test_scan_flags_rich_and_cheap(tmp_path):
    df = run_scan(FakeProvider(), ["FAKE", "EMPTY"], SETTINGS, as_of=AS_OF)
    assert set(df["dte"]) == {30}                  # 3 and 200 DTE expiries excluded
    assert 150 not in df["strike"].values          # moneyness filter
    signals = dict(zip(df["contract"], df["signal"]))
    assert signals == {"FAKEC100": "RICH", "FAKEP95": "CHEAP", "FAKEC105": ""}
    rich = df[df["contract"] == "FAKEC100"].iloc[0]
    assert rich["time_value_diff_pct"] == pytest.approx(1.0, abs=0.01)
    assert rich["iv"] > rich["hv"]

    path = write_report(df, SETTINGS, "TEST", tmp_path, top_n=10, timestamp="x")
    sheets = pd.read_excel(path, sheet_name=None)
    assert list(sheets) == ["Rich", "Cheap", "All options", "Settings"]
    assert sheets["Rich"]["contract"].tolist() == ["FAKEC100"]
    assert sheets["Cheap"]["contract"].tolist() == ["FAKEP95"]


def test_liquidity_filter():
    base = {"bid": 1.0, "ask": 1.1, "volume": 50, "open_interest": 0}
    assert passes_liquidity(base, SETTINGS)
    assert not passes_liquidity({**base, "bid": 0.0}, SETTINGS)
    assert not passes_liquidity({**base, "ask": 2.0}, SETTINGS)          # spread too wide
    assert not passes_liquidity({**base, "volume": 0}, SETTINGS)         # no volume, no OI
    assert passes_liquidity({**base, "volume": 0, "open_interest": 100}, SETTINGS)


def test_config_markets():
    config = load_config("config.toml")
    us = market_settings(config, "US")
    hk = market_settings(config, "HK")
    assert us["provider"] == "yfinance" and "SPY" in load_tickers(us)
    assert hk["risk_free_rate"] == 0.035 and hk["min_dte"] == 7
    hk_tickers = load_tickers(hk)
    assert len(hk_tickers) == 135 and hk_tickers[0] == "0001.HK"
    with pytest.raises(ValueError):
        market_settings(config, "JP")
