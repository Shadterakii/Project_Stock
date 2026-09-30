"""Core scan: find options whose market time value diverges from Black-Scholes time value."""
import logging
from datetime import date

import numpy as np
import pandas as pd

from .pricing import bs_price, historical_vol, hv_window_for_dte, implied_vol, intrinsic_value
from .providers import OptionDataProvider

log = logging.getLogger(__name__)

RESULT_COLUMNS = [
    "ticker", "contract", "type", "expiry", "dte", "strike", "spot", "moneyness",
    "bid", "ask", "mid", "spread_pct", "volume", "open_interest",
    "intrinsic", "market_time_value", "hv_window", "hv", "fair_price", "fair_time_value",
    "time_value_diff", "time_value_diff_pct", "edge_after_spread", "iv", "iv_minus_hv", "signal",
]


def passes_liquidity(row, s):
    if not (row["bid"] >= s["min_bid"] and row["ask"] > row["bid"]):
        return False
    if row["volume"] < s["min_volume"] and row["open_interest"] < s["min_open_interest"]:
        return False
    mid = (row["bid"] + row["ask"]) / 2
    return (row["ask"] - row["bid"]) / mid <= s["max_spread_pct"]


def evaluate_option(row, spot, closes, dte, s, div_yield):
    """Price one option against Black-Scholes using DTE-matched historical volatility."""
    t = dte / 365.0
    rate = s["risk_free_rate"]
    window = hv_window_for_dte(dte, s["min_hv_window"])
    hv = historical_vol(closes, window)
    if not np.isfinite(hv) or hv <= 0:
        return None

    mid = (row["bid"] + row["ask"]) / 2
    intrinsic = intrinsic_value(row["type"], spot, row["strike"])
    fair = bs_price(row["type"], spot, row["strike"], t, rate, hv, div_yield)
    market_tv = mid - intrinsic
    fair_tv = fair - intrinsic
    diff = market_tv - fair_tv
    diff_pct = diff / fair_tv if fair_tv >= s["min_fair_time_value"] else float("nan")
    # Edge only counts once it exceeds half the bid-ask spread (the cost to cross to mid).
    edge = abs(diff) - (row["ask"] - row["bid"]) / 2
    iv = implied_vol(row["type"], mid, spot, row["strike"], t, rate, div_yield)

    threshold = s["mispricing_threshold"]
    if np.isfinite(diff_pct) and edge > 0 and diff_pct >= threshold:
        signal = "RICH"
    elif np.isfinite(diff_pct) and edge > 0 and diff_pct <= -threshold:
        signal = "CHEAP"
    else:
        signal = ""

    return {
        "contract": row.get("contract"),
        "type": row["type"],
        "strike": row["strike"],
        "spot": spot,
        "moneyness": row["strike"] / spot - 1,
        "bid": row["bid"],
        "ask": row["ask"],
        "mid": mid,
        "spread_pct": (row["ask"] - row["bid"]) / mid,
        "volume": row["volume"],
        "open_interest": row["open_interest"],
        "intrinsic": intrinsic,
        "market_time_value": market_tv,
        "hv_window": window,
        "hv": hv,
        "fair_price": fair,
        "fair_time_value": fair_tv,
        "time_value_diff": diff,
        "time_value_diff_pct": diff_pct,
        "edge_after_spread": edge,
        "iv": iv,
        "iv_minus_hv": iv - hv if np.isfinite(iv) else float("nan"),
        "signal": signal,
    }


def scan_ticker(provider: OptionDataProvider, ticker, s, as_of: date):
    closes = provider.get_price_history(ticker, s["history_period"])
    if closes.empty:
        log.warning("%s: no price history, skipping", ticker)
        return []
    spot = float(closes.iloc[-1])
    div_yield = provider.get_dividend_yield(ticker) if s.get("use_dividend_yield", True) else 0.0

    expiries = [e for e in provider.get_expiries(ticker)
                if s["min_dte"] <= (e - as_of).days <= s["max_dte"]]
    if not expiries:
        log.warning("%s: no option expiries in %s-%s DTE (provider may have no chains for this market)",
                    ticker, s["min_dte"], s["max_dte"])
        return []

    types = set(s.get("option_types", ["call", "put"]))
    rows = []
    for expiry in expiries:
        dte = (expiry - as_of).days
        chain = provider.get_chain(ticker, expiry)
        for _, opt in chain.iterrows():
            if opt["type"] not in types:
                continue
            if abs(opt["strike"] / spot - 1) > s["moneyness"]:
                continue
            if not passes_liquidity(opt, s):
                continue
            result = evaluate_option(opt, spot, closes, dte, s, div_yield)
            if result:
                rows.append({"ticker": ticker, "expiry": expiry, "dte": dte, **result})
    log.info("%s: %d options evaluated across %d expiries", ticker, len(rows), len(expiries))
    return rows


def run_scan(provider: OptionDataProvider, tickers, s, as_of: date | None = None):
    """Scan all tickers; one failing ticker never aborts the run. Returns a DataFrame."""
    as_of = as_of or date.today()
    rows = []
    try:
        for i, ticker in enumerate(tickers, 1):
            log.info("[%d/%d] %s", i, len(tickers), ticker)
            try:
                rows += scan_ticker(provider, ticker, s, as_of)
            except Exception as e:
                log.warning("%s: failed (%s: %s)", ticker, type(e).__name__, e)
    except KeyboardInterrupt:
        log.warning("Interrupted - keeping %d options scanned so far", len(rows))
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)
