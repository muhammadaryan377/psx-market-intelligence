"""Sector mapping helpers for PSX price datasets.

These helpers keep sector enrichment consistent across collectors and cleaning
scripts. They never guess a sector. Missing symbols are written to a report so
the mapping file can be fixed by a human.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECTOR_MAPPING_FILE = PROJECT_ROOT / "data" / "metadata" / "psx_company_sectors.csv"
MISSING_SECTOR_REPORT_FILE = PROJECT_ROOT / "data" / "reports" / "missing_sector_symbols.csv"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with simple lowercase column names."""
    cleaned = df.copy()
    cleaned.columns = [str(col).strip().lower().replace(" ", "_") for col in cleaned.columns]
    return cleaned


def _clean_text_series(series: pd.Series) -> pd.Series:
    """Convert values to uppercase strings and remove surrounding spaces."""
    return series.fillna("").astype(str).str.strip().str.upper()


def load_sector_mapping() -> pd.DataFrame:
    """Load and validate the symbol-to-sector mapping file.

    Returns:
        A dataframe with exactly these columns: symbol, sector.
    """
    if not SECTOR_MAPPING_FILE.exists():
        raise FileNotFoundError(f"Sector mapping file not found: {SECTOR_MAPPING_FILE}")

    mapping = pd.read_csv(SECTOR_MAPPING_FILE, dtype="string")
    mapping = _normalize_columns(mapping)

    required_columns = {"symbol", "sector"}
    missing_columns = required_columns.difference(mapping.columns)
    if missing_columns:
        raise ValueError(
            f"Sector mapping file is missing columns {sorted(missing_columns)}: "
            f"{SECTOR_MAPPING_FILE}"
        )

    mapping = mapping[["symbol", "sector"]].copy()
    mapping["symbol"] = _clean_text_series(mapping["symbol"])
    mapping["sector"] = _clean_text_series(mapping["sector"])
    mapping = mapping[mapping["symbol"] != ""]

    # If the same symbol appears more than once, the latest row is treated as
    # the correction and is kept.
    mapping = mapping.drop_duplicates(subset=["symbol"], keep="last")
    return mapping.reset_index(drop=True)


def add_sector_column(df: pd.DataFrame, strict: bool = False) -> pd.DataFrame:
    """Add or clean the sector column on a price dataframe.

    Args:
        df: Price dataframe containing at least a symbol column.
        strict: When True, raise an error if any symbol still has no sector.

    Returns:
        A dataframe with normalized columns and a sector column.
    """
    if df is None:
        raise ValueError("Cannot add sector column to None dataframe.")

    enriched = _normalize_columns(df)
    if "symbol" not in enriched.columns:
        raise ValueError("Price dataframe must contain a 'symbol' column before sector enrichment.")

    enriched["symbol"] = _clean_text_series(enriched["symbol"])

    if "sector" in enriched.columns:
        existing_sector = _clean_text_series(enriched["sector"])
        enriched = enriched.drop(columns=["sector"])
    else:
        existing_sector = pd.Series("", index=enriched.index, dtype="string")

    enriched = enriched.reset_index(drop=True)
    existing_sector = existing_sector.reset_index(drop=True)

    sector_mapping = load_sector_mapping()
    enriched = enriched.merge(sector_mapping, on="symbol", how="left")
    enriched["sector"] = _clean_text_series(enriched["sector"])

    # Keep any pre-existing non-empty sector only when the mapping file does not
    # have a value. The mapping file remains the main source of truth.
    existing_sector = existing_sector.reindex(enriched.index).fillna("").astype(str).str.strip().str.upper()
    enriched.loc[enriched["sector"] == "", "sector"] = existing_sector[enriched["sector"] == ""]

    missing_symbols = sorted(
        symbol for symbol in enriched.loc[enriched["sector"] == "", "symbol"].dropna().unique() if symbol
    )

    MISSING_SECTOR_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"symbol": missing_symbols}).to_csv(MISSING_SECTOR_REPORT_FILE, index=False)

    if strict and missing_symbols:
        preview = ", ".join(missing_symbols[:20])
        if len(missing_symbols) > 20:
            preview += ", ..."
        raise ValueError(
            f"Missing sector mapping for {len(missing_symbols)} symbol(s). "
            f"Report saved to {MISSING_SECTOR_REPORT_FILE}. Symbols: {preview}"
        )

    return enriched
