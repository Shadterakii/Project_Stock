"""CLI entry point: python scan.py [--market US] [--tickers AAPL MSFT] [--config config.toml]"""
import argparse
import logging

from option_scanner.config import load_config, load_tickers, market_settings
from option_scanner.providers import get_provider
from option_scanner.report import rank, write_report
from option_scanner.scanner import run_scan

DISPLAY_COLUMNS = ["ticker", "type", "expiry", "dte", "strike", "mid", "market_time_value",
                   "fair_time_value", "time_value_diff_pct", "iv", "hv"]


def main():
    parser = argparse.ArgumentParser(description="Scan option chains for time-value mispricing.")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--market", help="Market key from config (default: [scan].market)")
    parser.add_argument("--tickers", nargs="+", help="Override the configured ticker list")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(args.config)
    market = args.market or config["scan"]["market"]
    settings = market_settings(config, market)
    tickers = args.tickers or load_tickers(settings)
    provider = get_provider(settings["provider"], request_delay=settings.get("request_delay", 0.5))

    df = run_scan(provider, tickers, settings)
    report_cfg = config.get("report", {})
    top_n = report_cfg.get("top_n", 50)
    print(f"\nEvaluated {len(df)} options: "
          f"{(df['signal'] == 'RICH').sum()} RICH, {(df['signal'] == 'CHEAP').sum()} CHEAP")
    for signal in ("RICH", "CHEAP"):
        top = rank(df, signal, report_cfg.get("print_top", 10))
        if not top.empty:
            print(f"\nTop {signal}:")
            print(top[DISPLAY_COLUMNS].round(3).to_string(index=False))

    if df.empty:
        print("No options passed the filters; no report written.")
        return
    path = write_report(df, settings, market, report_cfg.get("output_dir", "results"), top_n)
    print(f"\nReport saved to {path}")


if __name__ == "__main__":
    main()
