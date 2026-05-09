from pyspark.sql import DataFrame
from pyspark.sql.window import Window
from pyspark.sql.functions import (
    col,
    avg,
    lag,
    when,
    lit,
    round,
    abs as spark_abs,
    coalesce
)


def add_trend_signals(
    df: DataFrame,
    moving_average_days: int = 5,
    stable_threshold: float = 0.005,
    volume_multiplier: float = 2.0
) -> DataFrame:
    """
    Adds moving average, price change, trend, and event type.

    Trend rules:
    close > moving_average  => UP
    close < moving_average  => DOWN
    close near MA           => STABLE
    """

    price_window = (
        Window
        .partitionBy("symbol")
        .orderBy("event_time")
        .rowsBetween(-(moving_average_days - 1), 0)
    )

    order_window = (
        Window
        .partitionBy("symbol")
        .orderBy("event_time")
    )

    volume_window = (
        Window
        .partitionBy("symbol")
        .orderBy("event_time")
        .rowsBetween(-(moving_average_days - 1), 0)
    )

    df = df.withColumn(
        "moving_average",
        round(avg(col("close")).over(price_window), 4)
    )

    df = df.withColumn(
        "previous_close",
        lag(col("close")).over(order_window)
    )

    df = df.withColumn(
        "price_change",
        round(
            col("close") - coalesce(col("previous_close"), col("close")),
            4
        )
    )

    df = df.withColumn(
        "price_change_pct",
        round(
            when(
                col("previous_close").isNotNull() & (col("previous_close") > 0),
                ((col("close") - col("previous_close")) / col("previous_close")) * 100
            ).otherwise(lit(0.0)),
            4
        )
    )

    df = df.withColumn(
        "avg_volume",
        round(avg(col("volume")).over(volume_window), 2)
    )

    df = df.withColumn(
        "ma_difference_pct",
        round(
            when(
                col("moving_average") > 0,
                ((col("close") - col("moving_average")) / col("moving_average")) * 100
            ).otherwise(lit(0.0)),
            4
        )
    )

    df = df.withColumn(
        "trend",
        when(
            spark_abs((col("close") - col("moving_average")) / col("moving_average")) <= stable_threshold,
            lit("STABLE")
        )
        .when(col("close") > col("moving_average"), lit("UP"))
        .when(col("close") < col("moving_average"), lit("DOWN"))
        .otherwise(lit("STABLE"))
    )

    df = df.withColumn(
        "event_type",
        when(col("is_anomaly") == True, lit("anomaly_detected"))
        .when(col("volume") > (col("avg_volume") * volume_multiplier), lit("unusual_volume"))
        .when(col("trend") == "UP", lit("price_up"))
        .when(col("trend") == "DOWN", lit("price_down"))
        .otherwise(lit("stable_market"))
    )

    df = df.withColumn(
        "confidence_hint",
        when(col("is_anomaly") == True, lit(0.40))
        .when(col("event_type") == "unusual_volume", lit(0.65))
        .when(col("trend").isin("UP", "DOWN"), lit(0.75))
        .otherwise(lit(0.55))
    )

    return df