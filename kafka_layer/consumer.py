"""
Kafka Consumer with Agents – reads cleaned ticks from psx-cleaned-tick
"""
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.data_agent import DataAgent
from agents.news_agent import NewsAgent
from agents.sentiment_agent import SentimentAgent
from agents.analysis_agent import AnalysisAgent
from agents.decision_agent import DecisionAgent
from kafka import KafkaConsumer
import json

# ... rest of your consumer logic
CLEANED_TOPIC = "psx-cleaned-tick"

def create_consumer():
    return KafkaConsumer(
        CLEANED_TOPIC,
        bootstrap_servers='localhost:9092',
        auto_offset_reset='latest',
        enable_auto_commit=True,
        group_id="psx-agent-consumer-group",
        value_deserializer=lambda m: json.loads(m.decode("utf-8"))
    )

def process_tick(tick):
    """Run the agent pipeline on a cleaned tick"""
    symbol = tick['symbol']
    price = tick['price']
    change_pct = tick['change_pct']

    state = {
        'query': symbol,
        'market_data': {
            'symbol': symbol,
            'price': price,
            'change': change_pct
        },
        'messages': [],
        'news_data': []
    }

    # Agents pipeline
    data_agent = DataAgent()
    news_agent = NewsAgent()
    sentiment_agent = SentimentAgent()
    analysis_agent = AnalysisAgent()
    decision_agent = DecisionAgent()

    state = data_agent.process(state)
    state = news_agent.process(state)
    state = sentiment_agent.process(state)
    state = analysis_agent.process(state)
    state = decision_agent.process(state)

    print(f"🎯 Recommendation for {symbol}: {state['recommendations'][0] if state['recommendations'] else 'HOLD'}")
    # Optionally send to frontend via WebSocket or store in DB
    return state

def run():
    consumer = create_consumer()
    print("🎧 Listening for cleaned ticks...")
    for msg in consumer:
        process_tick(msg.value)

if __name__ == "__main__":
    run()