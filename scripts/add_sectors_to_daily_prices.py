"""Add sector metadata to the daily PSX price dataset.

This script uses data/processed/psx_prices_100_daily.csv as the source of
truth for symbols. It creates or updates a sector mapping template, merges the
sector column into the daily prices, and reports symbols that still need sector
values.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DAILY_PRICES_PATH = PROJECT_ROOT / "data" / "processed" / "psx_prices_100_daily.csv"
SECTOR_TEMPLATE_PATH = PROJECT_ROOT / "data" / "metadata" / "psx_company_sectors.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "psx_prices_100_daily_with_sectors.csv"
MISSING_REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "missing_sector_symbols_daily.csv"


def normalize_symbol(value: object) -> str:
    """Normalize PSX symbols to the project's canonical format."""
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def load_daily_prices() -> pd.DataFrame:
    if not DAILY_PRICES_PATH.exists():
        raise FileNotFoundError(f"Daily price file not found: {DAILY_PRICES_PATH}")

    daily_prices = pd.read_csv(DAILY_PRICES_PATH, dtype={"symbol": "string"})
    if "symbol" not in daily_prices.columns:
        raise ValueError(f"Missing required 'symbol' column in {DAILY_PRICES_PATH}")

    daily_prices["symbol"] = daily_prices["symbol"].map(normalize_symbol)
    return daily_prices


def clean_sector_mapping(sectors: pd.DataFrame) -> pd.DataFrame:
    if "symbol" not in sectors.columns:
        raise ValueError(f"Missing required 'symbol' column in {SECTOR_TEMPLATE_PATH}")

    if "sector" not in sectors.columns:
        sectors["sector"] = ""

    sectors = sectors[["symbol", "sector"]].copy()
    sectors["symbol"] = sectors["symbol"].map(normalize_symbol)
    sectors["sector"] = sectors["sector"].fillna("").astype(str).str.strip()
    sectors = sectors[sectors["symbol"] != ""]

    # Preserve the first filled sector if duplicates collapse after normalization.
    sectors["_has_sector"] = sectors["sector"] != ""
    sectors = sectors.sort_values("_has_sector", ascending=False)
    sectors = sectors.drop_duplicates(subset=["symbol"], keep="first")
    return sectors.drop(columns=["_has_sector"]).sort_values("symbol").reset_index(drop=True)


def load_or_create_sector_template(symbols: list[str]) -> pd.DataFrame:
    SECTOR_TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if SECTOR_TEMPLATE_PATH.exists():
        sectors = pd.read_csv(SECTOR_TEMPLATE_PATH, dtype={"symbol": "string", "sector": "string"})
        sectors = clean_sector_mapping(sectors)
    else:
        sectors = pd.DataFrame(columns=["symbol", "sector"])

    existing_symbols = set(sectors["symbol"])
    new_symbols = [symbol for symbol in symbols if symbol not in existing_symbols]
    if new_symbols:
        additions = pd.DataFrame({"symbol": new_symbols, "sector": ""})
        sectors = pd.concat([sectors, additions], ignore_index=True)
        sectors = clean_sector_mapping(sectors)

    sectors.to_csv(SECTOR_TEMPLATE_PATH, index=False)
    return sectors


def write_outputs(daily_prices: pd.DataFrame, sectors: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    enriched = daily_prices.merge(sectors, on="symbol", how="left")
    enriched["sector"] = enriched["sector"].fillna("").astype(str).str.strip()

    missing_symbols = sorted(enriched.loc[enriched["sector"] == "", "symbol"].dropna().unique())
    missing_report = pd.DataFrame({"symbol": missing_symbols})

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    MISSING_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    enriched.to_csv(OUTPUT_PATH, index=False)
    missing_report.to_csv(MISSING_REPORT_PATH, index=False)
    return enriched, missing_report


def print_summary(enriched: pd.DataFrame, missing_report: pd.DataFrame) -> None:
    total_rows = len(enriched)
    total_symbols = enriched["symbol"].nunique()
    mapped_symbols = enriched.loc[enriched["sector"] != "", "symbol"].nunique()
    missing_symbols = len(missing_report)
    sector_distribution = (
        enriched.loc[enriched["sector"] != ""]
        .drop_duplicates(subset=["symbol"])
        ["sector"]
        .value_counts()
        .sort_index()
    )

    print(f"total rows: {total_rows}")
    print(f"total symbols: {total_symbols}")
    print(f"mapped symbols: {mapped_symbols}")
    print(f"missing symbols: {missing_symbols}")
    print("sector distribution:")
    if sector_distribution.empty:
        print("(none)")
    else:
        for sector, count in sector_distribution.items():
            print(f"{sector}: {count}")


def main() -> None:
    daily_prices = load_daily_prices()
    symbols = sorted(symbol for symbol in daily_prices["symbol"].dropna().unique() if symbol)
    sectors = load_or_create_sector_template(symbols)
    enriched, missing_report = write_outputs(daily_prices, sectors)
    print_summary(enriched, missing_report)


if __name__ == "__main__":
    main()
