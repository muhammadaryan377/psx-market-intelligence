"""
Kafka Topics Setup - Create, list, delete topics
"""
import sys
from pathlib import Path
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import NoBrokersAvailable, TopicAlreadyExistsError, UnknownTopicOrPartitionError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC

# Additional topics for different data streams
ADDITIONAL_TOPICS = {
    'psx-stock-prices': 3,      # 3 partitions for stock prices
    'psx-news-data': 2,          # 2 partitions for news
    'psx-sentiment': 2,          # 2 partitions for sentiment
    'psx-predictions': 1         # 1 partition for ML predictions
}


def create_admin_client():
    return KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)


def create_topic(topic_name: str, num_partitions: int = 1, replication_factor: int = 1):
    """Create Kafka topic"""
    admin = create_admin_client()
    topic = NewTopic(
        name=topic_name,
        num_partitions=num_partitions,
        replication_factor=replication_factor,
    )
    
    try:
        admin.create_topics(new_topics=[topic], validate_only=False)
        print(f"✅ Created Kafka topic: '{topic_name}' (partitions: {num_partitions})")
        return True
    except TopicAlreadyExistsError:
        print(f"⚠️ Topic already exists: '{topic_name}'")
        return False
    except Exception as e:
        print(f"❌ Error creating topic '{topic_name}': {e}")
        return False
    finally:
        admin.close()


def create_all_topics():
    """Create all required topics"""
    print("\n" + "="*60)
    print("📦 CREATING KAFKA TOPICS")
    print("="*60)
    
    # Create main topic
    create_topic(KAFKA_TOPIC, num_partitions=3)
    
    # Create additional topics
    for topic_name, partitions in ADDITIONAL_TOPICS.items():
        create_topic(topic_name, num_partitions=partitions)
    
    print("="*60 + "\n")


def list_topics():
    """List all available topics with details"""
    admin = create_admin_client()
    try:
        topics = admin.list_topics()
        print("\n" + "="*60)
        print("📋 AVAILABLE KAFKA TOPICS")
        print("="*60)
        
        for topic in sorted(topics):
            # Get topic details
            try:
                metadata = admin.describe_topics([topic])
                partitions = len(metadata[0].partitions) if metadata else '?'
                print(f"   📌 {topic} (partitions: {partitions})")
            except:
                print(f"   📌 {topic}")
        
        print("="*60 + f"\nTotal: {len(topics)} topics\n")
    except Exception as e:
        print(f"❌ Error listing topics: {e}")
    finally:
        admin.close()
    
    return topics


def delete_topic(topic_name: str):
    """Delete a topic (use carefully)"""
    admin = create_admin_client()
    try:
        admin.delete_topics(topics=[topic_name])
        print(f"🗑️ Deleted topic: '{topic_name}'")
        return True
    except UnknownTopicOrPartitionError:
        print(f"⚠️ Topic not found: '{topic_name}'")
        return False
    except Exception as e:
        print(f"❌ Error deleting topic '{topic_name}': {e}")
        return False
    finally:
        admin.close()


def delete_all_topics():
    """Delete all PSX-related topics"""
    print("\n" + "="*60)
    print("⚠️ DELETING ALL PSX TOPICS")
    print("="*60)
    
    topics_to_delete = [KAFKA_TOPIC] + list(ADDITIONAL_TOPICS.keys())
    
    for topic_name in topics_to_delete:
        delete_topic(topic_name)
    
    print("="*60 + "\n")


def get_topic_info(topic_name: str):
    """Get detailed information about a topic"""
    admin = create_admin_client()
    try:
        metadata = admin.describe_topics([topic_name])
        if metadata:
            topic = metadata[0]
            print(f"\n📊 Topic: {topic.topic}")
            print(f"   Partitions: {len(topic.partitions)}")
            for partition in topic.partitions:
                print(f"   - Partition {partition.partition}: leader={partition.leader}, replicas={len(partition.replicas)}")
    except Exception as e:
        print(f"❌ Error getting topic info: {e}")
    finally:
        admin.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Kafka Topics Management')
    parser.add_argument('--list', action='store_true', help='List all topics')
    parser.add_argument('--create', type=str, help='Create a specific topic')
    parser.add_argument('--create-all', action='store_true', help='Create all required topics')
    parser.add_argument('--delete', type=str, help='Delete a specific topic')
    parser.add_argument('--delete-all', action='store_true', help='Delete all PSX topics')
    parser.add_argument('--info', type=str, help='Get info about a topic')
    parser.add_argument('--partitions', type=int, default=3, help='Number of partitions (default: 3)')
    
    args = parser.parse_args()
    
    try:
        if args.list:
            list_topics()
        elif args.create:
            create_topic(args.create, num_partitions=args.partitions)
        elif args.create_all:
            create_all_topics()
        elif args.delete:
            delete_topic(args.delete)
        elif args.delete_all:
            delete_all_topics()
        elif args.info:
            get_topic_info(args.info)
        else:
            # Default: create main topic if not exists
            create_topic(KAFKA_TOPIC, num_partitions=3)
            
    except NoBrokersAvailable:
        print(f"\n❌ Kafka broker not available at {KAFKA_BOOTSTRAP_SERVERS}")
        print("💡 Make sure Kafka is running: docker-compose up -d kafka zookeeper")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())