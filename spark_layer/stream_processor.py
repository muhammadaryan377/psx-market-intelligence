from pathlib import Path
import json
import os
import sys
import time
import traceback

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_HADOOP_HOME = PROJECT_ROOT / ".hadoop"


def configure_local_hadoop():
    if os.name != "nt":
        return

    existing_hadoop_home = os.environ.get("HADOOP_HOME")
    if existing_hadoop_home:
        existing_bin = Path(existing_hadoop_home) / "bin"
        if (existing_bin / "winutils.exe").exists() and (existing_bin / "hadoop.dll").exists():
            return

    winutils_path = LOCAL_HADOOP_HOME / "bin" / "winutils.exe"
    hadoop_dll_path = LOCAL_HADOOP_HOME / "bin" / "hadoop.dll"

    if not winutils_path.exists() or not hadoop_dll_path.exists():
        return

    os.environ["HADOOP_HOME"] = str(LOCAL_HADOOP_HOME)
    os.environ["HADOOP_CONF_DIR"] = str(LOCAL_HADOOP_HOME / "etc" / "hadoop")
    os.environ["PATH"] = f"{winutils_path.parent};{os.environ.get('PATH', '')}"


configure_local_hadoop()

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pyspark
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import (
    StructType,
    StringType,
    DoubleType,
    LongType,
    BooleanType,
)

from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC

from spark_layer.cleaning import clean_stock_batch
from spark_layer.trend_detection import add_trend_signals
from spark_layer.output_writer import write_processed_batch


SPARK_VERSION = pyspark.__version__
SCALA_BINARY_VERSION = "2.13" if SPARK_VERSION.startswith("4.") else "2.12"

KAFKA_CONNECTOR_PACKAGE = (
    f"org.apache.spark:spark-sql-kafka-0-10_{SCALA_BINARY_VERSION}:{SPARK_VERSION}"
)

MANUAL_KAFKA_BATCH_SIZE = int(os.getenv("MANUAL_KAFKA_BATCH_SIZE", "100"))
MANUAL_KAFKA_POLL_TIMEOUT_MS = int(os.getenv("MANUAL_KAFKA_POLL_TIMEOUT_MS", "1000"))
MANUAL_KAFKA_IDLE_SLEEP_SECONDS = float(os.getenv("MANUAL_KAFKA_IDLE_SLEEP_SECONDS", "0.5"))
MANUAL_KAFKA_GROUP_ID = os.getenv(
    "MANUAL_KAFKA_GROUP_ID",
    "psx-spark-stream-processor",
)
MANUAL_KAFKA_TEMP_DIR = PROJECT_ROOT / "data" / "tmp" / "manual_kafka_batches"

KAFKA_CONNECTOR_JAR_NAMES = [
    "com.google.code.findbugs_jsr305-3.0.0.jar",
    "org.apache.commons_commons-pool2-2.12.1.jar",
    "org.apache.hadoop_hadoop-client-api-3.4.2.jar",
    "org.apache.hadoop_hadoop-client-runtime-3.4.2.jar",
    "org.apache.kafka_kafka-clients-3.9.1.jar",
    f"org.apache.spark_spark-sql-kafka-0-10_{SCALA_BINARY_VERSION}-{SPARK_VERSION}.jar",
    f"org.apache.spark_spark-token-provider-kafka-0-10_{SCALA_BINARY_VERSION}-{SPARK_VERSION}.jar",
    "org.lz4_lz4-java-1.8.0.jar",
    "org.scala-lang.modules_scala-parallel-collections_2.13-1.2.0.jar",
    "org.slf4j_slf4j-api-2.0.17.jar",
    "org.xerial.snappy_snappy-java-1.1.10.8.jar",
]


