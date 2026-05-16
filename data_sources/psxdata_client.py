from pathlib import Path
import sys

import pandas as pd
import psxdata


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.app_config import ALL_TICKERS_FILE, HISTORICAL_DIR, SAMPLE_DATA_FILE
from utils.sector_utils import add_sector_column
from utils.price_data_utils import clean_price_dataframe

START_DATE = "2016-05-09"
END_DATE = "2026-05-09"

SYMBOLS = [
    "HBL",
    "UBL",
    "MCB",
    "ENGRO",
    "LUCK",
    "OGDC",
    "PPL",
    "FFC",
    "PSO",
    "MARI"
]


def save_all_tickers():
    ALL_TICKERS_FILE.parent.mkdir(parents=True, exist_ok=True)

    tickers = psxdata.tickers(cache=False)

    df = pd.DataFrame({"symbol": tickers})
    df.to_csv(ALL_TICKERS_FILE, index=False)

    print(f"Saved total tickers: {len(df)}")


def download_historical_data():
    HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

    all_data = []

    for symbol in SYMBOLS:
        try:
            print(f"Downloading {symbol}...")

            df = psxdata.stocks(
                symbol,
                start=START_DATE,
                end=END_DATE,
                cache=False
            )

            if df is None or df.empty:
                print(f"No data found for {symbol}")
                continue

            df["symbol"] = symbol
            df["source"] = "psxdata"
            df["ingested_at"] = pd.Timestamp.now().isoformat(timespec="seconds")

            # Enrich and clean before writing. strict=True prevents price data
            # from being saved when a symbol is missing in the sector mapping.
            df = add_sector_column(df, strict=True)
            df, _ = clean_price_dataframe(
                df,
                strict_sector=True,
                source_default="psxdata",
                log_prefix=f"{symbol}:",
            )

            file_path = HISTORICAL_DIR / f"{symbol}.csv"
            df.to_csv(file_path, index=False)

            all_data.append(df)

            print(f"Saved {symbol}: {len(df)} rows")

        except Exception as e:
            print(f"Error downloading {symbol}: {e}")

    if not all_data:
        print("No data downloaded.")
        return

    final_df = pd.concat(all_data, ignore_index=True)

    final_df.to_csv(SAMPLE_DATA_FILE, index=False)

    print(f"Final merged dataset saved: {SAMPLE_DATA_FILE}")
    print("Shape:", final_df.shape)
    print("Columns:", final_df.columns.tolist())


def get_live_quote(symbol="HBL"):
    quote = psxdata.quote(symbol)
    print(quote)
    return quote


if __name__ == "__main__":
    save_all_tickers()
    download_historical_data()
