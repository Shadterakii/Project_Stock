# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Standalone Python scripts that screen Hong Kong (HKEX) stocks using Yahoo Finance data (`yfinance`) and write results to Excel. There is no package structure, build system, requirements file, linter config, or test suite — each script is run directly.

Dependencies (install manually): `yfinance pandas numpy openpyxl scikit-learn matplotlib`.

## Running

```bash
python hk_opt_list.py   # (re)generate HK_Stocks_With_Options.xlsx from a hardcoded list of HKEX option-class tickers
python main.py          # primary screener: reads HK_Stocks_With_Options.xlsx, writes screening_results_<timestamp>.xlsx
python predict.py       # RandomForest "5% gain in 20 trading days" classifier for a single TICKER (constant at top of file)
python test.py          # older/alternate full-market scanner (NOT a test suite)
```

All scripts hit the live Yahoo Finance API; runs are slow and rate-limit sensitive.

## Architecture

**Pipeline:** `hk_opt_list.py` → `HK_Stocks_With_Options.xlsx` → `main.py` → `screening_results_*.xlsx`.

- Ticker format everywhere is a zero-padded 4-digit code plus `.HK` (e.g. `0700.HK`). Excel inputs must have a `Ticker` column; `main.py` falls back to finding a `Stock Code` header row (the raw HKEX `ListOfSecurities.xlsx` layout) and converting codes.
- `main.py` screening is two-stage to minimize API calls:
  1. **Technical** (cheap, batched): `yf.download` over chunks of 50 tickers (`period="1mo"`, `group_by='ticker'`), with retries and `time.sleep` between batches to avoid Yahoo throttling. Criteria: 1‑month max price > 10 and absolute 1‑month change between 15% and 25%.
  2. **Fundamental** (expensive, per ticker via `yf.Ticker(...).info`): only for technical matches; `trailingPE` must be 15–50. Options existence is assumed from the input list rather than queried.
  - Ctrl‑C during scanning is caught and partial results are still saved.
  - Results are sorted by absolute % change and include per-month High/Low columns.
- `test.py` is the earlier approach: scans all of `ListOfSecurities.xlsx` (2mo period), checks `ticker.options` per stock, and writes `hk_scan_results_<timestamp>.xlsx`. `main.py` superseded it by pre-filtering to option-listed stocks.
- `predict.py` is independent of the screener: downloads history since 2015, computes RSI/SMA/MACD/Bollinger features, trains on the first 80% chronologically (no shuffling — time series) and predicts on the latest row.

yfinance can return MultiIndex columns (e.g. for single-ticker downloads); handle both shapes, as `main.py` (`len(ticker_chunk) == 1` branch) and `predict.py` (column flattening) do.

## Notes

- Screening thresholds are hardcoded in `main.py` (`screen_hk_stocks_batched` / `check_fundamentals`); README.md's criteria list is partly stale (it mentions 2mo/10%, the code uses 1mo/15–25%).
- README todo items still open: filter out tickers with no data, and ML-based price change prediction (`predict.py` is the start of this).
- `screening_results_*.xlsx` files in the repo are generated outputs.
