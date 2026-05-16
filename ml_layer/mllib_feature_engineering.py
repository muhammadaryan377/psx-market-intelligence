from pyspark.sql import  DataFrame # type: ignore
from pyspark.sql.functions import col, when, lag, lead, avg, stddev , to_date # type: ignore
from pyspark.sql.window import Window # pyright: ignore[reportMissingImports]


FEATURE_COLS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "price_change",
    "volume_change",
    "ma_5",
    "ma_10",
    "ma_20",
    "volatility_5",
    "daily_range",
    "close_vs_ma5",
    "close_vs_ma10",
]

def create_features(df:DataFrame) -> DataFrame:
    """
    Create technical indicator features for stock price data.
    """

    df = df.withColumn(
        "data" ,
        to_date(col("date"))
    )

    numeric_cols = ["open", "high", "low", "close", "volume"]

    for c in numeric_cols:
        df= df.withColumn(
            c,
            col(c).cast("double")
        )
    df = df.withColumn("symbol", col("symbol").cast("string"))
    df = df.withColumn("sector", col("sector").cast("string"))

    symbol_window = Window.partitionBy("symbol").orderBy("data")

    window_5 = Window.partitionBy("symbol").orderBy("data").rowsBetween(-4, 0)
    window_10 = Window.partitionBy("symbol").orderBy("data").rowsBetween(-9, 0)
    window_20 = Window.partitionBy("symbol").orderBy("data").rowsBetween(-19, 0)



    df = df.withColumn(
        "prev_close",
        lag("close").over(symbol_window)
    )

    df = df.withColumn(
        "prev_volume",
        lag("volume").over(symbol_window)
    )

    df= df.withColumn(
        "next_close",
        lead("close").over(symbol_window)
    )

    df = df.withColumn(
        "price_change",
        (col("close") - col("prev_close")) / col("prev_close")
    )

    df = df.withColumn(
        "volume_change",
        (col("volume") - col("prev_volume")) / col("prev_volume")
    )

    df = df.withColumn(
        "ma_5",
        avg("close").over(window_5)
    )

    df = df.withColumn(
        "ma_10",
        avg("close").over(window_10)
    )

    df = df.withColumn(
        "ma_20",
        avg("close").over(window_20)
    )

    df = df.withColumn(
        "volatility_5",
        stddev("close").over(window_5)
    )

    df = df.withColumn(
        "daily_range",
        (col("high") - col("low")) / col("low")
    )

    df = df.withColumn(
        "close_vs_ma5",
        (col("close") - col("ma_5")) / col("ma_5")
    )

    df = df.withColumn(
        "close_vs_ma10",
        (col("close") - col("ma_10")) / col("ma_10")
    )

    df = df.withColumn(
        "next_return",
        (col("next_close") - col("close")) / col("close")
    )

    df =df.withColumn(
        "target",
        when(col("next_return") > 0.003, "UP")
        .when(col("next_return") < -0.003, "DOWN")
        .otherwise("STABLE")
    )

    required_cols = ["symbol", "date" , "sector"] + FEATURE_COLS + ["target"]
    df = df.dropna(subset=required_cols)
    return df
