"""Excel report: ranked RICH / CHEAP sheets plus all evaluated options and the settings used."""
from datetime import datetime
from pathlib import Path

import pandas as pd


def rank(df, signal, top_n):
    subset = df[df["signal"] == signal]
    ascending = signal == "CHEAP"  # most negative diff first for CHEAP
    return subset.sort_values("time_value_diff_pct", ascending=ascending).head(top_n)


def write_report(df, settings, market, output_dir="results", top_n=50, timestamp=None):
    timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"option_scan_{market}_{timestamp}.xlsx"

    summary = pd.DataFrame(
        [{"setting": k, "value": ", ".join(map(str, v)) if isinstance(v, list) else v}
         for k, v in {"market": market, "generated": timestamp, **settings}.items()]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        rank(df, "RICH", top_n).to_excel(writer, sheet_name="Rich", index=False)
        rank(df, "CHEAP", top_n).to_excel(writer, sheet_name="Cheap", index=False)
        df.sort_values(["ticker", "expiry", "type", "strike"]).to_excel(
            writer, sheet_name="All options", index=False)
        summary.to_excel(writer, sheet_name="Settings", index=False)
    return path
