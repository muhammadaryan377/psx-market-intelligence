import sys
from pathlib import Path

from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import NoBrokersAvailable, TopicAlreadyExistsError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC


def create_admin_client():
    return KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)


def create_topic(topic_name: str, num_partitions: int = 1, replication_factor: int = 1):
    admin = create_admin_client()
    topic = NewTopic(
        name=topic_name,
        num_partitions=num_partitions,
        replication_factor=replication_factor,
    )

    try:
        admin.create_topics(new_topics=[topic], validate_only=False)
        print(f"Created Kafka topic: {topic_name}")
    except TopicAlreadyExistsError:
        print(f"Kafka topic already exists: {topic_name}")
    finally:
        admin.close()


def main():
    try:
        create_topic(KAFKA_TOPIC)
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
