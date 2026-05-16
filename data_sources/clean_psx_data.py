from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.app_config import CLEANED_DATA_FILE, SAMPLE_DATA_FILE
from utils.price_data_utils import clean_price_dataframe


RAW_FILE = SAMPLE_DATA_FILE
CLEAN_FILE = CLEANED_DATA_FILE


def clean_psx_data():
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Raw file not found: {RAW_FILE}")

    CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(RAW_FILE)
    df, _ = clean_price_dataframe(
        df,
        strict_sector=True,
        source_default="psxdata",
        log_prefix="legacy-clean:",
    )

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

    print("\nSector count:")
    print(df["sector"].value_counts())


if __name__ == "__main__":
    clean_psx_data()
