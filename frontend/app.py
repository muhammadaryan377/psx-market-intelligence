import sys
import os
import random
import time
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import feedparser
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import psxdata as psx
import csv   # add this line with other imports

sys.path.append(str(Path(__file__).parent.parent))

from agents.data_agent import DataAgent
from agents.news_agent import NewsAgent
from agents.sentiment_agent import SentimentAgent
from agents.analysis_agent import AnalysisAgent
from agents.decision_agent import DecisionAgent
from rag_layer import get_rag
from services.stock_service import stock_service
from services.market_status import market_status
from ml_models.trend_predictor import trend_predictor

app = Flask(__name__)
CORS(app)

# Initialize agents
data_agent = DataAgent()
news_agent = NewsAgent()
sentiment_agent = SentimentAgent()
analysis_agent = AnalysisAgent()
decision_agent = DecisionAgent()
rag = get_rag()

# Store for historical data
HISTORICAL_DATA_FILE = Path("data/historical_prices_clean.csv")
HISTORICAL_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# ========== KAFKA SECTION ==========
# Global variable for Kafka data
kafka_latest_data = {}

def init_kafka_consumer():
    """Initialize Kafka consumer in background"""
    import threading
    from kafka import KafkaConsumer
    
    def consume():
        global kafka_latest_data
        try:
            consumer = KafkaConsumer(
                'psx-stock-prices',
                bootstrap_servers='localhost:9092',
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                api_version_auto_timeout_ms=3000
            )
            for message in consumer:
                tick = message.value
                kafka_latest_data[tick['symbol']] = tick
                print(f"Kafka received: {tick['symbol']} @ {tick['price']}")
        except Exception as e:
            print(f"Kafka consumer error: {e}")
    
    thread = threading.Thread(target=consume, daemon=True)
    thread.start()
    print("✅ Kafka consumer thread started")

# Call this when Kafka is available
# init_kafka_consumer()

def save_historical_data(data):
    """Save historical data to CSV file"""
    rows = []
    for symbol, entries in data.items():
        for entry in entries:
            rows.append({
                'symbol': symbol,
                'price': entry['price'],
                'timestamp': entry['timestamp']
            })
    
    with open(HISTORICAL_DATA_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['symbol', 'price', 'timestamp'])
        writer.writeheader()
        writer.writerows(rows)


def save_historical_data(data):
    rows = []
    for symbol, entries in data.items():
        for entry in entries:
            rows.append({
                'symbol': symbol,
                'price': entry['price'],
                'timestamp': entry['timestamp']
            })
    with open(HISTORICAL_DATA_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['symbol', 'price', 'timestamp'])
        writer.writeheader()
        writer.writerows(rows)


def update_model_incrementally(symbol, new_price):
    """Update per‑symbol price predictor incrementally (partial_fit)"""
    from ml_models.price_predictor import PricePredictor
    import numpy as np
    
    predictor = PricePredictor(symbol=symbol)
    
    # If model doesn't exist yet, train on all historical data
    if not predictor.model_file.exists():
        if symbol in historical_cache and len(historical_cache[symbol]) >= 5:
            all_prices = [p['price'] for p in historical_cache[symbol]]
            predictor.train(all_prices)
        return
    
    # Model exists – do incremental update with new price point
    # Use the current length as the next index
    current_len = len(historical_cache.get(symbol, []))
    if current_len == 0:
        return
    X_new = np.array([[current_len - 1]]).astype(np.float64)
    y_new = np.array([new_price]).astype(np.float64)
    
    # partial_fit expects scaler already fitted
    if hasattr(predictor.scaler, 'scale_'):
        predictor.partial_fit(X_new, y_new)

