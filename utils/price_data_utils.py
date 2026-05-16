"""Shared cleaning, validation, and reporting helpers for PSX price data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils.sector_utils import add_sector_column


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUALITY_REPORT_FILE = PROJECT_ROOT / "data" / "reports" / "price_data_quality_report.csv"

STANDARD_PRICE_COLUMNS = [
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source",
    "ingested_at",
    "sector",
]


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with lowercase snake-like column names."""
    cleaned = df.copy()
    cleaned.columns = [str(col).strip().lower().replace(" ", "_") for col in cleaned.columns]
    return cleaned


def clean_price_dataframe(
    df: pd.DataFrame,
    *,
    strict_sector: bool = True,
    source_default: str = "psxdata",
    log_prefix: str = "",
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Clean a PSX price dataframe and enforce the standard schema.

    The returned dataframe always has STANDARD_PRICE_COLUMNS in the required
    order. Bad rows are removed and counted, not ignored silently.
    """
    if df is None:
        raise ValueError("Price dataframe is None.")

    if not isinstance(df.index, pd.RangeIndex):
        df = df.reset_index()

    cleaned = normalize_column_names(df)
    input_rows = len(cleaned)

    # Older files used collected_at. The new pipeline standard is ingested_at.
    if "ingested_at" not in cleaned.columns and "collected_at" in cleaned.columns:
        cleaned = cleaned.rename(columns={"collected_at": "ingested_at"})

    base_required = ["symbol", "date", "open", "high", "low", "close", "volume"]
    missing_base = [col for col in base_required if col not in cleaned.columns]
    if missing_base:
        raise ValueError(f"Price dataframe is missing required column(s): {missing_base}")

    if "source" not in cleaned.columns:
        cleaned["source"] = source_default
    if "ingested_at" not in cleaned.columns:
        cleaned["ingested_at"] = pd.Timestamp.now().isoformat(timespec="seconds")

    cleaned["symbol"] = cleaned["symbol"].fillna("").astype(str).str.strip().str.upper()
    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")

    for col in ["open", "high", "low", "close", "volume"]:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    cleaned["source"] = cleaned["source"].fillna(source_default).astype(str).str.strip()
    cleaned.loc[cleaned["source"] == "", "source"] = source_default
    cleaned["ingested_at"] = cleaned["ingested_at"].fillna("").astype(str).str.strip()
    cleaned.loc[cleaned["ingested_at"] == "", "ingested_at"] = pd.Timestamp.now().isoformat(timespec="seconds")

    before_required_drop = len(cleaned)
    cleaned = cleaned.dropna(subset=["date", "open", "high", "low", "close", "volume"])
    cleaned = cleaned[cleaned["symbol"] != ""].copy()
    removed_missing_required = before_required_drop - len(cleaned)

    # OHLC sanity checks for daily candles.
    valid_ohlc = (
        (cleaned["high"] >= cleaned["low"])
        & (cleaned["high"] >= cleaned["open"])
        & (cleaned["high"] >= cleaned["close"])
        & (cleaned["low"] <= cleaned["open"])
        & (cleaned["low"] <= cleaned["close"])
        & (cleaned["open"] > 0)
        & (cleaned["high"] > 0)
        & (cleaned["low"] > 0)
        & (cleaned["close"] > 0)
        & (cleaned["volume"] >= 0)
    )

    removed_invalid_ohlc = int((~valid_ohlc).sum())
    cleaned = cleaned[valid_ohlc].copy()

    before_duplicates = len(cleaned)
    cleaned = cleaned.sort_values(["symbol", "date", "ingested_at"])
    cleaned = cleaned.drop_duplicates(subset=["symbol", "date"], keep="last")
    removed_duplicates = before_duplicates - len(cleaned)

    cleaned["date"] = cleaned["date"].dt.strftime("%Y-%m-%d")
    cleaned["volume"] = cleaned["volume"].round().astype("int64")

    cleaned = add_sector_column(cleaned, strict=strict_sector)

    missing_final = [col for col in STANDARD_PRICE_COLUMNS if col not in cleaned.columns]
    if missing_final:
        raise ValueError(f"Cleaned price dataframe is missing final column(s): {missing_final}")

    cleaned = cleaned[STANDARD_PRICE_COLUMNS].sort_values(["symbol", "date"]).reset_index(drop=True)

    stats = {
        "input_rows": input_rows,
        "output_rows": len(cleaned),
        "removed_missing_required_rows": removed_missing_required,
        "removed_invalid_rows": removed_invalid_ohlc,
        "removed_duplicate_rows": removed_duplicates,
        "total_removed_rows": input_rows - len(cleaned),
        "total_symbols": cleaned["symbol"].nunique(),
        "total_sectors": cleaned["sector"].nunique(),
        "missing_sector_symbols_count": cleaned.loc[cleaned["sector"] == "", "symbol"].nunique(),
    }

    label = f"{log_prefix} " if log_prefix else ""
    print(f"{label}input rows: {stats['input_rows']}")
    print(f"{label}output rows: {stats['output_rows']}")
    print(f"{label}total symbols: {stats['total_symbols']}")
    print(f"{label}total sectors: {stats['total_sectors']}")
    print(f"{label}missing sector symbols count: {stats['missing_sector_symbols_count']}")
    print(f"{label}removed invalid rows count: {stats['removed_invalid_rows']}")
    print(f"{label}removed duplicate rows count: {stats['removed_duplicate_rows']}")

    return cleaned, stats


def build_price_quality_report(
    df: pd.DataFrame,
    output_path: Path = QUALITY_REPORT_FILE,
) -> pd.DataFrame:
    """Create the per-symbol price data quality report."""
    missing = [col for col in ["symbol", "sector", "date", "volume", "close"] if col not in df.columns]
    if missing:
        raise ValueError(f"Cannot build quality report. Missing column(s): {missing}")

    report = (
        df.groupby(["symbol", "sector"], dropna=False)
        .agg(
            rows=("date", "count"),
            start_date=("date", "min"),
            end_date=("date", "max"),
            avg_volume=("volume", "mean"),
            min_close=("close", "min"),
            max_close=("close", "max"),
        )
        .reset_index()
        .sort_values("symbol")
    )

    report["avg_volume"] = report["avg_volume"].round(2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_path, index=False)
    return report
