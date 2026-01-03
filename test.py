import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time
import os

def generate_hk_tickers(limit=2000):
    """
    Generates a list of HK tickers (0001.HK to limit.HK) if no file is found.
    """
    return [f"{str(i).zfill(4)}.HK" for i in range(1, limit + 1)]

def get_tickers_from_excel(file_path):
    """
    Tries to read tickers from the HKEX Excel file if it exists.
    """
    try:
        print(f"Reading {file_path}...")
        df = pd.read_excel(file_path, header=None)
        
        # Find header row
        header_row = 0
        for i, row in df.iterrows():
            if "Stock Code" in row.values:
                header_row = i
                break
                
        df = pd.read_excel(file_path, skiprows=header_row)
        df = df[pd.to_numeric(df['Stock Code'], errors='coerce').notnull()]
        tickers = df['Stock Code'].astype(int).apply(lambda x: f"{str(x).zfill(4)}.HK").tolist()
        return tickers
    except Exception:
        return []

def check_fundamentals(symbol, pe_min, pe_max):
    """
    Checks if a ticker has options and a PE (TTM) within range.
    Returns: (Passed_Boolean, PE_Value)
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # 1. Check Options (Fastest fail)
        if len(ticker.options) == 0:
            return False, None
            
        # 2. Check PE TTM
        # We use 'trailingPE' which corresponds to TTM
        pe_ttm = ticker.info.get('trailingPE')
        
        if pe_ttm is not None and pe_min <= pe_ttm <= pe_max:
            return True, round(pe_ttm, 2)
            
        return False, None
    except:
        return False, None

def run_hk_scan(pe_min=15, pe_max=50, price_change_threshold=0.15):
    """
    Scans HK stocks by:
    1. Batch downloading 2mo history (Fast).
    2. Filtering for >15% price movement.
    3. Checking P/E TTM and Options for matches.
    """
    print(f"Starting Manual Scan: PE {pe_min}-{pe_max}, Price Change > {price_change_threshold:.0%}")
    
    # Load tickers
    excel_file = "ListOfSecurities.xlsx"
    if os.path.exists(excel_file):
        tickers = get_tickers_from_excel(excel_file)
        # Limit to first 4000 to save time/resources if list is huge
        tickers = tickers[4000:8000] 
        print(f"Loaded {len(tickers)} tickers from file.")
    else:
        print("Excel file not found. Generating first 2000 tickers...")
        tickers = generate_hk_tickers(2000)

    # Batch settings
    batch_size = 100 # Smaller batch size to be safe
    chunks = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
    results = []

    try:
        for i, chunk in enumerate(chunks):
            print(f"Scanning batch {i+1}/{len(chunks)}...")
            
            try:
                # 1. Download Price History (Technical Filter)
                data = yf.download(
                    tickers=chunk, 
                    period="2mo", 
                    group_by='ticker', 
                    threads=True, 
                    progress=False,
                    timeout=20
                )
                
                if data.empty: 
                    continue
                
                for symbol in chunk:
                    try:
                        # Extract data for single symbol
                        if len(chunk) > 1:
                            if symbol not in data.columns.levels[0]: continue
                            hist = data[symbol].dropna()
                        else:
                            hist = data.dropna()
                            
                        if len(hist) < 5: continue

                        # Calculate Price Change
                        start_price = hist['Close'].iloc[0]
                        curr_price = hist['Close'].iloc[-1]
                        
                        # Use abs() to capture both up and down movements
                        pct_change = abs((curr_price - start_price) / start_price)
                        
                        # 2. If Price criteria met, check Fundamentals (Slow)
                        if pct_change >= price_change_threshold:
                            print(f"  > Match: {symbol} ({pct_change:.1%}). Checking PE/Options...")
                            
                            valid, pe_val = check_fundamentals(symbol, pe_min, pe_max)
                            
                            if valid:
                                print(f"    >> CONFIRMED: {symbol} | PE: {pe_val}")
                                results.append({
                                    "Ticker": symbol,
                                    "Current Price": round(curr_price, 2),
                                    "Price Change (2mo)": f"{pct_change:.2%}",
                                    "PE (TTM)": pe_val,
                                    "Has Options": "Yes"
                                })
                                # Small sleep to be polite to API after an individual check
                                time.sleep(1)
                                
                    except Exception:
                        continue
                        
            except Exception as e:
                print(f"Batch error: {e}")
                time.sleep(5)
                
            # Cooldown between batches
            if i < len(chunks) - 1:
                time.sleep(10)

    except KeyboardInterrupt:
        print("\nScan stopped by user.")

    # Output Results
    print("\n" + "="*50)
    print(f"SCAN COMPLETE. Found {len(results)} matches.")
    print("="*50)
    
    if results:
        df = pd.DataFrame(results)
        print(df.to_string(index=False))
        
        # Save to file
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"hk_scan_results_{ts}.xlsx"
        df.to_excel(fname, index=False)
        print(f"\nSaved to {fname}")

if __name__ == "__main__":
   
    run_hk_scan(pe_min=15, pe_max=50, price_change_threshold=0.15)