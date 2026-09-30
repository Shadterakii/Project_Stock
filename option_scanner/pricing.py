"""Black-Scholes pricing, implied volatility and historical volatility."""
import math

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def intrinsic_value(option_type, spot, strike):
    if option_type == "call":
        return max(spot - strike, 0.0)
    return max(strike - spot, 0.0)


def bs_price(option_type, spot, strike, t, rate, vol, div_yield=0.0):
    """European Black-Scholes price with continuous dividend yield.

    t is in years. Falls back to discounted intrinsic value when t or vol is ~0.
    """
    if t <= 0 or vol <= 0:
        fwd_intrinsic = (spot * math.exp(-div_yield * max(t, 0)) - strike * math.exp(-rate * max(t, 0)))
        return max(fwd_intrinsic, 0.0) if option_type == "call" else max(-fwd_intrinsic, 0.0)

    sqrt_t = math.sqrt(t)
    d1 = (math.log(spot / strike) + (rate - div_yield + 0.5 * vol * vol) * t) / (vol * sqrt_t)
    d2 = d1 - vol * sqrt_t
    disc_spot = spot * math.exp(-div_yield * t)
    disc_strike = strike * math.exp(-rate * t)
    if option_type == "call":
        return disc_spot * _norm_cdf(d1) - disc_strike * _norm_cdf(d2)
    return disc_strike * _norm_cdf(-d2) - disc_spot * _norm_cdf(-d1)


def implied_vol(option_type, price, spot, strike, t, rate, div_yield=0.0,
                low=1e-4, high=5.0, tol=1e-6, max_iter=200):
    """Implied volatility by bisection. Returns NaN if price is outside the model's range."""
    if price is None or not np.isfinite(price) or price <= 0 or t <= 0:
        return float("nan")
    if price < bs_price(option_type, spot, strike, t, rate, low, div_yield) - tol:
        return float("nan")
    if price > bs_price(option_type, spot, strike, t, rate, high, div_yield):
        return float("nan")
    for _ in range(max_iter):
        mid = 0.5 * (low + high)
        if bs_price(option_type, spot, strike, t, rate, mid, div_yield) > price:
            high = mid
        else:
            low = mid
        if high - low < tol:
            break
    return 0.5 * (low + high)


def hv_window_for_dte(dte, min_window):
    """Trading-day lookback matching an option's calendar days to expiry."""
    return max(min_window, int(round(dte * TRADING_DAYS / 365)))


def historical_vol(closes: pd.Series, window: int):
    """Annualized close-to-close volatility over the last `window` returns."""
    closes = closes.dropna()
    if len(closes) < window + 1:
        return float("nan")
    log_ret = np.log(closes / closes.shift(1)).dropna().iloc[-window:]
    return float(log_ret.std(ddof=1) * math.sqrt(TRADING_DAYS))
