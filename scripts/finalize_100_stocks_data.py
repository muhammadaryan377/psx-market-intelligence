from datetime import datetime
import time
import traceback
import re

import pandas as pd
import psxdata

from config.app_config import DATA_DIR, LOG_DIR, METADATA_DIR, PROCESSED_DIR, RAW_PRICE_DIR

# -----------------------------
# Project Settings
# -----------------------------

START_DATE = "2016-05-09"
END_DATE = "2026-05-09"

# Recent period used only to rank active/liquid stocks
RANK_START_DATE = "2025-05-09"
RANK_END_DATE = "2026-05-09"

TARGET_N = 100
MIN_RECENT_ROWS = 120
REQUEST_SLEEP_SECONDS = 0.3

# True rakho jab fresh ranking dobara banani ho
# Successful final run ke baad False kar sakte ho
FORCE_REBUILD_TARGET = False

ALL_TICKERS_FILE = METADATA_DIR / "all_tickers.csv"
FILTERED_TICKERS_FILE = METADATA_DIR / "filtered_common_stocks.csv"
LIQUIDITY_RANK_FILE = METADATA_DIR / "liquidity_rank.csv"
TARGET_100_FILE = METADATA_DIR / "target_100_stocks.csv"
FINAL_PRICE_FILE = PROCESSED_DIR / "psx_prices_100_daily.csv"
QUALITY_REPORT_FILE = PROCESSED_DIR / "psx_prices_100_quality_report.csv"
FAILED_SYMBOLS_FILE = LOG_DIR / "failed_symbols.csv"


def make_dirs():
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_PRICE_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def filter_common_stocks(tickers: list) -> list:
    """
    psxdata.tickers() main common stocks ke ilawa TFC, ETF, rights,
    bonds, preference shares aur inactive/non-common instruments bhi aa jate hain.
    Ye function sirf normal/common stock symbols rakhne ke liye hai.
    """

    bad_keywords = [
        "TFC",
        "ETF",
        "SUKUK",
        "BOND",
        "NCPS",
        "CPS",
        "PREF",
        "PREFERENCE",
        "RIGHT",
    ]

    clean_symbols = []

    for symbol in tickers:
        symbol = str(symbol).upper().strip()

        if not symbol:
            continue

        # pure numeric symbols remove, e.g. 786
        if symbol.isdigit():
            continue

        # weird characters remove
        if not re.match(r"^[A-Z0-9]+$", symbol):
            continue

        # Rights shares remove, e.g. 786R, AGICR2, ASCR1.
        if symbol.endswith("R"):
            continue

        if re.search(r"R\d+$", symbol):
            continue

        # TFC, ETF, preference shares, bonds remove
        if any(word in symbol for word in bad_keywords):
            continue

        # bohot zyada long symbols mostly instruments hote hain
        if len(symbol) > 10:
            continue

        clean_symbols.append(symbol)

    clean_symbols = sorted(set(clean_symbols))

    pd.DataFrame({"symbol": clean_symbols}).to_csv(FILTERED_TICKERS_FILE, index=False)

    print(f"Filtered common stock symbols: {len(clean_symbols)}")
    print(f"Saved filtered tickers: {FILTERED_TICKERS_FILE}")

    return clean_symbols