# Kafka producer message schema
TICK_SCHEMA = (
    StructType()
    .add("symbol", StringType())
    .add("date", StringType())
    .add("open", DoubleType())
    .add("high", DoubleType())
    .add("low", DoubleType())
    .add("close", DoubleType())
    .add("volume", LongType())
    .add("is_anomaly", BooleanType())
    .add("source", StringType())
    .add("stream_type", StringType())
)


def get_cached_kafka_connector_classpath():
    ivy_jars_dir = Path.home() / ".ivy2.5.2" / "jars"
    jar_paths = [ivy_jars_dir / name for name in KAFKA_CONNECTOR_JAR_NAMES]

    if not all(path.exists() for path in jar_paths):
        return None

    separator = ";" if os.name == "nt" else ":"
    return separator.join(str(path) for path in jar_paths)


def create_spark_session():
    configure_local_hadoop()

    builder = (
        SparkSession.builder
        .appName("PSX Kafka Stream Processor")
        .config(
            "spark.hadoop.hadoop.security.group.mapping",
            "org.apache.hadoop.security.ShellBasedUnixGroupsMapping",
        )
        .config("spark.sql.shuffle.partitions", "4")
    )

    if should_use_manual_kafka_consumer():
        return builder.getOrCreate()

    connector_classpath = get_cached_kafka_connector_classpath()

    if connector_classpath:
        builder = (
            builder
            .config("spark.driver.extraClassPath", connector_classpath)
            .config("spark.executor.extraClassPath", connector_classpath)
        )
    else:
        builder = builder.config("spark.jars.packages", KAFKA_CONNECTOR_PACKAGE)

    spark = builder.getOrCreate()
    return spark


def read_psx_ticks(spark):
    return (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )


def parse_ticks(raw_df):
    return (
        raw_df
        .selectExpr("CAST(value AS STRING) as json_str")
        .select(from_json(col("json_str"), TICK_SCHEMA).alias("data"))
        .select("data.*")
        .where(col("symbol").isNotNull())
    )


def is_empty_dataframe(df):
    return df.limit(1).count() == 0


def process_batch(batch_df, batch_id):
    """
    This function runs on every micro-batch from Kafka.

    Flow:
    Kafka batch
        -> clean_stock_batch()
        -> add_trend_signals()
        -> write_processed_batch()
    """

    try:
        print("\n" + "=" * 80)
        print(f"PROCESSING BATCH: {batch_id}")
        print("=" * 80)

        if is_empty_dataframe(batch_df):
            print(f"Batch {batch_id}: empty batch skipped.")
            return

        incoming_count = batch_df.count()
        print(f"Incoming rows: {incoming_count}")

        print("\nIncoming schema:")
        batch_df.printSchema()

        print("\nIncoming sample:")
        batch_df.show(5, truncate=False)

        cleaned_df = clean_stock_batch(batch_df)
        cleaned_count = cleaned_df.count()

        print(f"\nCleaned rows: {cleaned_count}")

        if cleaned_count == 0:
            print(f"Batch {batch_id}: all rows removed after cleaning.")
            return

        trend_df = add_trend_signals(
            cleaned_df,
            moving_average_days=5,
            stable_threshold=0.005,
            volume_multiplier=2.0,
        )

        print("\nTrend output sample:")
        trend_df.show(10, truncate=False)

        write_processed_batch(
            batch_df=trend_df,
            batch_id=batch_id,
            output_dir="data/processed/psx_trends",
            output_format="json",
            show_console=True,
        )

        print(f"\nBatch {batch_id}: completed successfully.")

    except Exception as error:
        print("\n" + "!" * 80)
        print(f"ERROR INSIDE process_batch | batch_id={batch_id}")
        print(type(error).__name__)
        print(str(error))
        print("\nFull traceback:")
        traceback.print_exc()
        print("!" * 80 + "\n")
        raise error


def start_stream(parsed_df):
    checkpoint_path = str(
        PROJECT_ROOT / "data" / "checkpoints" / "psx_stream_processor"
    )

    return (
        parsed_df.writeStream
        .foreachBatch(process_batch)
        .outputMode("append")
        .option("checkpointLocation", checkpoint_path)
        .start()
    )


