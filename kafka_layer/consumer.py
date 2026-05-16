"""
Kafka Consumer with Agents Integration
"""
import json
from pathlib import Path
import sys
from kafka import KafkaConsumer
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC
from agents.data_agent import DataAgent
from agents.news_agent import NewsAgent
from agents.sentiment_agent import SentimentAgent
from agents.analysis_agent import AnalysisAgent
from agents.decision_agent import DecisionAgent


def process_tick_with_agents(tick):
    """Process incoming tick through all agents"""
    symbol = tick.get('symbol')
    price = tick.get('price')
    change_pct = tick.get('change_pct', 0)
    volume = tick.get('volume', 0)
    high = tick.get('high', price)
    low = tick.get('low', price)
    
    print(f"\n{'='*50}")
    print(f"📊 Processing: {symbol}")
    print(f"💰 Price: PKR {price} ({change_pct:+.2f}%)")
    print(f"📊 Volume: {volume:,} | High: {high} | Low: {low}")
    print(f"{'='*50}")
    
    # Initialize agents
    data_agent = DataAgent()
    news_agent = NewsAgent()
    sentiment_agent = SentimentAgent()
    analysis_agent = AnalysisAgent()
    decision_agent = DecisionAgent()
    
    # Create state
    state = {
        'query': symbol,
        'market_data': {
            'symbol': symbol,
            'price': price,
            'change': change_pct,
            'volume': volume,
            'high': high,
            'low': low
        },
        'messages': [],
        'news_data': []
    }
    
    # Run agents pipeline
    print("\n🔄 Running Agents Pipeline...")
    state = data_agent.process(state)
    state = news_agent.process(state)
    state = sentiment_agent.process(state)
    state = analysis_agent.process(state)
    state = decision_agent.process(state)
    
    # Display recommendation
    recommendations = state.get('recommendations', [])
    if recommendations:
        print(f"\n🎯 RECOMMENDATION: {recommendations[0]}")
    
    sentiment = state.get('sentiment_analysis', {})
    technical = state.get('technical_analysis', {})
    
    print(f"📈 Sentiment: {sentiment.get('overall_sentiment', 'N/A')}")
    print(f"📊 RSI: {technical.get('rsi', 'N/A')}")
    print(f"📉 Trend: {technical.get('trend', 'N/A')}")
    
    return state


def create_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest',  # Change from 'latest' to 'earliest'
        enable_auto_commit=True,
        group_id="psx-consumer-group",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        api_version_auto_timeout_ms=3000
    )

def run_consumer():
    consumer = create_consumer()
    print("\n" + "="*60)
    print("🎧 KAFKA CONSUMER WITH AGENTS")
    print("="*60)
    print(f"📡 Topic: {KAFKA_TOPIC}")
    print(f"🔗 Broker: {KAFKA_BOOTSTRAP_SERVERS}")
    print("="*60)
    print("Waiting for messages... (Press Ctrl+C to stop)\n")
    
    message_count = 0
    
    try:
        for message in consumer:
            tick = message.value
            process_tick_with_agents(tick)
            message_count += 1
            
            if message_count % 5 == 0:
                print(f"\n📈 Total messages processed: {message_count}\n")
                
    except KeyboardInterrupt:
        print(f"\n🛑 Consumer stopped. Total messages: {message_count}")
    finally:
        consumer.close()


def main():
    try:
        run_consumer()
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()