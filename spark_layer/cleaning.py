from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col,
    lit,
    trim,
    upper,
    to_date,
    when,
    coalesce,
    expr
)
from pyspark.sql.types import DoubleType, LongType, BooleanType


def normalize_stock_schema(df: DataFrame) -> DataFrame:
    """
    Normalize incoming stock data schema.
    Expected input columns:
    symbol, date or timestamp, open, high, low, close, volume, is_anomaly
    """

    # Normalize column names
    for old_col in df.columns:
        new_col = old_col.strip().lower().replace(" ", "_")
        if old_col != new_col:
            df = df.withColumnRenamed(old_col, new_col)

    # Add optional columns if missing
    if "is_anomaly" not in df.columns:
        df = df.withColumn("is_anomaly", lit(False))

    if "date" not in df.columns:
        df = df.withColumn("date", lit(None).cast("string"))

    if "timestamp" not in df.columns:
        df = df.withColumn("timestamp", lit(None).cast("string"))

    if "source" not in df.columns:
        df = df.withColumn("source", lit("psxdata"))

    if "stream_type" not in df.columns:
        df = df.withColumn("stream_type", lit("historical_replay"))

    # Cast columns
    df = df.withColumn("symbol", upper(trim(col("symbol").cast("string"))))
    df = df.withColumn(
        "event_time",
        coalesce(
            expr("try_to_timestamp(CAST(`timestamp` AS STRING))"),
            expr("try_to_timestamp(CAST(`date` AS STRING))"),
        )
    )
    df = df.withColumn("date", to_date(col("event_time")))

    df = df.withColumn("open", col("open").cast(DoubleType()))
    df = df.withColumn("high", col("high").cast(DoubleType()))
    df = df.withColumn("low", col("low").cast(DoubleType()))
    df = df.withColumn("close", col("close").cast(DoubleType()))
    df = df.withColumn("volume", col("volume").cast(LongType()))
    df = df.withColumn("is_anomaly", coalesce(col("is_anomaly").cast(BooleanType()), lit(False)))

    return df


def clean_stock_batch(df: DataFrame) -> DataFrame:
    """
    Cleaning function for foreachBatch or static DataFrame.
    This can safely remove duplicates.
    """

    df = normalize_stock_schema(df)

    # Remove rows with missing important fields
    df = df.dropna(
        subset=[
            "symbol",
            "date",
            "event_time",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]
    )
    df = df.filter(col("symbol") != "")

    # Basic valid price checks
    df = df.filter(
        (col("open") > 0) &
        (col("high") > 0) &
        (col("low") > 0) &
        (col("close") > 0) &
        (col("volume") >= 0)
    )

    # OHLC rule violation flag
    df = df.withColumn(
        "ohlc_violation",
        when(
            (col("high") < col("low")) |
            (col("high") < col("open")) |
            (col("high") < col("close")) |
            (col("low") > col("open")) |
            (col("low") > col("close")),
            lit(True)
        ).otherwise(lit(False))
    )

    # Keep anomaly rows but mark them
    df = df.withColumn(
        "is_anomaly",
        col("is_anomaly") | col("ohlc_violation")
    )

    # Remove duplicate symbol-date rows
    df = df.dropDuplicates(["symbol", "date"])

    return df


def clean_stock_stream(df: DataFrame) -> DataFrame:
    """
    Cleaning function for direct streaming DataFrame.
    Does not use dropDuplicates because streaming duplicate handling needs watermark.
    """

    df = normalize_stock_schema(df)

    df = df.dropna(
        subset=[
            "symbol",
            "date",
            "event_time",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]
    )
    df = df.filter(col("symbol") != "")

    df = df.filter(
        (col("open") > 0) &
        (col("high") > 0) &
        (col("low") > 0) &
        (col("close") > 0) &
        (col("volume") >= 0)
    )

    df = df.withColumn(
        "ohlc_violation",
        when(
            (col("high") < col("low")) |
            (col("high") < col("open")) |
            (col("high") < col("close")) |
            (col("low") > col("open")) |
            (col("low") > col("close")),
            lit(True)
        ).otherwise(lit(False))
    )

    df = df.withColumn(
        "is_anomaly",
        col("is_anomaly") | col("ohlc_violation")
    )

    return df
