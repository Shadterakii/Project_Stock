import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import time

def get_tickers_from_excel(file_path):
    """
    Reads the tickers directly from the provided clean Excel file.
    Expects a column named 'Ticker' (e.g., '0001.HK').
    """
    try:
        print(f"Reading {file_path}...")
        df = pd.read_excel(file_path)
        
        # Check if 'Ticker' column exists (based on your file structure)
        if 'Ticker' in df.columns:
            tickers = df['Ticker'].tolist()
            print(f"Successfully loaded {len(tickers)} tickers.")
            return tickers
        
        # Fallback: Look for Stock Code if Ticker column is missing
        print("Column 'Ticker' not found, searching for 'Stock Code'...")
        # Find header row
        header_row_index = 0
        for i, row in df.iterrows():
            if "Stock Code" in row.values:
                header_row_index = i
                break
        
        df = pd.read_excel(file_path, skiprows=header_row_index)
        if 'Stock Code' in df.columns:
            df = df[pd.to_numeric(df['Stock Code'], errors='coerce').notnull()]
            tickers = df['Stock Code'].astype(int).apply(lambda x: f"{str(x).zfill(4)}.HK").tolist()
            print(f"Successfully generated {len(tickers)} tickers from Stock Codes.")
            return tickers
            
        print("Error: Could not find 'Ticker' or 'Stock Code' columns.")
        return []
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return []

def check_fundamentals(symbol):
    """
    Checks if its P/E ratio is between 15 and 50.
    (Options existence is implied by the input file, but we keep the logic robust)
    """
    try:
        ticker_obj = yf.Ticker(symbol)
        info = ticker_obj.info
        
        # Check P/E Ratio (trailingPE)
        pe_ratio = info.get('trailingPE')
        
        # Print PE and Ticker to terminal as requested
        if pe_ratio is not None:
            print(f"  [Fundamental Check] {symbol} | PE: {pe_ratio}")
        else:
            print(f"  [Fundamental Check] {symbol} | PE: None")

        # Filter: PE must exist and be between 15 and 50
        if pe_ratio and 15 <= pe_ratio <= 50:
            return True, round(pe_ratio, 2)
            
        return False, None
    except:
        return False, None

def screen_hk_stocks_batched(tickers, batch_size=50):
    """
    Screens HK tickers in batches.
    Batch size reduced to 50 for safety since the list is high-quality.
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
                        period="2mo",
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
                                
                                # --- MODIFIED CRITERIA ---
                                # 1. Max Price > 10
                                # 2. Absolute Change between 15% and 50%
                                if max_price > 10 and 15 <= abs(pct_change) <= 50:
                                    print(f"Technical match found: {symbol} ({pct_change:.2f}%). Checking P/E...")
                                    valid_fundamentals, pe_val = check_fundamentals(symbol)
                                    
                                    if valid_fundamentals:
                                        results.append({
                                            "Ticker": symbol,
                                            "Start Price": round(start_price, 2),
                                            "End Price": round(end_price, 2),
                                            "Max Price (2mo)": round(max_price, 2),
                                            "Change %": pct_change,
                                            "P/E Ratio": pe_val,
                                            "Has Options": "Yes"
                                        })
                            except:
                                continue
                    else:
                        print("Received empty data, retrying...")
                        retries += 1
                        time.sleep(5)

                except Exception as e:
                    print(f"Error in batch {chunk_index + 1}: {e}")
                    retries += 1
                    time.sleep(5)
            
            # Small cooldown between batches
            if chunk_index < len(chunks) - 1:
                time.sleep(2)
                
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Saving current results...")

    return results

if __name__ == "__main__":
    # Updated Input File
    excel_input = "HK_Stocks_With_Options.xlsx"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_output = f"screening_results_{timestamp}.xlsx"
    
    if os.path.exists(excel_input):
        tickers_to_scan = get_tickers_from_excel(excel_input)
    else:
        print(f"File {excel_input} not found.")
        tickers_to_scan = []

    if tickers_to_scan:
        matched_stocks = screen_hk_stocks_batched(tickers_to_scan, batch_size=50)
        
        print("\n" + "="*50)
        print(f"SCREENING COMPLETE - Found {len(matched_stocks)} matches")
        print("="*50)
        
        if matched_stocks:
            df_results = pd.DataFrame(matched_stocks)
            df_results['AbsChange'] = df_results['Change %'].abs()
            df_results = df_results.sort_values(by='AbsChange', ascending=False).drop(columns=['AbsChange'])
            
            display_df = df_results.copy()
            display_df['Change %'] = display_df['Change %'].apply(lambda x: f"{x:.2f}%")
            
            print(display_df.to_string(index=False))
            
            try:
                display_df.to_excel(excel_output, index=False)
                print(f"\nResults successfully saved to: {excel_output}")
            except Exception as e:
                print(f"Error saving results: {e}")