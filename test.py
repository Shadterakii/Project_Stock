import yfinance as yf

tickers = [f"{i:04d}.HK" for i in range(1, 1001)]

batch_size = 100


print(tickers)
# for i in range(0, len(tickers), batch_size):
#     batch = tickers[i:i + batch_size]
#     data = yf.download(
#         tickers=batch,
#         period="15d",
#         group_by="ticker",
#         threads=True
#     )
