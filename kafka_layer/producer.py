"""
Kafka Producer - Sends live PSX data to Kafka topic
"""
import json
import time
import random
from datetime import datetime
from pathlib import Path
import sys
import psxdata as psx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable


def get_live_psx_tick(symbol):
    """Fetch live tick from PSX API"""
    try:
        quote = psx.quote(symbol)
        if quote is not None:
            if hasattr(quote, 'iloc') and len(quote) > 0:
                quote = quote.iloc[0]
            
            price = quote.get('current_price') or quote.get('price')
            change = quote.get('change') or quote.get('net_change')
            change_pct = quote.get('change_percent') or quote.get('p_change')
            volume = quote.get('volume') or quote.get('total_volume')
            high = quote.get('high') or quote.get('day_high')
            low = quote.get('low') or quote.get('day_low')
            
            if price:
                return {
                    "symbol": symbol,
                    "price": float(price),
                    "change": float(change) if change else 0,
                    "change_pct": float(change_pct) if change_pct else 0,
                    "volume": int(volume) if volume else 0,
                    "high": float(high) if high else float(price),
                    "low": float(low) if low else float(price),
                    "timestamp": datetime.now().isoformat(),
                    "source": "live_psx"
                }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    
    return None


def generate_mock_tick(symbol, base_price=100):
    """Generate mock tick for testing"""
    price_change = random.uniform(-2, 2)
    new_price = round(base_price + price_change, 2)
    
    return {
        "symbol": symbol,
        "price": new_price,
        "change": round(price_change, 2),
        "change_pct": round((price_change / base_price) * 100, 2),
        "volume": random.randint(1000, 100000),
        "high": round(new_price + random.uniform(0, 5), 2),
        "low": round(new_price - random.uniform(0, 5), 2),
        "timestamp": datetime.now().isoformat(),
        "source": "mock"
    }


def create_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        api_version_auto_timeout_ms=3000,
        retries=3
    )


def run_producer(symbols=None, use_live=True, interval=5):
    """Run producer to send stock ticks"""
    if symbols is None:
        symbols = ['UBL', 'MCB', 'SYS', 'ENGRO', 'LUCK', 'HUBC', 'HBL', 'POL', 'FCCL', 'NRL']
    
    kafka_producer = create_producer()
    print("\n" + "="*60)
    print("📤 KAFKA PRODUCER STARTED")
    print("="*60)
    print(f"📡 Topic: {KAFKA_TOPIC}")
    print(f"🔗 Broker: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"📊 Symbols: {symbols}")
    print(f"🔴 Live mode: {use_live}")
    print(f"⏱️ Interval: {interval} seconds")
    print("="*60 + "\n")
    
    tick_count = 0
    
    try:
        while True:
            for symbol in symbols:
                if use_live:
                    tick = get_live_psx_tick(symbol)
                    if tick is None:
                        tick = generate_mock_tick(symbol)
                else:
                    tick = generate_mock_tick(symbol)
                
                kafka_producer.send(KAFKA_TOPIC, tick)
                print(f"📨 [{tick_count+1}] Sent: {tick['symbol']} @ PKR {tick['price']} ({tick.get('change_pct', 0):+.2f}%) | Source: {tick.get('source', 'unknown')}")
                tick_count += 1
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n🛑 Producer stopped by user")
        print(f"📊 Total ticks sent: {tick_count}")
    except NoBrokersAvailable:
        print(f"\n❌ Kafka broker not available at {KAFKA_BOOTSTRAP_SERVERS}")
        print("💡 Make sure Kafka is running: docker-compose up -d kafka zookeeper")
    finally:
        kafka_producer.close()
        print("🔌 Producer connection closed")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Kafka Producer for PSX Data')
    parser.add_argument('--mock', action='store_true', help='Use mock data instead of live PSX')
    parser.add_argument('--symbols', nargs='+', help='Symbols to track', 
                        default=['UBL', 'MCB', 'SYS', 'ENGRO', 'LUCK'])
    parser.add_argument('--interval', type=int, default=5, help='Interval between batches (seconds)')
    
    args = parser.parse_args()
    
    run_producer(symbols=args.symbols, use_live=not args.mock, interval=args.interval)


if __name__ == "__main__":
    main()