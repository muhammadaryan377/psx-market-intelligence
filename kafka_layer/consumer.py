import json
from pathlib import Path
import sys
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC


def create_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="psx-consumer-group",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        api_version_auto_timeout_ms=3000
    )


def run_consumer():
    consumer = create_consumer()

    print(f"Listening to Kafka topic: {KAFKA_TOPIC}")

    for message in consumer:
        print("Received:", message.value)


def main():
    try:
        run_consumer()
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
