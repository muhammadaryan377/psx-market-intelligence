import pandas as pd
from pathlib import Path
from ml_models.price_predictor import PricePredictor

DATA_FILE = Path("data/cleaned_historical_prices.csv")
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

def train_per_symbol():
    if not DATA_FILE.exists():
        print(f"❌ Cleaned data file not found: {DATA_FILE}")
        print("Please run clean_historical_data.py first.")
        return

    df = pd.read_csv(DATA_FILE)
    # Ensure required columns
    if "symbol" not in df.columns or "price" not in df.columns:
        print("❌ CSV must have 'symbol' and 'price' columns")
        return

    # Group by symbol
    trained = 0
    for symbol, group in df.groupby("symbol"):
        group = group.sort_values("timestamp" if "timestamp" in df.columns else "date")
        prices = group["price"].tolist()

        if len(prices) < 10:
            print(f"⚠️ Not enough data for {symbol} ({len(prices)} points), skipping")
            continue

        # Train model for this symbol
        predictor = PricePredictor(symbol=symbol)   # note: pass symbol
        success = predictor.train(prices)
        if success:
            predictor._save()   # now the method exists
            print(f"✅ Trained {symbol} (samples: {len(prices)})")
            trained += 1
        else:
            print(f"❌ Training failed for {symbol}")

    print(f"\n📊 Trained models for {trained} symbols.")

if __name__ == "__main__":
    train_per_symbol()