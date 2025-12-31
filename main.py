import yfinance as yf
import pandas as pd
from time import sleep

# -----------------------------
# CONFIG
tickers = [f"{i:04d}.HK" for i in range(1, 3001)]
DAYS = 10
THRESHOLD = 10  # % price change over 10 days
DRAWDOWN_THRESHOLD = 10  # % drop from max
BATCH_SIZE = 100
# -----------------------------

def get_movers_with_drawdown(tickers, days, threshold, drawdown_threshold, batch_size):
    results = []

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        try:
            data = yf.download(batch, period=f"{days+5}d", group_by="ticker", threads=True)

            for ticker in batch:
                if ticker not in data.columns.levels[0]:
                    continue  # skip missing data

                hist = data[ticker]['Close'].dropna()
                if len(hist) < days:
                    continue

                start_price = hist.iloc[-days]
                end_price = hist.iloc[-1]
                pct_change = ((end_price - start_price) / start_price) * 100

                # calculate drawdown from max in period
                max_price = hist[-days:].max()
                min_from_max = hist[-days:].min()
                drawdown = ((min_from_max - max_price) / max_price) * 100

                if abs(pct_change) >= threshold and drawdown <= -drawdown_threshold:
                    results.append({
                        "Ticker": ticker,
                        "Start Price": round(start_price, 2),
                        "End Price": round(end_price, 2),
                        "Change (%)": round(pct_change, 2),
                        "Max Price": round(max_price, 2),
                        "Min from Max": round(min_from_max, 2),
                        "Drawdown (%)": round(drawdown, 2)
                    })

        except Exception as e:
            print(f"Error fetching batch {i}–{i+batch_size}: {e}")

        sleep(1)  # avoid rate limits

    return results

# -----------------------------
movers = get_movers_with_drawdown(tickers, DAYS, THRESHOLD, DRAWDOWN_THRESHOLD, BATCH_SIZE)

print("\nStocks with ±10% change and ≥10% drawdown in last 10 days:\n")
for stock in movers:
    print(stock)

# Optional CSV
pd.DataFrame(movers).to_csv("hk_stock_movers_drawdown.csv", index=False)