def standardize_columns(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    psxdata output ko standard schema main convert karta hai.
    Final schema:
    symbol, date, open, high, low, close, volume, source, collected_at
    """

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Agar date index main ho to column bana do
    if not isinstance(df.index, pd.RangeIndex):
        df = df.reset_index()

    # Column names normalize
    df.columns = [
        str(col).strip().lower().replace(" ", "_")
        for col in df.columns
    ]

    column_candidates = {
        "date": ["date", "index", "timestamp", "time"],
        "open": ["open", "open_price"],
        "high": ["high", "high_price"],
        "low": ["low", "low_price"],
        "close": ["close", "close_price", "closing_price"],
        "volume": ["volume", "vol", "trade_volume"],
    }

    selected = {}

    for final_col, candidates in column_candidates.items():
        for candidate in candidates:
            if candidate in df.columns:
                selected[final_col] = candidate
                break

    required = ["date", "open", "high", "low", "close", "volume"]
    missing = [col for col in required if col not in selected]

    if missing:
        raise ValueError(
            f"{symbol}: Missing columns {missing}. Available columns: {list(df.columns)}"
        )

    clean_df = df[
        [
            selected["date"],
            selected["open"],
            selected["high"],
            selected["low"],
            selected["close"],
            selected["volume"],
        ]
    ].copy()

    clean_df.columns = ["date", "open", "high", "low", "close", "volume"]

    clean_df["symbol"] = symbol.upper().strip()
    clean_df["date"] = pd.to_datetime(clean_df["date"], errors="coerce")

    for col in ["open", "high", "low", "close", "volume"]:
        clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce")

    clean_df["source"] = "psxdata"
    clean_df["collected_at"] = datetime.now().isoformat(timespec="seconds")

    clean_df = clean_df[
        [
            "symbol",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "source",
            "collected_at",
        ]
    ]

    clean_df = clean_df.dropna(subset=["symbol", "date", "open", "high", "low", "close"])
    clean_df = clean_df.drop_duplicates(subset=["symbol", "date"])

    # Basic OHLC validation yahin bhi apply kar dete hain
    valid_ohlc = (
        (clean_df["high"] >= clean_df[["open", "close", "low"]].max(axis=1))
        & (clean_df["low"] <= clean_df[["open", "close", "high"]].min(axis=1))
        & (clean_df["open"] > 0)
        & (clean_df["high"] > 0)
        & (clean_df["low"] > 0)
        & (clean_df["close"] > 0)
    )

    clean_df = clean_df[valid_ohlc].copy()

    clean_df["volume"] = clean_df["volume"].fillna(0)
    clean_df = clean_df[clean_df["volume"] >= 0]

    clean_df["date"] = clean_df["date"].dt.date
    clean_df = clean_df.sort_values(["symbol", "date"])

    return clean_df


def fetch_stock_data(symbol: str, start: str, end: str, retries: int = 3) -> pd.DataFrame:
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            print(f"Downloading {symbol} | attempt {attempt}")

            df = psxdata.stocks(
                symbol,
                start=start,
                end=end,
                cache=False,
            )

            clean_df = standardize_columns(df, symbol)

            if clean_df.empty:
                raise ValueError(f"{symbol}: empty dataframe after cleaning")

            return clean_df

        except Exception as error:
            last_error = error
            print(f"Failed {symbol} attempt {attempt}: {error}")
            time.sleep(attempt)

    raise last_error


def save_all_tickers() -> list:
    print("Fetching all PSX tickers...")

    tickers = psxdata.tickers(cache=False)
    tickers = sorted(set(str(t).upper().strip() for t in tickers if str(t).strip()))

    pd.DataFrame({"symbol": tickers}).to_csv(ALL_TICKERS_FILE, index=False)

    print(f"Saved all tickers: {len(tickers)}")
    print(f"Saved all tickers file: {ALL_TICKERS_FILE}")

    return tickers


def rank_stocks_by_liquidity(tickers: list) -> pd.DataFrame:
    """
    Recent 1 year average volume ke basis par stocks rank karta hai.
    Is se hum inactive stocks avoid karte hain.
    """

    rankings = []
    failures = []

    for index, symbol in enumerate(tickers, start=1):
        print(f"\nRanking {index}/{len(tickers)}: {symbol}")

        try:
            df = fetch_stock_data(symbol, RANK_START_DATE, RANK_END_DATE, retries=2)

            rows = len(df)
            avg_volume = df["volume"].mean()
            last_close = df.sort_values("date")["close"].iloc[-1]
            start_date = df["date"].min()
            end_date = df["date"].max()

            # Strong active stock filter
            if rows >= MIN_RECENT_ROWS and pd.notna(avg_volume) and avg_volume > 0:
                rankings.append(
                    {
                        "symbol": symbol,
                        "rows_recent": rows,
                        "avg_volume_recent": round(float(avg_volume), 2),
                        "last_close": float(last_close),
                        "data_start": start_date,
                        "data_end": end_date,
                    }
                )
            else:
                print(
                    f"Skipped {symbol}: rows={rows}, avg_volume={avg_volume}"
                )

        except Exception as error:
            failures.append(
                {
                    "symbol": symbol,
                    "stage": "ranking",
                    "error": str(error),
                }
            )

        time.sleep(REQUEST_SLEEP_SECONDS)

    rank_df = pd.DataFrame(rankings)

    if rank_df.empty:
        raise RuntimeError("No stocks ranked. Check psxdata connection/source.")

    rank_df = rank_df.sort_values(
        ["avg_volume_recent", "rows_recent"],
        ascending=[False, False],
    )

    rank_df.to_csv(LIQUIDITY_RANK_FILE, index=False)

    target_df = rank_df.head(TARGET_N).copy()
    target_df.to_csv(TARGET_100_FILE, index=False)

    if failures:
        pd.DataFrame(failures).to_csv(FAILED_SYMBOLS_FILE, index=False)

    print(f"\nSaved liquidity ranking: {LIQUIDITY_RANK_FILE}")
    print(f"Saved target {TARGET_N} stocks: {TARGET_100_FILE}")
    print(f"Ranked usable stocks: {len(rank_df)}")

    if len(rank_df) < TARGET_N:
        print(
            f"WARNING: Only {len(rank_df)} usable stocks found. "
            f"Target was {TARGET_N}."
        )

    return target_df


def download_full_history(target_symbols: list) -> pd.DataFrame:
    all_data = []
    failures = []

    for index, symbol in enumerate(target_symbols, start=1):
        print(f"\nFull history {index}/{len(target_symbols)}: {symbol}")

        try:
            df = fetch_stock_data(symbol, START_DATE, END_DATE, retries=3)

            raw_file = RAW_PRICE_DIR / f"{symbol}.csv"
            df.to_csv(raw_file, index=False)

            all_data.append(df)

        except Exception as error:
            print(f"Final download failed for {symbol}: {error}")

            failures.append(
                {
                    "symbol": symbol,
                    "stage": "full_history",
                    "error": str(error),
                    "trace": traceback.format_exc(),
                }
            )

        time.sleep(REQUEST_SLEEP_SECONDS)

    if failures:
        failed_df = pd.DataFrame(failures)

        if FAILED_SYMBOLS_FILE.exists():
            old_failed = pd.read_csv(FAILED_SYMBOLS_FILE)
            failed_df = pd.concat([old_failed, failed_df], ignore_index=True)

        failed_df.to_csv(FAILED_SYMBOLS_FILE, index=False)

    if not all_data:
        raise RuntimeError("No full historical data downloaded.")

    final_df = pd.concat(all_data, ignore_index=True)
    final_df = clean_final_dataset(final_df)

    final_df.to_csv(FINAL_PRICE_FILE, index=False)

    print(f"\nSaved final price dataset: {FINAL_PRICE_FILE}")
    print(f"Total rows: {len(final_df)}")
    print(f"Total symbols: {final_df['symbol'].nunique()}")

    return final_df


def clean_final_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["symbol", "date", "open", "high", "low", "close"])
    df = df.drop_duplicates(subset=["symbol", "date"])

    valid_ohlc = (
        (df["high"] >= df[["open", "close", "low"]].max(axis=1))
        & (df["low"] <= df[["open", "close", "high"]].min(axis=1))
        & (df["open"] > 0)
        & (df["high"] > 0)
        & (df["low"] > 0)
        & (df["close"] > 0)
    )

    df = df[valid_ohlc].copy()

    df["volume"] = df["volume"].fillna(0)
    df = df[df["volume"] >= 0]

    df["date"] = df["date"].dt.date
    df = df.sort_values(["symbol", "date"])

    return df


def build_quality_report(df: pd.DataFrame):
    report = (
        df.groupby("symbol")
        .agg(
            rows=("date", "count"),
            start_date=("date", "min"),
            end_date=("date", "max"),
            avg_volume=("volume", "mean"),
            min_close=("close", "min"),
            max_close=("close", "max"),
        )
        .reset_index()
    )

    report["avg_volume"] = report["avg_volume"].round(2)
    report.to_csv(QUALITY_REPORT_FILE, index=False)

    print(f"Saved quality report: {QUALITY_REPORT_FILE}")


def main():
    make_dirs()

    tickers = save_all_tickers()

    # Important: useless PSX symbols filter
    tickers = filter_common_stocks(tickers)

    if TARGET_100_FILE.exists() and not FORCE_REBUILD_TARGET:
        print(f"\nTarget 100 file already exists: {TARGET_100_FILE}")
        print("Using existing target_100_stocks.csv")
        target_df = pd.read_csv(TARGET_100_FILE)
    else:
        print("\nBuilding fresh target stock list...")
        target_df = rank_stocks_by_liquidity(tickers)

    target_symbols = (
        target_df["symbol"]
        .astype(str)
        .str.upper()
        .str.strip()
        .drop_duplicates()
        .head(TARGET_N)
        .tolist()
    )

    print("\nFinal target symbols:")
    print(target_symbols)

    final_df = download_full_history(target_symbols)
    build_quality_report(final_df)

    print("\nDATA FINALIZATION COMPLETE")


if __name__ == "__main__":
    main()
