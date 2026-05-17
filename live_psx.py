"""
Live PSX Dashboard - All Companies OR Search Specific
Auto-refresh every 10 seconds
Now with Kafka integration: sends each tick to Kafka topic 'psx-raw-tick'
"""
import psxdata as psx
import time
import os
import json
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# ------------------ Kafka Producer Setup ------------------
def create_producer():
    """Create and return a Kafka producer instance."""
    try:
        producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version_auto_timeout_ms=3000
        )
        print("✅ Kafka producer connected")
        return producer
    except Exception as e:
        print(f"⚠️ Kafka producer error: {e}")
        return None

# Global producer (will be initialized when needed)
_kafka_producer = None

def get_kafka_producer():
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = create_producer()
    return _kafka_producer

def send_to_kafka(data):
    """Send a tick dictionary to Kafka topic 'psx-raw-tick'."""
    producer = get_kafka_producer()
    if producer:
        try:
            producer.send('psx-raw-tick', data)
            # Do not flush every time; let the producer batch
        except Exception as e:
            print(f"Kafka send error: {e}")
# ---------------------------------------------------------

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_all_tickers():
    """Get ALL PSX companies dynamically"""
    try:
        all_tickers = psx.tickers()
        return all_tickers
    except:
        return ["UBL", "MCB", "SYS", "ENGRO", "LUCK", "HUBC", "HBL", "POL", "FCCL", "NRL", "PSO", "OGDC", "MARI", "EFERT"]

def get_live_data(symbol):
    """Get live data for any symbol"""
    try:
        quote = psx.quote(symbol)

        if quote is None:
            return None
        
        if hasattr(quote, 'iloc') and len(quote) > 0:
            quote = quote.iloc[0]
        
        if hasattr(quote, 'get'):
            price = quote.get('current_price') or quote.get('price') or quote.get('close')
            change = quote.get('change') or quote.get('net_change')
            change_pct = quote.get('change_percent') or quote.get('p_change')
        else:
            price = getattr(quote, 'current_price', getattr(quote, 'price', None))
            change = getattr(quote, 'change', None)
            change_pct = getattr(quote, 'change_percent', None)
        
        return {
            'symbol': symbol,
            'price': float(price) if price else None,
            'change': float(change) if change else None,
            'change_pct': float(change_pct) if change_pct else None,
            'found': price is not None
        }
    except Exception:
        return None

def show_all_companies(tickers):
    """Show all companies live data and send each tick to Kafka"""
    print("="*70)
    print(f"🚀 LIVE PSX MARKET - {datetime.now().strftime('%H:%M:%S')}")
    print("="*70)
    print(f"{'Symbol':<12} {'Price':<15} {'Change':<12} {'Change%':<10} Status")
    print("-"*70)
    
    gainers = 0
    losers = 0
    displayed = 0
    
    for symbol in tickers[:1000]:  # Limit to 1000 for performance
        data = get_live_data(symbol)
        
        if data and data.get('found'):
            price = data['price']
            change = data['change'] or 0
            change_pct = data['change_pct'] or 0
            
            # Send to Kafka (raw tick)
            tick = {
                'symbol': symbol,
                'price': price,
                'change': change,
                'change_pct': change_pct,
                'timestamp': datetime.now().isoformat(),
                'source': 'live_psx_dashboard'
            }
            send_to_kafka(tick)
            
            if change_pct > 0:
                status = "🟢 UP"
                gainers += 1
            elif change_pct < 0:
                status = "🔴 DOWN"
                losers += 1
            else:
                status = "🟡 SAME"
            
            print(f"{symbol:<12} PKR {price:<12.2f} {change:<+12.2f} {change_pct:<+10.2f}% {status}")
            displayed += 1
        else:
            print(f"{symbol:<12} {'N/A':<15} {'N/A':<12} {'N/A':<10} ⚪ N/A")
    
    print("-"*70)
    print(f"📊 Summary: 🟢 {gainers} Gainers | 🔴 {losers} Losers | Displayed: {displayed}")
    print(f"⏰ Updates every 10 seconds... (Press Ctrl+C to stop)")

def show_single_company(symbol):
    """Show single company with auto-refresh and send to Kafka"""
    print(f"\n🔍 Tracking {symbol.upper()} - Auto-refresh every 10 seconds")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            clear_screen()
            
            data = get_live_data(symbol.upper())
            
            print("="*50)
            print(f"🚀 {symbol.upper()} - LIVE DATA")
            print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
            print("="*50)
            
            if data and data.get('found'):
                price = data['price']
                change = data['change'] or 0
                change_pct = data['change_pct'] or 0
                
                # Send to Kafka
                tick = {
                    'symbol': symbol.upper(),
                    'price': price,
                    'change': change,
                    'change_pct': change_pct,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'live_psx_single'
                }
                send_to_kafka(tick)
                
                if change_pct > 0:
                    trend = "🟢 UP"
                elif change_pct < 0:
                    trend = "🔴 DOWN"
                else:
                    trend = "🟡 STABLE"
                
                print(f"💰 Price: PKR {price:.2f}")
                print(f"📈 Change: {change:+.2f} ({change_pct:+.2f}%)")
                print(f"📊 Trend: {trend}")
            else:
                print(f"❌ Symbol '{symbol}' not found on PSX")
                print("\n💡 Try: UBL, MCB, SYS, ENGRO, LUCK, HUBC, HBL")
            
            print("\n" + "="*50)
            print(f"⏰ Next update in 10 seconds...")
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n✅ Tracking stopped")

def main():
    """Main menu"""
    print("\n" + "="*50)
    print("🚀 LIVE PSX DASHBOARD (with Kafka producer)")
    print("="*50)
    print("\n1. 📊 Show ALL Companies (Live Data)")
    print("2. 🔍 Search Specific Company (Auto-refresh)")
    print("3. ❌ Exit")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == '1':
        print("\n🔄 Loading all companies...\n")
        tickers = get_all_tickers()
        print(f"✅ Found {len(tickers)} PSX companies\n")
        
        try:
            while True:
                clear_screen()
                show_all_companies(tickers)
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n\n✅ Dashboard stopped")
    
    elif choice == '2':
        symbol = input("\n📊 Enter PSX symbol (e.g., UBL, MCB, SYS): ").strip().upper()
        if symbol:
            show_single_company(symbol)
        else:
            print("❌ No symbol entered")
    
    else:
        print("👋 Goodbye!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exited")