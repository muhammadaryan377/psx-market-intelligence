from pathlib import Path
import sys

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit, current_timestamp


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.app_config import TREND_OUTPUT_DIR


DEFAULT_OUTPUT_DIR = str(TREND_OUTPUT_DIR)


FINAL_COLUMNS = [
    "symbol",
    "date",
    "event_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "moving_average",
    "previous_close",
    "price_change",
    "price_change_pct",
    "ma_difference_pct",
    "trend_reference_price",
    "trend_reference_change",
    "avg_volume",
    "trend",
    "event_type",
    "is_anomaly",
    "ohlc_violation",
    "confidence_hint",
    "source",
    "stream_type"
]


def select_output_columns(df: DataFrame) -> DataFrame:
    """
    Select only final columns that exist in DataFrame.
    """

    existing_columns = [c for c in FINAL_COLUMNS if c in df.columns]
    return df.select(*existing_columns)


def show_processed_batch(df: DataFrame, rows: int = 20) -> None:
    """
    Show processed trends in console for demo/testing.
    """

    output_df = select_output_columns(df)

    output_df.orderBy(col("symbol"), col("date")).show(
        rows,
        truncate=False
    )


def write_processed_batch(
    batch_df: DataFrame,
    batch_id: int,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    output_format: str = "json",
    show_console: bool = True
) -> None:
    """
    Used inside foreachBatch.
    Writes processed PySpark output to local folder.
    """

    if batch_df.limit(1).count() == 0:
        print(f"Batch {batch_id}: empty batch skipped.")
        return

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    output_df = select_output_columns(batch_df)
    output_df = output_df.dropDuplicates(["symbol", "date", "event_type", "trend"])

    output_df = output_df.withColumn("batch_id", lit(int(batch_id)))
    output_df = output_df.withColumn("processed_at", current_timestamp())

    if show_console:
        print(f"\n========== Processed Batch {batch_id} ==========")
        output_df.orderBy(col("symbol"), col("date")).show(20, truncate=False)

    if output_format == "json":
        (
            output_df
            .coalesce(1)
            .write
            .mode("append")
            .json(output_dir)
        )

    elif output_format == "csv":
        (
            output_df
            .coalesce(1)
            .write
            .mode("append")
            .option("header", True)
            .csv(output_dir)
        )

    elif output_format == "parquet":
        (
            output_df
            .write
            .mode("append")
            .parquet(output_dir)
        )

    else:
        raise ValueError(
            "Invalid output_format. Use: json, csv, or parquet"
        )

    print(f"Batch {batch_id}: written to {output_dir}")


def write_latest_snapshot(
    df: DataFrame,
    output_dir: str = "data/processed/latest_snapshot"
) -> None:
    """
    Optional helper for saving latest processed snapshot.
    Useful for Flask dashboard later.
    """

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    output_df = select_output_columns(df)

    (
        output_df
        .coalesce(1)
        .write
        .mode("overwrite")
        .option("header", True)
        .csv(output_dir)
    )

    print(f"Latest snapshot written to {output_dir}")
