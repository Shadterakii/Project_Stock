import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import time

def clean_and_get_tickers(file_path):
    """
    Reads the full HKEX list (e.g., 17k+ rows), removes delisted/invalid entries, 
    and exports a clean master list to a new Excel file.
    """
    try:
        print(f"Reading {file_path}...")
        df = pd.read_excel(file_path, header=None)
        
        # Find the header row by looking for the "Stock Code" column name
        header_row_index = 0
        for i, row in df.iterrows():
            if "Stock Code" in row.values:
                header_row_index = i
                break
        
        # Reload with correct headers
        df = pd.read_excel(file_path, skiprows=header_row_index)
        
        # 1. Filter out rows where 'Stock Code' is not a number
        df = df[pd.to_numeric(df['Stock Code'], errors='coerce').notnull()]
        
        # 2. Convert codes to standard 4-digit strings for Yahoo Finance
        df['Stock Code'] = df['Stock Code'].astype(int)
        df['Ticker'] = df['Stock Code'].apply(lambda x: f"{str(x).zfill(4)}.HK")
        
        # 3. Export the clean list to a new file for your records
        clean_file_name = "Clean_HK_Tickers.xlsx"
        df.to_excel(clean_file_name, index=False)
        print(f"Master list cleaned. Saved {len(df)} valid tickers to {clean_file_name}")
        
        return df['Ticker'].tolist()
    except Exception as e:
        print(f"Error cleaning Excel file: {e}")
        return []

def check_fundamentals(symbol):
    """
    Checks if a specific ticker has listed options and 
    if its P/E ratio is between 15 and 50.
    """
    try:
        ticker_obj = yf.Ticker(symbol)
        info = ticker_obj.info
        
        # Check for options availability
        options_available = len(ticker_obj.options) > 0
        if not options_available:
            return False, None
            
        # Check P/E Ratio (trailingPE)
        pe_ratio = info.get('trailingPE')
        
        # Print PE and Ticker as requested
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

def screen_hk_stocks_batched(tickers, batch_size=100):
    """
    Screens HK tickers in batches with extended cooldowns to prevent rate limits.
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
                        period="1mo", # Changed from 2mo to 1mo
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
                                
                                # Technical Criteria check
                                if max_price > 10 and abs(pct_change) >= 10:
                                    print(f"Technical match found: {symbol}. Checking options and P/E...")
                                    valid_fundamentals, pe_val = check_fundamentals(symbol)
                                    
                                    if valid_fundamentals:
                                        results.append({
                                            "Ticker": symbol,
                                            "Start Price": round(start_price, 2),
                                            "End Price": round(end_price, 2),
                                            "Max Price (1mo)": round(max_price, 2),
                                            "Change %": pct_change,
                                            "P/E Ratio": pe_val,
                                            "Has Options": "Yes"
                                        })
                            except:
                                continue
                    else:
                        print("Received empty data, retrying in 30s...")
                        retries += 1
                        time.sleep(30)

                except Exception as e:
                    print(f"Error in batch {chunk_index + 1}: {e}")
                    retries += 1
                    time.sleep(30)
            
            # Rate limiting cooldown - essential for long runs
            if chunk_index < len(chunks) - 1:
                print("Cooling down for 30 seconds...")
                time.sleep(30)
                
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Saving current results...")

    return results

if __name__ == "__main__":
    excel_input = "Clean_HK_Tickers.xlsx" # Changed input file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_output = f"screening_results_{timestamp}.xlsx"
    
    # Configuration: How many tickers to skip
    MAX_TICKERS_TO_SCAN = 4000
    
    if os.path.exists(excel_input):
        # Step 1: Clean the messy 17k list and export 'Clean_HK_Tickers.xlsx'
        # (Since we are loading the clean file, this function will essentially just load it)
        all_valid_tickers = clean_and_get_tickers(excel_input)
        
        # Step 2: Slice the list to scan 4000 to 8001
        print(f"Scanning tickers from index {MAX_TICKERS_TO_SCAN} to 8001...")
        tickers_to_scan = all_valid_tickers[MAX_TICKERS_TO_SCAN: 8001]
    else:
        print(f"File {excel_input} not found.")
        tickers_to_scan = []

    if tickers_to_scan:
        matched_stocks = screen_hk_stocks_batched(tickers_to_scan, batch_size=100)
        
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