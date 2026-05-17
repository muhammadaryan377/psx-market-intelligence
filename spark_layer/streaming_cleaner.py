from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, to_timestamp, row_number, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType
from pyspark.sql.window import Window
import pandas as pd
from pathlib import Path
import joblib
import numpy as np
from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import MinMaxScaler

# ------------------------------
# Incremental model updater (in‑memory cache)
# ------------------------------
class ModelCache:
    def __init__(self):
        self.predictors = {}   # symbol -> PricePredictor instance

    def get_predictor(self, symbol):
        if symbol not in self.predictors:
            self.predictors[symbol] = PricePredictor(symbol)
        return self.predictors[symbol]

    def update_model(self, symbol, new_prices):
        predictor = self.get_predictor(symbol)
        # Prepare features: use time indices (0,1,2,...) as X, next price as y
        X = np.arange(len(new_prices)).reshape(-1, 1)
        y = np.array(new_prices)
        # Fit the scaler on first call (or use existing)
        if not hasattr(predictor.scaler, 'scale_'):
            X_scaled = predictor.scaler.fit_transform(X)
        else:
            X_scaled = predictor.scaler.transform(X)
        # Incremental update
        predictor.model.partial_fit(X_scaled, y)
        # Save updated model to disk (optional, can be done periodically)
        predictor._save()
        print(f"🤖 Updated model for {symbol} with {len(new_prices)} new points")

# ------------------------------
# PricePredictor class (same as before, but added partial_fit wrapper)
# ------------------------------
class PricePredictor:
    def __init__(self, symbol):
        self.symbol = symbol
        self.model_file = Path(f"models/price_predictor_{symbol}.pkl")
        self.scaler_file = Path(f"models/price_scaler_{symbol}.pkl")
        self.model = None
        self.scaler = MinMaxScaler()
        self._load_or_create()

    def _load_or_create(self):
        if self.model_file.exists() and self.scaler_file.exists():
            self.model = joblib.load(self.model_file)
            self.scaler = joblib.load(self.scaler_file)
            print(f"✅ Loaded existing model for {self.symbol}")
        else:
            self.model = SGDRegressor(loss='squared_error', penalty='l2',
                                      alpha=0.0001, max_iter=1000, tol=1e-3,
                                      random_state=42)
            print(f"⚠️ Created new model for {self.symbol}")

    def partial_fit(self, X, y):
        self.model.partial_fit(X, y)

    def _save(self):
        self.model_file.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, self.model_file)
        joblib.dump(self.scaler, self.scaler_file)

# ------------------------------
# PySpark streaming job
# ------------------------------
spark = SparkSession.builder \
    .appName("PSXStreamCleaner") \
    .getOrCreate()

# Schema of raw tick
schema = StructType([
    StructField("symbol", StringType(), True),
    StructField("price", DoubleType(), True),
    StructField("change", DoubleType(), True),
    StructField("change_pct", DoubleType(), True),
    StructField("timestamp", StringType(), True),
    StructField("source", StringType(), True)
])

# Read raw stream
raw_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "psx-raw-tick") \
    .option("startingOffsets", "latest") \
    .load()

# Parse JSON
parsed = raw_stream.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")
parsed = parsed.withColumn("timestamp", to_timestamp(col("timestamp")))

# Cleaning
window = Window.partitionBy("symbol", col("timestamp").cast("date"))
cleaned = parsed.withColumn("rn", row_number().over(window)) \
                .filter(col("rn") == 1) \
                .drop("rn")
cleaned = cleaned.filter((col("price") > 1) & (col("price") < 100000))
cleaned = cleaned.fillna({"change_pct": 0.0})
cleaned = cleaned.withColumn("processed_at", current_timestamp())

# Path for historical CSV
HISTORICAL_CSV = "data/historical_cleaned.csv"
Path(HISTORICAL_CSV).parent.mkdir(parents=True, exist_ok=True)

# Cache for model updater (shared across batches)
model_cache = ModelCache()

def process_batch(df, epoch_id):
    """Called for each micro‑batch: append to CSV and update models"""
    if df.count() == 0:
        return

    # Convert to Pandas
    pdf = df.toPandas()
    # Append to CSV
    file_exists = Path(HISTORICAL_CSV).exists()
    pdf.to_csv(HISTORICAL_CSV, mode='a', header=not file_exists, index=False)
    print(f"📝 Appended {len(pdf)} records to {HISTORICAL_CSV}")

    # Incrementally update models per symbol
    for symbol, group in pdf.groupby("symbol"):
        # Sort by timestamp within the batch
        group = group.sort_values("timestamp")
        prices = group["price"].tolist()
        if len(prices) >= 5:   # need at least a few points for partial_fit
            model_cache.update_model(symbol, prices)

# Write stream using foreachBatch
query = cleaned.writeStream \
    .foreachBatch(process_batch) \
    .outputMode("append") \
    .trigger(processingTime="10 seconds") \
    .start()

# Also send cleaned data to Kafka (optional)
cleaned_kafka = cleaned.selectExpr("to_json(struct(*)) AS value")
kafka_query = cleaned_kafka.writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("topic", "psx-cleaned-tick") \
    .option("checkpointLocation", "data/checkpoints/cleaner_kafka") \
    .outputMode("append") \
    .trigger(processingTime="5 seconds") \
    .start()

# Console for debugging
console_query = cleaned.writeStream \
    .outputMode("append") \
    .format("console") \
    .trigger(processingTime="10 seconds") \
    .start()

spark.streams.awaitAnyTermination()