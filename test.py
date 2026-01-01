import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import time

def get_tickers_from_excel(file_path, limit=5000):
    """
    Reads the HKEX List of Securities Excel file and extracts stock codes.
    Added a limit parameter to handle large datasets.
    """
    try:
        df = pd.read_excel(file_path, header=None)
        header_row_index = 0
        for i, row in df.iterrows():
            if "Stock Code" in row.values:
                header_row_index = i
                break
        
        df = pd.read_excel(file_path, skiprows=header_row_index)
        df = df[pd.to_numeric(df['Stock Code'], errors='coerce').notnull()]
        
        # Extract and format the tickers
        all_tickers = df['Stock Code'].astype(int).apply(lambda x: f"{str(x).zfill(4)}.HK").tolist()
        
        # Apply the limit (first 5000)
        tickers = all_tickers[:limit]
        
        print(f"Extracted {len(all_tickers)} tickers total. Limiting scan to the first {len(tickers)}.")
        return tickers
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return []

def screen_hk_stocks_batched(tickers, batch_size=200):
    """
    Screens HK tickers in smaller batches with rate-limit protection.
    """
    chunks = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
    results = []
    
    try:
        for chunk_index, ticker_chunk in enumerate(chunks):
            print(f"Processing batch {chunk_index + 1}/{len(chunks)} ({len(ticker_chunk)} stocks)...")
            
            success = False
            retries = 0
            max_retries = 2
            
            while not success and retries < max_retries:
                try:
                    data = yf.download(
                        tickers=ticker_chunk,
                        period="1mo",
                        group_by='ticker',
                        threads=True,
                        progress=False,
                        timeout=20 
                    )
                    
                    if not data.empty:
                        success = True
                        for symbol in ticker_chunk:
                            try:
                                if len(ticker_chunk) == 1:
                                    stock_data = data.dropna()
                                else:
                                    if symbol not in data.columns.levels[0]:
                                        continue
                                    stock_data = data[symbol].dropna()
                                    
                                if stock_data.empty or len(stock_data) < 5:
                                    continue
                                
                                start_price = stock_data['Close'].iloc[0]
                                end_price = stock_data['Close'].iloc[-1]
                                max_price = stock_data['High'].max()
                                
                                pct_change = ((end_price - start_price) / start_price) * 100
                                
                                if max_price > 10 and abs(pct_change) >= 10:
                                    results.append({
                                        "Ticker": symbol,
                                        "Start Price": round(start_price, 2),
                                        "End Price": round(end_price, 2),
                                        "Max Price (30d)": round(max_price, 2),
                                        "Change %": pct_change
                                    })
                            except:
                                continue
                    else:
                        print("Received empty data, retrying...")
                        retries += 1
                        time.sleep(10)

                except Exception as e:
                    print(f"Error in batch {chunk_index + 1}: {e}")
                    retries += 1
                    time.sleep(10)
            
            if chunk_index < len(chunks) - 1:
                print("Cooling down for 5 seconds...")
                time.sleep(5)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user (Ctrl+C). Saving current results...")

    return results

if __name__ == "__main__":
    excel_input = "ListOfSecurities.xlsx" 
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_output = f"screening_results_{timestamp}.xlsx"
    
    # Set the limit here (e.g., 4000)
    MAX_TICKERS = 4000
    
    if os.path.exists(excel_input):
        tickers_to_scan = get_tickers_from_excel(excel_input, limit=MAX_TICKERS)
    else:
        print(f"File {excel_input} not found. Defaulting to first 100 stocks.")
        tickers_to_scan = [f"{str(i).zfill(4)}.HK" for i in range(1, 101)]
    
    if tickers_to_scan:
        matched_stocks = screen_hk_stocks_batched(tickers_to_scan, batch_size=200)
        
        print("\n" + "="*50)
        print(f"SCREENING COMPLETE - Found {len(matched_stocks)} matches")
        print("="*50)
        
        if matched_stocks:
            df_results = pd.DataFrame(matched_stocks)
            df_results = df_results.sort_values(by='Change %', ascending=False)
            
            display_df = df_results.copy()
            display_df['Change %'] = display_df['Change %'].apply(lambda x: f"{x:.2f}%")
            
            print(display_df.to_string(index=False))
            
            try:
                display_df.to_excel(excel_output, index=False)
                print(f"\nResults successfully saved to: {excel_output}")
            except Exception as e:
                print(f"Error saving to Excel: {e}")