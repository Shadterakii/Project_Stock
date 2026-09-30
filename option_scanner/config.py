"""Load config.toml into plain dicts, resolving per-market settings."""
import tomllib
from pathlib import Path

import pandas as pd


def load_config(path="config.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f)


def market_settings(config, market):
    """Merge [scan]/[liquidity]/[pricing] defaults with [markets.<MARKET>] overrides."""
    markets = config.get("markets", {})
    if market not in markets:
        raise ValueError(f"Market '{market}' not defined in config. Available: {list(markets)}")
    settings = {**config.get("scan", {}), **config.get("liquidity", {}), **config.get("pricing", {})}
    settings.update(markets[market])
    return settings


def load_tickers(settings, base_dir="."):
    """Tickers from the inline list plus an optional Excel/CSV file with a 'Ticker' column."""
    tickers = list(settings.get("tickers", []))
    tickers_file = settings.get("tickers_file")
    if tickers_file:
        path = Path(base_dir) / tickers_file
        df = pd.read_csv(path) if path.suffix == ".csv" else pd.read_excel(path)
        tickers += df["Ticker"].dropna().astype(str).str.strip().tolist()
    # De-duplicate while keeping order.
    return list(dict.fromkeys(t for t in tickers if t))
