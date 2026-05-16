from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sys
from pathlib import Path
import psxdata as psx
import feedparser
from datetime import datetime
import time
import json
import os
import random

sys.path.append(str(Path(__file__).parent.parent))

from agents.data_agent import DataAgent
from agents.news_agent import NewsAgent
from agents.sentiment_agent import SentimentAgent
from agents.analysis_agent import AnalysisAgent
from agents.decision_agent import DecisionAgent
from rag_layer import get_rag
from services.stock_service import stock_service
from services.market_status import market_status

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
HISTORICAL_DATA_FILE = Path("data/historical_prices.json")
HISTORICAL_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_historical_data():
    """Load stored historical data"""
    if HISTORICAL_DATA_FILE.exists():
        with open(HISTORICAL_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_historical_data(data):
    """Save historical data"""
    with open(HISTORICAL_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

historical_cache = load_historical_data()

def get_live_or_stored_price(symbol):
    """Get live price if market open, else get stored data"""
    symbol = symbol.upper()
    status = market_status.get_status()
    
    # Try to get live data
    try:
        quote = psx.quote(symbol)
        if quote is not None:
            if hasattr(quote, 'iloc') and len(quote) > 0:
                quote = quote.iloc[0]
            
            price = quote.get('current_price') or quote.get('price')
            change = quote.get('change') or quote.get('net_change')
            change_pct = quote.get('change_percent') or quote.get('p_change')
            
            if price:
                data = {
                    'price': float(price),
                    'change': float(change) if change else 0,
                    'change_pct': float(change_pct) if change_pct else 0,
                    'source': 'live',
                    'timestamp': datetime.now().isoformat()
                }
                # Store for future
                if symbol not in historical_cache:
                    historical_cache[symbol] = []
                historical_cache[symbol].append({
                    'price': data['price'],
                    'timestamp': data['timestamp']
                })
                historical_cache[symbol] = historical_cache[symbol][-100:]
                save_historical_data(historical_cache)
                return data, status
    except:
        pass
    
    # Return stored data if available
    if symbol in historical_cache and historical_cache[symbol]:
        last_entry = historical_cache[symbol][-1]
        return {
            'price': float(last_entry['price']),
            'change': 0,
            'change_pct': 0,
            'source': 'stored',
            'timestamp': last_entry['timestamp'],
            'message': status['message']
        }, status
    
    # Fallback mock data
    seed = hash(symbol) % 1000
    random.seed(seed)
    mock_price = float(round(100 + random.uniform(0, 400), 2))
    return {
        'price': mock_price,
        'change': 0,
        'change_pct': 0,
        'source': 'fallback',
        'timestamp': datetime.now().isoformat(),
        'message': status['message']
    }, status

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/market_status')
def get_market_status():
    """Get current market status"""
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
        trend = 'uptrend'
    elif change < -1:
        trend = 'downtrend'
    else:
        trend = 'sideways'
    
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
        'trend': trend,
        'confidence': int(conf),
        'market_status': status['status'],
        'market_message': status['message'],
        'data_source': live_data['source'],
        'news': state.get('news_data', [])[:3],
        'rag_context': rag_context
    })

@app.route('/api/all_stocks')
def all_stocks():
    """Get all stocks with data"""
    tickers = stock_service.get_all_tickers()
    stocks = []
    for symbol in tickers[:50]:
        data, _ = get_live_or_stored_price(symbol)
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
        if data['change_pct'] > 0:
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
        if data['change_pct'] < 0:
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
    """Get ML prediction for a specific symbol"""
    symbol = symbol.upper()
    
    live_data, status = get_live_or_stored_price(symbol)
    
    if not live_data or live_data.get('price') == 'N/A':
        return jsonify({'error': 'Symbol not found'})
    
    current_price = float(live_data['price'])
    
    try:
        from ml_models.price_predictor import price_predictor
        
        # Generate historical prices based on current price
        historical = []
        base_price = current_price
        for i in range(30):
            change_pct = random.uniform(-0.03, 0.03)
            price = base_price * (1 + change_pct)
            historical.append(float(price))
        
        # Use last 20 for prediction
        recent_prices = [float(p) for p in historical[-20:]]
        
        # Train model
        price_predictor.train(recent_prices)
        
        # Predict next price
        next_price = price_predictor.predict_next_price(recent_prices)
        
        if next_price and next_price > 0:
            next_price = float(next_price)
            expected_return = float(((next_price - current_price) / current_price) * 100)
            
            if expected_return > 1:
                action = "BUY"
            elif expected_return < -1:
                action = "SELL"
            else:
                action = "HOLD"
            
            confidence = int(min(85, 50 + abs(expected_return) * 5))
            
            return jsonify({
                'symbol': str(symbol),
                'current_price': round(current_price, 2),
                'predicted_price': round(next_price, 2),
                'expected_return': round(expected_return, 1),
                'action': str(action),
                'confidence': confidence
            })
        else:
            return jsonify({'error': 'Could not generate prediction'})
            
    except Exception as e:
        print(f"ML Prediction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Prediction error: {str(e)}'})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 PSX Market Intelligence Server")
    print("="*50)
    print("📍 http://localhost:5000")
    print("="*50)
    app.run(debug=True, host='0.0.0.0', port=5000)