from pathlib import Path
import sys

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import NoBrokersAvailable, TopicAlreadyExistsError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.app_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC


def create_or_verify_topic(topic_name: str = KAFKA_TOPIC) -> bool:
    try:
        admin = KafkaAdminClient(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            client_id="psx-topic-setup",
            api_version_auto_timeout_ms=3000,
        )
    except NoBrokersAvailable:
        print(
            "Error: Kafka broker is not available at "
            f"{KAFKA_BOOTSTRAP_SERVERS}. Start it with: docker compose up -d"
        )
        return False

    try:
        existing_topics = set(admin.list_topics())
        if topic_name in existing_topics:
            print(f"Kafka topic already exists: {topic_name}")
            return True

        topic = NewTopic(name=topic_name, num_partitions=1, replication_factor=1)
        admin.create_topics(new_topics=[topic], validate_only=False)
        print(f"Kafka topic created: {topic_name}")
        return True
    except TopicAlreadyExistsError:
        print(f"Kafka topic already exists: {topic_name}")
        return True
    finally:
        admin.close()


def main() -> int:
    print(f"Kafka Bootstrap Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Kafka Topic: {KAFKA_TOPIC}")
    return 0 if create_or_verify_topic() else 1


if __name__ == "__main__":
    raise SystemExit(main())