# ---------- Historical data load/save functions ----------
def load_historical_data():
    """Load historical data from CSV file into dict format"""
    data = {}
    if HISTORICAL_DATA_FILE.exists():
        with open(HISTORICAL_DATA_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row['symbol']
                entry = {'price': float(row['price']), 'timestamp': row['timestamp']}
                if symbol not in data:
                    data[symbol] = []
                data[symbol].append(entry)
    return data

def save_historical_data(data):
    """Save historical data to CSV file"""
    rows = []
    for symbol, entries in data.items():
        for entry in entries:
            rows.append({
                'symbol': symbol,
                'price': entry['price'],
                'timestamp': entry['timestamp']
            })
    with open(HISTORICAL_DATA_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['symbol', 'price', 'timestamp'])
        writer.writeheader()
        writer.writerows(rows)

# ---------- Initialize historical cache ----------
historical_cache = load_historical_data()

def get_historical_prices(symbol):
    """Return historical prices for ML prediction.
    Only generates mock data if absolutely no data exists (cache + CSV empty).
    Mock data is deterministic (same for same symbol each time).
    """
    symbol = symbol.upper()
    
    # 1. Try cache first
    if symbol in historical_cache and historical_cache[symbol]:
        prices = [item['price'] for item in historical_cache[symbol][-30:]]
        if len(prices) >= 5:          # allow at least 5 points for training
            return prices
    
    # 2. Fallback: read from the clean CSV file
    csv_path = Path("data/historical_prices_clean.csv")
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            # Ensure timestamp column exists and sort
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
            # Filter for this symbol
            symbol_df = df[df['symbol'] == symbol]
            if not symbol_df.empty and 'price' in symbol_df.columns:
                prices = symbol_df['price'].tail(30).tolist()
                if len(prices) >= 5:
                    return prices
        except Exception as e:
            print(f"Error reading historical CSV: {e}")
    
    # 3. Absolutely no data – generate deterministic mock (same every time)
    # Use symbol hash as seed so same symbol → same mock sequence
    import random
    random.seed(hash(symbol) % 10000)
    base_price = 100 + (hash(symbol) % 400)   # fixed base per symbol
    prices = []
    price = base_price
    for _ in range(30):
        change_pct = random.uniform(-0.02, 0.02)
        price = price * (1 + change_pct)
        prices.append(round(price, 2))
    return prices

def get_live_or_stored_price(symbol):
    symbol = symbol.upper()
    status = market_status.get_status()
    
    # 1. Market open? Try live data
    if status['status'] == 'open':
        try:
            quote = psx.quote(symbol)
            if quote is not None:
                if hasattr(quote, 'iloc') and len(quote) > 0:
                    quote = quote.iloc[0]
                price = quote.get('current_price') or quote.get('price')
                if price:
                    data = {
                        'price': float(price),
                        'change': float(quote.get('change', 0)),
                        'change_pct': float(quote.get('change_percent', 0)),
                        'source': 'live',
                        'timestamp': datetime.now().isoformat()
                    }
                    # Avoid duplicate if same price
                    last = historical_cache.get(symbol, [])
                    if not last or last[-1]['price'] != data['price']:
                        historical_cache.setdefault(symbol, []).append({
                            'price': data['price'],
                            'timestamp': data['timestamp']
                        })
                        historical_cache[symbol] = historical_cache[symbol][-100:]
                        save_historical_data(historical_cache)
                        # Incremental ML update (define later)
                        update_model_incrementally(symbol, data['price'])
                    return data, status
        except Exception as e:
            print(f"Live error: {e}")
    
    # 2. Market closed or live failed → only stored data
    if symbol in historical_cache and historical_cache[symbol]:
        last = historical_cache[symbol][-1]
        return {
            'price': float(last['price']),
            'change': 0,
            'change_pct': 0,
            'source': 'stored',
            'timestamp': last['timestamp'],
            'message': "Market closed – last stored price"
        }, status
    
    # 3. No data at all → error (no mock!)
    return {
        'error': f'No historical data for {symbol}',
        'source': 'none'
    }, status

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/kafka')
def index_kafka():
    return render_template('index-kafka.html')

@app.route('/api/market_status')
def get_market_status():
    return jsonify(market_status.get_status())

@app.route('/api/stock/<symbol>')
def get_stock(symbol):
    symbol = symbol.upper()
    live_data, status = get_live_or_stored_price(symbol)
    
    state = {
        'query': symbol,
        'market_data': {
            'symbol': symbol, 
            'price': live_data['price'], 
            'change': live_data['change_pct']
        },
        'messages': [],
        'news_data': []
    }
    
    try:
        state = data_agent.process(state)
        state = news_agent.process(state)
        state = sentiment_agent.process(state)
        state = analysis_agent.process(state)
        state = decision_agent.process(state)
    except Exception as e:
        print(f"Agent error: {e}")
    
    change = live_data['change_pct']
    
    if change > 2:
        rec = 'STRONG BUY'
        conf = 85
    elif change > 0:
        rec = 'BUY'
        conf = 70
    elif change < -2:
        rec = 'STRONG SELL'
        conf = 85
    elif change < 0:
        rec = 'SELL'
        conf = 65
    else:
        rec = 'HOLD'
        conf = 50
    
    if change > 1:
        sent = 'bullish'
    elif change < -1:
        sent = 'bearish'
    else:
        sent = 'stable'
    
    rsi = 50 + (change * 2)
    rsi = max(30, min(70, rsi))
    
    if change > 1:
        price_trend = 'uptrend'
    elif change < -1:
        price_trend = 'downtrend'
    else:
        price_trend = 'sideways'
    
    ml_trend = "neutral"
    ml_trend_conf = 50
    try:
        historical_prices = get_historical_prices(symbol)
        ml_trend, base_conf = trend_predictor.predict_trend(historical_prices)
        
        if ml_trend == 'up':
            if change > 2:
                ml_trend_conf = 85
            elif change > 1:
                ml_trend_conf = 75
            elif change > 0.5:
                ml_trend_conf = 65
            else:
                ml_trend_conf = 55
        elif ml_trend == 'down':
            if change < -2:
                ml_trend_conf = 85
            elif change < -1:
                ml_trend_conf = 75
            elif change < -0.5:
                ml_trend_conf = 65
            else:
                ml_trend_conf = 55
        else:
            if abs(change) < 0.5:
                ml_trend_conf = 50
            elif change > 0:
                ml_trend_conf = 55
                ml_trend = 'up'
            elif change < 0:
                ml_trend_conf = 55
                ml_trend = 'down'
        
        ml_trend_conf = int((ml_trend_conf + base_conf) / 2)
        ml_trend_conf = max(50, min(85, ml_trend_conf))
        
    except Exception as e:
        print(f"Trend predictor error: {e}")
    
    try:
        rag_context = rag.get_context(symbol) if rag else []
    except:
        rag_context = []
    
    return jsonify({
        'symbol': symbol,
        'price': round(float(live_data['price']), 2),
        'change': round(float(change), 2),
        'recommendation': rec,
        'sentiment': sent,
        'rsi': int(round(rsi)),
        'trend': price_trend,
        'confidence': int(conf),
        'market_status': status['status'],
        'market_message': status['message'],
        'data_source': live_data['source'],
        'news': state.get('news_data', [])[:3],
        'rag_context': rag_context,
        'ml_trend': {
            'trend': ml_trend,
            'confidence': ml_trend_conf
        }
    })

@app.route('/api/all_stocks')
def all_stocks():
    tickers = stock_service.get_all_tickers()
    stocks = []
    for symbol in tickers[:50]:
        data, _ = get_live_or_stored_price(symbol)
        # Only add if data contains price and change_pct (i.e., not an error)
        if 'price' in data and 'change_pct' in data:
            stocks.append({
                'symbol': symbol,
                'price': round(float(data['price']), 2),
                'change': round(float(data['change_pct']), 2)
            })
    return jsonify(stocks)

@app.route('/api/gainers')
def gainers():
    tickers = stock_service.get_all_tickers()
    gainers_list = []
    for symbol in tickers[:100]:
        data, _ = get_live_or_stored_price(symbol)
        if 'change_pct' in data and data['change_pct'] > 0:
            gainers_list.append({
                'symbol': symbol,
                'price': round(float(data['price']), 2),
                'change': round(float(data['change_pct']), 2)
            })
    gainers_list.sort(key=lambda x: x['change'], reverse=True)
    return jsonify(gainers_list[:15])


@app.route('/api/losers')
def losers():
    tickers = stock_service.get_all_tickers()
    losers_list = []
    for symbol in tickers[:100]:
        data, _ = get_live_or_stored_price(symbol)
        if 'change_pct' in data and data['change_pct'] < 0:
            losers_list.append({
                'symbol': symbol,
                'price': round(float(data['price']), 2),
                'change': round(float(data['change_pct']), 2)
            })
    losers_list.sort(key=lambda x: x['change'])
    return jsonify(losers_list[:15])


@app.route('/api/news')
def news():
    news_list = []
    feeds = [
        "https://www.dawn.com/feeds/business",
        "https://tribune.com.pk/feed/business"
    ]
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = entry.get('title', '')
                sentiment = "neutral"
                if any(w in title.lower() for w in ['profit', 'gain', 'growth', 'positive']):
                    sentiment = "positive"
                elif any(w in title.lower() for w in ['loss', 'decline', 'negative']):
                    sentiment = "negative"
                
                news_list.append({
                    'title': title[:100],
                    'summary': entry.get('summary', '')[:200],
                    'source': feed_url.split('/')[2],
                    'sentiment': sentiment
                })
        except:
            pass
    
    return jsonify(news_list[:10])

@app.route('/api/search')
def search():
    query = request.args.get('q', '').upper()
    tickers = stock_service.get_all_tickers()
    results = [s for s in tickers if query in s][:15]
    return jsonify(results)

@app.route('/api/suggest/<prefix>')
def suggest(prefix):
    prefix = prefix.upper()
    tickers = stock_service.get_all_tickers()
    suggestions = [s for s in tickers if s.startswith(prefix)][:10]
    return jsonify(suggestions)

@app.route('/api/ml_predict/<symbol>')
def ml_predict(symbol):
    symbol = symbol.upper().strip()

    # ----- Validation -----
    if not symbol.isalpha():
        return jsonify({'error': f'❌ Invalid symbol: "{symbol}". Use only letters A-Z.'})

    if len(symbol) < 2 or len(symbol) > 10:
        return jsonify({'error': f'❌ Invalid symbol: "{symbol}". Length 2-10 characters.'})

    valid_symbols = stock_service.get_all_tickers()
    if symbol not in valid_symbols:
        similar = [s for s in valid_symbols if symbol in s][:5]
        if similar:
            return jsonify({'error': f'❌ Symbol "{symbol}" not found. Did you mean: {", ".join(similar)}?'})
        else:
            return jsonify({'error': f'❌ Symbol "{symbol}" not found on PSX.'})

    # ----- Current price -----
    live_data, status = get_live_or_stored_price(symbol)
    if not live_data or live_data.get('price') == 'N/A' or 'error' in live_data:
        return jsonify({'error': f'❌ Price data not available for {symbol}.'})

    current_price = float(live_data['price'])

    # ----- Historical prices (only from cache, no random generation) -----
    historical_prices = get_historical_prices(symbol)   # returns [] if not enough
    if not historical_prices or len(historical_prices) < 5:
        # Not enough historical data → use deterministic mock prediction
        import random
        random.seed(hash(symbol) % 10000)
        mock_change = random.uniform(-5, 5)
        predicted_price = current_price * (1 + mock_change / 100)
        expected_return = mock_change
        action = "BUY" if expected_return > 1 else "SELL" if expected_return < -1 else "HOLD"
        confidence = int(min(70, 50 + abs(expected_return) * 3))
        ml_trend = "neutral"
        ml_trend_conf = 50
        return jsonify({
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'predicted_price': round(predicted_price, 2),
            'expected_return': round(expected_return, 1),
            'action': action,
            'confidence': confidence,
            'ml_trend': ml_trend,
            'ml_trend_confidence': ml_trend_conf,
            'note': 'Mock prediction (insufficient historical data)'
        })

    recent_prices = [float(p) for p in historical_prices[-20:]]

    # ----- ML prediction using per‑symbol model (no retraining on each call) -----
    try:
        from ml_models.price_predictor import PricePredictor
        from ml_models.trend_predictor import trend_predictor

        # Use a model dedicated to this symbol
        predictor = PricePredictor(symbol=symbol)

        # Train only once: if the model file does not exist, train on all available history
        if not predictor.model_file.exists():
            all_prices = [p['price'] for p in historical_cache.get(symbol, [])]
            if len(all_prices) >= 5:
                predictor.train(all_prices)
                print(f"✅ Trained new model for {symbol} on {len(all_prices)} points")
            else:
                # Still not enough? Should not happen because we already checked historical_prices
                return jsonify({'error': 'Still not enough data to train model.'})

        # Predict next price
        next_price = predictor.predict_next_price(recent_prices)
        if next_price is None or next_price <= 0:
            return jsonify({'error': 'Prediction failed – model not ready.'})

        next_price = float(next_price)
        expected_return = ((next_price - current_price) / current_price) * 100

        if expected_return > 1:
            action = "BUY"
        elif expected_return < -1:
            action = "SELL"
        else:
            action = "HOLD"

        confidence = int(min(85, 50 + abs(expected_return) * 5))

        # Trend prediction (optional, uses same historical_prices)
        ml_trend, ml_trend_conf = trend_predictor.predict_trend(historical_prices)
        ml_trend_conf = int(ml_trend_conf)

        return jsonify({
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'predicted_price': round(next_price, 2),
            'expected_return': round(expected_return, 1),
            'action': action,
            'confidence': confidence,
            'ml_trend': ml_trend,
            'ml_trend_confidence': ml_trend_conf
        })

    except Exception as e:
        print(f"ML Prediction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Prediction error: {str(e)}'})
        
@app.route('/api/kafka/stock/<symbol>')
def get_kafka_stock(symbol):
    symbol = symbol.upper()
    data = kafka_latest_data.get(symbol)
    
    if not data:
        return jsonify({'error': 'No data from Kafka yet', 'symbol': symbol})
    
    price = data.get('price')
    change_pct = data.get('change_pct', 0)
    
    if change_pct > 2:
        rec = 'STRONG BUY'
        conf = 85
    elif change_pct > 0:
        rec = 'BUY'
        conf = 70
    elif change_pct < -2:
        rec = 'STRONG SELL'
        conf = 85
    elif change_pct < 0:
        rec = 'SELL'
        conf = 65
    else:
        rec = 'HOLD'
        conf = 50
    
    if change_pct > 1:
        sent = 'bullish'
    elif change_pct < -1:
        sent = 'bearish'
    else:
        sent = 'stable'
    
    rsi = 50 + (change_pct * 2)
    rsi = max(30, min(70, rsi))
    
    return jsonify({
        'symbol': symbol,
        'price': price,
        'change': round(change_pct, 2),
        'recommendation': rec,
        'sentiment': sent,
        'rsi': round(rsi),
        'confidence': conf,
        'source': 'kafka'
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 PSX Market Intelligence Server")
    print("="*50)
    print("📍 http://localhost:5000")
    print("="*50)
    app.run(debug=True, host='0.0.0.0', port=5000)