"""Clean the standard PSX daily price dataset.

Run from project root:
    python scripts/clean_price_data.py

The script validates OHLC rows, enforces sector enrichment, writes a clean copy,
and refreshes the price data quality report.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.price_data_utils import clean_price_dataframe, build_price_quality_report


INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "psx_prices_100_daily.csv"
CLEAN_OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "psx_prices_100_daily_clean.csv"
QUALITY_REPORT_FILE = PROJECT_ROOT / "data" / "reports" / "price_data_quality_report.csv"
STANDARD_OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "psx_prices_100_daily.csv"


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input price file not found: {INPUT_FILE}")

    print(f"Reading input file: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)

    clean_df, stats = clean_price_dataframe(
        df,
        strict_sector=True,
        source_default="psxdata",
        log_prefix="clean:",
    )

    CLEAN_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(CLEAN_OUTPUT_FILE, index=False)

    # Keep the standard processed file in the same enforced schema too. This is
    # useful when the input was an older file with collected_at instead of
    # ingested_at or without sector.
    clean_df.to_csv(STANDARD_OUTPUT_FILE, index=False)

    report = build_price_quality_report(clean_df, QUALITY_REPORT_FILE)

    print(f"output file path: {CLEAN_OUTPUT_FILE}")
    print(f"standard file path: {STANDARD_OUTPUT_FILE}")
    print(f"quality report path: {QUALITY_REPORT_FILE}")
    print(f"quality report rows: {len(report)}")
    print(f"removed invalid rows count: {stats['removed_invalid_rows']}")


if __name__ == "__main__":
    main()
