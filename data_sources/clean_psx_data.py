from pathlib import Path
import pandas as pd


RAW_FILE = Path("data/sample_psx_data.csv")
CLEAN_FILE = Path("data/processed/psx_cleaned_data.csv")


def clean_psx_data():
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Raw file not found: {RAW_FILE}")

    CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(RAW_FILE)

    # Normalize column names
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    # Convert date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Remove rows with missing important fields
    df = df.dropna(subset=["date", "symbol", "open", "high", "low", "close", "volume"])

    # Convert numeric columns
    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=numeric_cols)

    # Sort by symbol and date
    df = df.sort_values(by=["symbol", "date"])

    # Remove duplicate symbol-date rows
    df = df.drop_duplicates(subset=["symbol", "date"], keep="last")

    # Keep anomaly column, but make sure it exists
    if "is_anomaly" not in df.columns:
        df["is_anomaly"] = False

    # Add source metadata
    df["source"] = "psxdata"
    df["stream_type"] = "historical_replay"

    # Save cleaned data
    df.to_csv(CLEAN_FILE, index=False)

    print("Cleaned data saved:", CLEAN_FILE)
    print("Shape:", df.shape)
    print("Date range:", df["date"].min(), "to", df["date"].max())

    print("\nSymbol-wise summary:")
    print(
        df.groupby("symbol")["date"]
        .agg(["min", "max", "count"])
        .reset_index()
    )

    print("\nAnomaly count:")
    print(df["is_anomaly"].value_counts())


if __name__ == "__main__":
    clean_psx_data()