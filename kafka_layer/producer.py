import json
import time
import random
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


def generate_live_tick(row):
    price_change = random.uniform(-2, 2)
    new_price = round(float(row["price"]) + price_change, 2)

    return {
        "symbol": row["symbol"],
        "price": new_price,
        "volume": int(row["volume"]) + random.randint(100, 1000),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "timestamp": datetime.now().isoformat()
    }


def create_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        api_version_auto_timeout_ms=3000
    )


def run_producer():
    df = pd.read_csv(PROJECT_ROOT / "data" / "sample_psx_data.csv")
    kafka_producer = create_producer()

    print(f"Sending data to Kafka topic: {KAFKA_TOPIC}")

    while True:
        row = df.sample(1).iloc[0]
        tick = generate_live_tick(row)

        kafka_producer.send(KAFKA_TOPIC, tick)
        kafka_producer.flush()

        print("Sent:", tick)
        time.sleep(2)


def main():
    try:
        run_producer()
    except NoBrokersAvailable:
        print(
            "Error: Kafka broker is not available at "
            f"{KAFKA_BOOTSTRAP_SERVERS}. Start Kafka or set "
            "KAFKA_BOOTSTRAP_SERVERS in .env."
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
