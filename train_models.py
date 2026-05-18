"""
Train ML Models – Per‑symbol price predictors using historical CSV data
"""
import pandas as pd
import numpy as np
from pathlib import Path
from ml_models.price_predictor import PricePredictor

DATA_FILE = Path("data/cleaned_historical_prices.csv")
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

def train_per_symbol():
    if not DATA_FILE.exists():
        print(f"❌ CSV file not found: {DATA_FILE}")
        print("Please collect historical data first (run the app during market hours).")
        return

    df = pd.read_csv(DATA_FILE)
    # Ensure required columns exist
    required = ['symbol', 'price']
    if not all(col in df.columns for col in required):
        print(f"❌ CSV missing required columns. Found: {df.columns.tolist()}")
        return

    # Convert timestamp to datetime and sort
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(['symbol', 'timestamp'])

    trained = 0
    for symbol, group in df.groupby('symbol'):
        prices = group['price'].dropna().tolist()
        if len(prices) < 10:
            print(f"⚠️ Not enough data for {symbol} ({len(prices)} points), skipping.")
            continue

        # Train a new model for this symbol
        predictor = PricePredictor()
        success = predictor.train(prices)
        if success:
            # Save model with symbol-specific name
            model_file = MODELS_DIR / f"price_predictor_{symbol}.pkl"
            scaler_file = MODELS_DIR / f"price_scaler_{symbol}.pkl"
            # Override the default file names in the predictor instance
            predictor.model_file = model_file
            predictor.scaler_file = scaler_file
            predictor._save()  # manually save
            print(f"✅ Trained model for {symbol} (samples: {len(prices)})")
            trained += 1
        else:
            print(f"❌ Training failed for {symbol}")

    print(f"\n📊 Summary: Trained models for {trained} symbols.")
    print(f"Models saved in {MODELS_DIR}")

if __name__ == "__main__":
    print("="*50)
    print("Training Price Predictor Models (per symbol)")
    print("="*50)
    train_per_symbol()
    print("="*50)