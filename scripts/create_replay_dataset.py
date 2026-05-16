"""Create replay and ML-training price datasets without leakage.

Run from project root:
    python scripts/create_replay_dataset.py

Replay uses the latest 30 calendar days found in the clean daily price file.
Training data excludes that replay period.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.price_data_utils import STANDARD_PRICE_COLUMNS, clean_price_dataframe


INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "psx_prices_100_daily_clean.csv"
REPLAY_OUTPUT_FILE = PROJECT_ROOT / "data" / "replay" / "psx_replay_last_30_days.csv"
TRAINING_OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "ml_training_prices.csv"
REPLAY_DAYS = 30


def print_dataset_summary(label: str, df: pd.DataFrame, path: Path) -> None:
    print(f"{label} output rows: {len(df)}")
    print(f"{label} total symbols: {df['symbol'].nunique()}")
    print(f"{label} total sectors: {df['sector'].nunique()}")
    print(f"{label} missing sector symbols count: {df.loc[df['sector'] == '', 'symbol'].nunique()}")
    print(f"{label} output file path: {path}")


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Clean price file not found: {INPUT_FILE}. Run scripts/clean_price_data.py first."
        )

    print(f"Reading clean input file: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)
    clean_df, stats = clean_price_dataframe(
        df,
        strict_sector=True,
        source_default="psxdata",
        log_prefix="replay-source:",
    )

    clean_df["date"] = pd.to_datetime(clean_df["date"], errors="coerce")
    latest_date = clean_df["date"].max()
    if pd.isna(latest_date):
        raise ValueError("Cannot create replay dataset because no valid dates were found.")

    replay_start_date = latest_date - pd.Timedelta(days=REPLAY_DAYS - 1)
    replay_df = clean_df[clean_df["date"] >= replay_start_date].copy()
    training_df = clean_df[clean_df["date"] < replay_start_date].copy()

    if replay_df.empty:
        raise ValueError("Replay dataset is empty after applying the latest 30-day window.")
    if training_df.empty:
        raise ValueError("Training dataset is empty after excluding the replay period.")

    for output_df in [replay_df, training_df]:
        output_df["date"] = output_df["date"].dt.strftime("%Y-%m-%d")

    replay_df = replay_df[STANDARD_PRICE_COLUMNS].sort_values(["symbol", "date"]).reset_index(drop=True)
    training_df = training_df[STANDARD_PRICE_COLUMNS].sort_values(["symbol", "date"]).reset_index(drop=True)

    REPLAY_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRAINING_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    replay_df.to_csv(REPLAY_OUTPUT_FILE, index=False)
    training_df.to_csv(TRAINING_OUTPUT_FILE, index=False)

    print(f"input rows: {stats['input_rows']}")
    print(f"latest date: {latest_date.date()}")
    print(f"replay start date: {replay_start_date.date()}")
    print(f"removed invalid rows count: {stats['removed_invalid_rows']}")
    print_dataset_summary("replay", replay_df, REPLAY_OUTPUT_FILE)
    print_dataset_summary("training", training_df, TRAINING_OUTPUT_FILE)


if __name__ == "__main__":
    main()
