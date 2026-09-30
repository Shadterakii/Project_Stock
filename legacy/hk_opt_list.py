import pandas as pd

def generate_option_list():
    # This list is based on HKEX "Stock Option Classes" (Major liquid stocks)
    # Using this list skips the 99% of stocks that don't have options.
    tickers = [
        "0001.HK", "0002.HK", "0003.HK", "0004.HK", "0005.HK", "0006.HK", "0011.HK", "0012.HK", "0016.HK", "0017.HK", 
        "0019.HK", "0020.HK", "0023.HK", "0027.HK", "0066.HK", "0135.HK", "0151.HK", "0175.HK", "0241.HK", "0267.HK", 
        "0268.HK", "0285.HK", "0288.HK", "0293.HK", "0300.HK", "0358.HK", "0386.HK", "0388.HK", "0390.HK", "0489.HK", 
        "0669.HK", "0688.HK", "0700.HK", "0728.HK", "0753.HK", "0762.HK", "0788.HK", "0823.HK", "0836.HK", "0857.HK", 
        "0868.HK", "0881.HK", "0883.HK", "0902.HK", "0914.HK", "0939.HK", "0941.HK", "0968.HK", "0981.HK", "0992.HK", 
        "0998.HK", "1024.HK", "1044.HK", "1088.HK", "1093.HK", "1099.HK", "1109.HK", "1113.HK", "1171.HK", "1177.HK", 
        "1186.HK", "1211.HK", "1288.HK", "1299.HK", "1336.HK", "1339.HK", "1347.HK", "1359.HK", "1378.HK", "1398.HK", 
        "1658.HK", "1772.HK", "1800.HK", "1801.HK", "1810.HK", "1816.HK", "1833.HK", "1876.HK", "1898.HK", "1918.HK", 
        "1919.HK", "1928.HK", "1988.HK", "2007.HK", "2015.HK", "2018.HK", "2020.HK", "2202.HK", "2238.HK", "2269.HK", 
        "2282.HK", "2313.HK", "2318.HK", "2319.HK", "2328.HK", "2331.HK", "2333.HK", "2382.HK", "2388.HK", "2600.HK", 
        "2601.HK", "2611.HK", "2628.HK", "2800.HK", "2822.HK", "2823.HK", "2828.HK", "2899.HK", "3188.HK", "3323.HK", 
        "3328.HK", "3333.HK", "3690.HK", "3750.HK", "3888.HK", "3968.HK", "3988.HK", "3993.HK", "6030.HK", "6060.HK", 
        "6618.HK", "6690.HK", "6837.HK", "6862.HK", "9618.HK", "9626.HK", "9633.HK", "9868.HK", "9888.HK", "9898.HK", 
        "9901.HK", "9961.HK", "9988.HK", "9992.HK", "9999.HK"
    ]
    
    # Create a DataFrame in the format your screener expects
    df = pd.DataFrame({'Ticker': tickers})
    
    # For compatibility with your "clean" function, we can also add a "Stock Code" column
    df['Stock Code'] = df['Ticker'].apply(lambda x: x.split('.')[0])
    
    filename = "HK_Stocks_With_Options.xlsx"
    df.to_excel(filename, index=False)
    print(f"Successfully created '{filename}' with {len(tickers)} tickers.")
if __name__ == "__main__":
    generate_option_list()