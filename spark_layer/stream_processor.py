from pathlib import Path
import os
import sys

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

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import DoubleType, LongType, StringType, StructType

from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC


SPARK_VERSION = pyspark.__version__
SCALA_BINARY_VERSION = "" \
"2.13" if SPARK_VERSION.startswith("4.") else "2.12"
KAFKA_CONNECTOR_PACKAGE = (
    f"org.apache.spark:spark-sql-kafka-0-10_{SCALA_BINARY_VERSION}:{SPARK_VERSION}"
)
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

TICK_SCHEMA = StructType() \
    .add("symbol", StringType()) \
    .add("price", DoubleType()) \
    .add("volume", LongType()) \
    .add("high", DoubleType()) \
    .add("low", DoubleType()) \
    .add("timestamp", StringType())


def create_spark_session():
    configure_local_hadoop()

    builder = SparkSession.builder \
        .appName("PSX Kafka Stream Processor") \
        .config(
            "spark.hadoop.hadoop.security.group.mapping",
            "org.apache.hadoop.security.ShellBasedUnixGroupsMapping",
        )
    connector_classpath = get_cached_kafka_connector_classpath()

    if connector_classpath:
        builder = builder \
            .config("spark.driver.extraClassPath", connector_classpath) \
            .config("spark.executor.extraClassPath", connector_classpath)
    else:
        builder = builder.config("spark.jars.packages", KAFKA_CONNECTOR_PACKAGE)

    return builder.getOrCreate()


def get_cached_kafka_connector_classpath():
    ivy_jars_dir = Path.home() / ".ivy2.5.2" / "jars"
    jar_paths = [ivy_jars_dir / name for name in KAFKA_CONNECTOR_JAR_NAMES]

    if not all(path.exists() for path in jar_paths):
        return None

    return ";".join(str(path) for path in jar_paths)


def read_psx_ticks(spark):
    return spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()


def parse_ticks(raw_df):
    return raw_df.selectExpr("CAST(value AS STRING) as json_str") \
        .select(from_json(col("json_str"), TICK_SCHEMA).alias("data")) \
        .select("data.*") \
        .where(col("symbol").isNotNull())


def write_to_console(parsed_df):
    return parsed_df.writeStream \
       .format("console") \
       .outputMode("append") \
       .option("truncate", "false") \
       .option("checkpointLocation", "C:/tmp/checkpoint") \
       .start()


def main():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    print(f"Reading Kafka topic '{KAFKA_TOPIC}' from {KAFKA_BOOTSTRAP_SERVERS}")

    raw_df = read_psx_ticks(spark)
    parsed_df = parse_ticks(raw_df)
    query = write_to_console(parsed_df)
    query.awaitTermination()


if __name__ == "__main__":
    main()

