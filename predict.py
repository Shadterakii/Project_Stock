import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
TICKER = "0358.HK"
PREDICTION_DAYS = 20  # Look 20 trading days into the future (approx 1 month)
TARGET_GAIN = 0.05    # We want to predict a 5% gain

def add_indicators(df):
    """
    Calculates technical indicators to help the AI 'see' the chart.
    """
    df = df.copy()
    
    # 1. Relative Strength Index (RSI)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 2. Moving Averages (Trend)
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    df['Above_SMA200'] = np.where(df['Close'] > df['SMA_200'], 1, 0)
    
    # 3. MACD (Momentum)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    
    # 4. Bollinger Bands (Volatility)
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (2 * df['BB_Std'])
    df['BB_Lower'] = df['BB_Middle'] - (2 * df['BB_Std'])
    
    # Distance from Upper Band (Higher = closer to breakout or overbought)
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
    
    return df

def prepare_data(ticker):
    print(f"Downloading historical data for {ticker}...")
    # Get 10 years of data to maximize training samples
    df = yf.download(ticker, start="2015-01-01", progress=False)
    
    # --- FIX: Flatten MultiIndex columns ---
    # yfinance often returns columns like ('Close', '0358.HK'). 
    # This flattens them to just 'Close' to prevent "Operands not aligned" errors.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if len(df) < 500:
        print("Not enough data to train.")
        return None, None

    # Add the technical indicators
    df = add_indicators(df)
    df.dropna(inplace=True) # Remove rows with NaN from indicator calculations
    
    # --- CREATE THE TARGET ---
    # We want to know: "Is the Close price 20 days later > Current Close * 1.05?"
    # shift(-PREDICTION_DAYS) looks into the future
    df['Future_Close'] = df['Close'].shift(-PREDICTION_DAYS)
    df['Target'] = (df['Future_Close'] > df['Close'] * (1 + TARGET_GAIN)).astype(int)
    
    # We must remove the last 20 rows because they don't have a future yet (unknown target)
    data_for_training = df.iloc[:-PREDICTION_DAYS].copy()
    
    # But we keep the very last row separately to make our FINAL PREDICTION for today
    data_for_prediction = df.iloc[[-1]].copy()
    
    return data_for_training, data_for_prediction

def train_and_predict():
    # 1. Prepare Data
    train_df, latest_df = prepare_data(TICKER)
    
    if train_df is None:
        return

    # 2. Define Features (X) and Target (y)
    features = ['RSI', 'SMA_50', 'Above_SMA200', 'MACD', 'BB_Position', 'Volume']
    
    X = train_df[features]
    y = train_df['Target']
    
    # 3. Split Data (Train on old data, Test on recent data)
    # We don't shuffle because order matters in time-series
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    
    print(f"\nTraining model on {len(X_train)} days of history...")
    print(f"Testing accuracy on recent {len(X_test)} days...")

    # 4. Train Random Forest
    # n_estimators=200 means we create 200 decision trees
    # min_samples_split=10 prevents the model from memorizing noise
    model = RandomForestClassifier(n_estimators=200, min_samples_split=10, random_state=42)
    model.fit(X_train, y_train)
    
    # 5. Evaluate
    preds = model.predict(X_test)
    accuracy = accuracy_score(y_test, preds)
    print(f"\n--- Model Performance ---")
    print(f"Accuracy: {accuracy:.2%}")
    
    # Check "Precision" specifically for class 1 (Buy Signal)
    # This answers: "When the model said BUY, was it actually right?"
    report = classification_report(y_test, preds, output_dict=True)
    buy_precision = report['1']['precision']
    print(f"Buy Signal Precision: {buy_precision:.2%}")
    
    # 6. Predict for TODAY
    print(f"\n--- Prediction for {TICKER} (Starting Today) ---")
    current_features = latest_df[features]
    
    # Get probability (Confidence)
    # proba returns [Probability of 0, Probability of 1]
    prediction_prob = model.predict_proba(current_features)[0][1]
    
    current_price = latest_df['Close'].item()
    target_price = current_price * (1 + TARGET_GAIN)
    
    print(f"Current Price: {current_price:.2f}")
    print(f"Target Price (+{TARGET_GAIN:.0%}): {target_price:.2f} (in ~{PREDICTION_DAYS} trading days)")
    print(f"Model Confidence for UP Move: {prediction_prob:.2%}")
    
    if prediction_prob > 0.60:
        print("Verdict: 🟢 STRONG BUY SIGNAL (High Probability)")
    elif prediction_prob > 0.50:
        print("Verdict: 🟡 WEAK BUY SIGNAL (Lean Positive)")
    else:
        print("Verdict: 🔴 NO SIGNAL / WAIT")

    # Feature Importance (Optional: See what the AI cares about)
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    print("\nTop Factors influencing the AI:")
    for i in range(len(features)):
        print(f"{i+1}. {features[indices[i]]} ({importances[indices[i]]:.2f})")

if __name__ == "__main__":
    train_and_predict()