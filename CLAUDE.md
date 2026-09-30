# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Option time-value mispricing scanner: compares each option's market time value with a Black-Scholes time value priced at DTE-matched historical volatility, and writes RICH/CHEAP rankings to Excel. Python 3.11+ (uses `tomllib`). No scipy; the normal CDF uses `math.erf`.

## Commands

```bash
pip install -r requirements.txt
python scan.py [--market US|HK] [--tickers AAPL MSFT] [--config config.toml]
python -m pytest                                   # all tests
python -m pytest tests/test_scanner.py::test_scan_flags_rich_and_cheap   # single test
```

Tests are fully offline (they use `FakeProvider` in `tests/test_scanner.py`). Live runs need network access to Yahoo Finance.

## Architecture

- `config.toml`: `[scan]`, `[liquidity]` and `[pricing]` are defaults. `[markets.<NAME>]` overrides any key and sets `provider`, `tickers` and/or `tickers_file` (xlsx/csv with a `Ticker` column). `config.market_settings()` merges them into one flat dict `s` that is passed everywhere.
- `option_scanner/providers/`: the `OptionDataProvider` ABC (price history, expiries, chain, dividend yield). `get_chain()` must return the normalized columns in `CHAIN_COLUMNS` (plus an optional `contract`). New data sources are registered in `providers/__init__.py:get_provider()`. yfinance is imported lazily inside its provider.
- `option_scanner/scanner.py`: `run_scan` loops over tickers, and one ticker failing never aborts the run; Ctrl‑C keeps partial results. `scan_ticker` filters by DTE, moneyness and liquidity; `evaluate_option` computes the signal. RICH/CHEAP requires both |diff %| ≥ `mispricing_threshold` and `edge_after_spread` > 0 (diff exceeds half the bid-ask spread). diff % is NaN when fair time value < `min_fair_time_value`.
- `option_scanner/pricing.py`: BS price, bisection implied volatility, historical volatility, and `hv_window_for_dte` (calendar DTE → trading days, floored at `min_hv_window`). Time to expiry is `dte/365`.
- `option_scanner/report.py`: writes the Excel sheets Rich, Cheap, All options and Settings to `results/`.
- `legacy/`: the original HK stock screener and ML predictor, kept for reference only; `legacy/HK_Stocks_With_Options.xlsx` is still the HK ticker source.

## Known limitations

Yahoo returns no option chains for most `.HK` tickers, so HK needs a real provider (Futu/IBKR) implementing `OptionDataProvider`. The pricing model is European BS, while US single-stock options are American.