def should_use_manual_kafka_consumer():
    configured_mode = os.getenv("PSX_STREAM_MODE", "").strip().lower()

    if configured_mode in {"manual", "kafka-python", "safe"}:
        return True

    if configured_mode in {"spark", "structured", "structured-streaming"}:
        return False

    # Spark 4.1.1 has SPARK-55271: KafkaMicroBatchStream.metrics can crash
    # after a successful micro-batch while progress is being reported.
    return SPARK_VERSION == "4.1.1"


def decode_kafka_value(value):
    if value is None:
        return None

    try:
        return json.loads(value.decode("utf-8"))
    except Exception:
        return None


def create_manual_kafka_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset="latest",
        enable_auto_commit=False,
        group_id=MANUAL_KAFKA_GROUP_ID,
        value_deserializer=decode_kafka_value,
        consumer_timeout_ms=1000,
    )


def run_manual_kafka_micro_batches(spark):
    """
    Spark 4.1.1 workaround for SPARK-55271.

    Kafka is polled with kafka-python, then each small batch is converted into
    a Spark DataFrame and sent through the same process_batch function.
    """

    try:
        consumer = create_manual_kafka_consumer()
    except NoBrokersAvailable:
        print(
            "Error: Kafka broker is not available at "
            f"{KAFKA_BOOTSTRAP_SERVERS}. Start Kafka first."
        )
        return

    print("Using safe Kafka polling mode for Spark 4.1.1.")
    print("Set PSX_STREAM_MODE=structured to force Spark Kafka source.")
    print("Waiting for Kafka data...")
    print("=" * 60)

    batch_id = 0

    try:
        while True:
            polled_records = consumer.poll(
                timeout_ms=MANUAL_KAFKA_POLL_TIMEOUT_MS,
                max_records=MANUAL_KAFKA_BATCH_SIZE,
            )
            rows = []

            for records in polled_records.values():
                for record in records:
                    if isinstance(record.value, dict):
                        rows.append(record.value)

            if not rows:
                time.sleep(MANUAL_KAFKA_IDLE_SLEEP_SECONDS)
                continue

            batch_file = write_manual_batch_file(rows, batch_id)

            try:
                batch_df = spark.read.schema(TICK_SCHEMA).json(str(batch_file))
                process_batch(batch_df, batch_id)
                consumer.commit()
            finally:
                batch_file.unlink(missing_ok=True)

            batch_id += 1

    except KeyboardInterrupt:
        print("\nStream stopped by user.")

    finally:
        consumer.close()


def write_manual_batch_file(rows, batch_id):
    MANUAL_KAFKA_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    batch_file = MANUAL_KAFKA_TEMP_DIR / f"batch_{batch_id}.jsonl"

    with open(batch_file, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, default=str))
            f.write("\n")

    return batch_file


def main():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    print("=" * 60)
    print("PSX PySpark Stream Processor Started")
    print(f"Spark Version: {SPARK_VERSION}")
    print(f"Kafka Bootstrap Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Kafka Topic: {KAFKA_TOPIC}")
    print("=" * 60)

    if should_use_manual_kafka_consumer():
        run_manual_kafka_micro_batches(spark)
        return

    raw_df = read_psx_ticks(spark)
    parsed_df = parse_ticks(raw_df)

    query = start_stream(parsed_df)

    print("Streaming query started. Waiting for Kafka data...")
    print("Now run producer.py in another terminal.")
    print("=" * 60)

    try:
        query.awaitTermination()

    except KeyboardInterrupt:
        print("\nStream stopped by user.")
        query.stop()

    except Exception as error:
        print("\nSTREAM FAILED")
        print(type(error).__name__)
        print(str(error))

        if query.exception() is not None:
            print("\nSpark query exception:")
            print(query.exception())

        raise error


if __name__ == "__main__":
    main()
