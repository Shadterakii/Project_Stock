# Option Time-Value Scanner

Scans option chains and flags contracts whose **time value** (option price minus intrinsic value) is far above (**RICH**) or below (**CHEAP**) a Black-Scholes fair value computed from the stock's own historical volatility.

## How it works

For each ticker and each option within the configured filters:

1. **Filters:** 7–90 days to expiry, strike within ±20% of spot, and liquidity (bid > 0, volume ≥ 10 or open interest ≥ 100, bid-ask spread ≤ 20% of mid).
2. **Historical volatility:** annualized close-to-close volatility over a lookback matching the option's days to expiry (minimum 20 trading days).
3. **Fair value:** European Black-Scholes price using that volatility, the risk-free rate and the dividend yield. Fair time value = fair price − intrinsic value.
4. **Signal:** `time_value_diff_pct = (market time value − fair time value) / fair time value`. The option is flagged RICH/CHEAP when this is beyond ±30% **and** the difference is larger than half the bid-ask spread.
5. Implied volatility and `IV − HV` are reported alongside for context.

All thresholds live in `config.toml`.

## Usage

```bash
pip install -r requirements.txt
python scan.py                          # default market from config.toml (US)
python scan.py --market HK              # HK tickers from legacy/HK_Stocks_With_Options.xlsx
python scan.py --tickers AAPL TSLA      # override tickers
python -m pytest                        # run tests (offline, uses a fake data provider)
```

Output: `results/option_scan_<MARKET>_<timestamp>.xlsx` with sheets **Rich**, **Cheap**, **All options** and **Settings**.

## Markets and data

- **US:** Yahoo Finance via `yfinance` (free, delayed quotes).
- **HK:** Yahoo has no option chains for most `.HK` tickers, so they are skipped. To scan HK properly, add a provider (e.g. Futu OpenAPI or Interactive Brokers) by subclassing `OptionDataProvider` in `option_scanner/providers/` and registering it in `get_provider()`, then set `provider` under `[markets.HK]`.

## Caveats

- Black-Scholes is European; US single-stock options are American, so deep ITM puts and calls near an ex-dividend date can look mispriced when they aren't.
- Historical volatility looks backward. A RICH signal before earnings often just reflects the expected earnings move.
- Yahoo quotes are delayed and can be stale outside market hours (bid/ask may be 0), so run the scan during trading hours.

## Legacy

`legacy/` holds the original stock screener (`main.py`), the RandomForest predictor (`predict.py`), and the HK ticker lists.
