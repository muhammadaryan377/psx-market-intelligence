from pathlib import Path
import pandas as pd
import psxdata


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
    Path("data").mkdir(parents=True, exist_ok=True)

    tickers = psxdata.tickers(cache=False)

    df = pd.DataFrame({"symbol": tickers})
    df.to_csv("data/all_tickers.csv", index=False)

    print(f"Saved total tickers: {len(df)}")


def download_historical_data():
    Path("data/historical").mkdir(parents=True, exist_ok=True)

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

            file_path = f"data/historical/{symbol}.csv"
            df.to_csv(file_path, index=False)

            all_data.append(df)

            print(f"Saved {symbol}: {len(df)} rows")

        except Exception as e:
            print(f"Error downloading {symbol}: {e}")

    if not all_data:
        print("No data downloaded.")
        return

    final_df = pd.concat(all_data, ignore_index=True)

    final_df.to_csv("data/sample_psx_data.csv", index=False)

    print("Final merged dataset saved: data/sample_psx_data.csv")
    print("Shape:", final_df.shape)
    print("Columns:", final_df.columns.tolist())


def get_live_quote(symbol="HBL"):
    quote = psxdata.quote(symbol)
    print(quote)
    return quote


if __name__ == "__main__":
    save_all_tickers()
    download_historical_data()