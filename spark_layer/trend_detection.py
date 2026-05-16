"""
PySpark Trend Detection - Identify market trends using Spark
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.window import Window


def create_spark_session():
    return SparkSession.builder \
        .appName("PSXTrendDetection") \
        .getOrCreate()


def calculate_moving_average(df, symbol_col="symbol", price_col="price", window_size=20):
    """Calculate moving average for each stock"""
    window_spec = Window.partitionBy(symbol_col).orderBy("timestamp").rowsBetween(-window_size, 0)
    
    return df.withColumn(
        f"ma_{window_size}",
        avg(price_col).over(window_spec)
    )


def calculate_rsi(df, symbol_col="symbol", price_col="price", period=14):
    """Calculate RSI (Relative Strength Index) for each stock"""
    window_spec = Window.partitionBy(symbol_col).orderBy("timestamp")
    
    # Calculate price changes
    df_with_changes = df.withColumn(
        "price_change",
        col(price_col) - lag(price_col).over(window_spec)
    )
    
    # Calculate gains and losses
    df_with_gl = df_with_changes.withColumn(
        "gain", when(col("price_change") > 0, col("price_change")).otherwise(0)
    ).withColumn(
        "loss", when(col("price_change") < 0, -col("price_change")).otherwise(0)
    )
    
    # Calculate average gain and loss
    avg_window = Window.partitionBy(symbol_col).orderBy("timestamp").rowsBetween(-period, 0)
    
    df_with_avg = df_with_gl.withColumn(
        "avg_gain", avg("gain").over(avg_window)
    ).withColumn(
        "avg_loss", avg("loss").over(avg_window)
    )
    
    # Calculate RSI
    return df_with_avg.withColumn(
        "rsi",
        when(col("avg_loss") == 0, 100)
        .otherwise(100 - (100 / (1 + (col("avg_gain") / col("avg_loss")))))
    )


def detect_trend(df, ma_short=20, ma_long=50):
    """Detect trend using moving averages"""
    df = calculate_moving_average(df, window_size=ma_short)
    df = calculate_moving_average(df, window_size=ma_long)
    
    return df.withColumn(
        "trend",
        when(col(f"ma_{ma_short}") > col(f"ma_{ma_long}"), "UPTREND")
        .when(col(f"ma_{ma_short}") < col(f"ma_{ma_long}"), "DOWNTREND")
        .otherwise("SIDEWAYS")
    )


def run_trend_analysis():
    """Run trend analysis on historical data"""
    spark = create_spark_session()
    
    # Read data
    df = spark.read.csv("data/historical_prices.csv", header=True, inferSchema=True)
    
    # Calculate trends
    df_with_trend = detect_trend(df)
    
    # Show results
    df_with_trend.select("symbol", "timestamp", "price", "trend", "rsi").show(20)
    
    return df_with_trend