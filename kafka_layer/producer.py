import json
import random
import time
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC


CSV_PATH = PROJECT_ROOT / "data" / "processed" / "psx_cleaned_data.csv"
SEND_DELAY_SECONDS = 0.5


def generate_live_tick(row):
    """
    Build a simulated live market tick from a simple price row.

    Kept for tests and backward compatibility with the earlier live-tick producer.
    The streaming producer below uses row_to_kafka_message for OHLC records.
    """

    price_change = random.uniform(-2, 2)
    new_price = round(float(row["price"]) + price_change, 2)

    return {
        "symbol": str(row["symbol"]),
        "price": new_price,
        "volume": int(row["volume"]) + random.randint(100, 1000),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "timestamp": datetime.now().isoformat()
    }


def convert_bool(value):
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in ["true", "1", "yes"]


def create_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value, default=str).encode("utf-8"),
        key_serializer=lambda key: str(key).encode("utf-8"),
        api_version_auto_timeout_ms=3000
    )


def load_cleaned_data():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Cleaned CSV file not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)

    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    required_columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "is_anomaly",
        "symbol",
        "source",
        "stream_type"
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValueError(f"Missing required columns in CSV: {missing_columns}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "symbol", "open", "high", "low", "close", "volume"])

    # Important: chronological order for moving average
    df = df.sort_values(by=["symbol", "date"])

    return df


def row_to_kafka_message(row):
    return {
        "symbol": str(row["symbol"]),
        "date": str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "volume": int(row["volume"]),
        "is_anomaly": convert_bool(row["is_anomaly"]),
        "source": str(row["source"]),
        "stream_type": str(row["stream_type"])
    }


def run_producer():
    df = load_cleaned_data()
    kafka_producer = create_producer()

    print("=" * 60)
    print("PSX Kafka Producer Started")
    print(f"Kafka Bootstrap Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Kafka Topic: {KAFKA_TOPIC}")
    print(f"CSV File: {CSV_PATH}")
    print(f"Total Rows: {len(df)}")
    print("=" * 60)

    for index, row in df.iterrows():
        message = row_to_kafka_message(row)

        kafka_producer.send(
            KAFKA_TOPIC,
            key=message["symbol"],
            value=message
        )

        print(
            f"Sent {index + 1}/{len(df)} | "
            f"{message['symbol']} | "
            f"{message['date']} | "
            f"Close={message['close']} | "
            f"Volume={message['volume']} | "
            f"Anomaly={message['is_anomaly']}"
        )

        time.sleep(SEND_DELAY_SECONDS)

    kafka_producer.flush()
    kafka_producer.close()

    print("All cleaned PSX data sent to Kafka successfully.")


def main():
    try:
        run_producer()

    except NoBrokersAvailable:
        print(
            "Error: Kafka broker is not available at "
            f"{KAFKA_BOOTSTRAP_SERVERS}. Start Kafka first."
        )
        return 1

    except Exception as error:
        print(f"Producer error: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
