"""
Recommendation Engine - Combines all ML models
"""
import numpy as np
from .price_predictor import price_predictor
from .trend_predictor import trend_predictor
from .sentiment_analyzer import sentiment_analyzer

class RecommendationEngine:
    def __init__(self):
        self.price_predictor = price_predictor
        self.trend_predictor = trend_predictor
        self.sentiment_analyzer = sentiment_analyzer
    
    def generate_recommendation(self, symbol, current_price, historical_prices,
                                 news_text=None, rsi=None):
        
        signals = {'price': 0, 'trend': 0, 'sentiment': 0, 'technical': 0}
        
        # Price prediction
        next_price = self.price_predictor.predict_next_price(historical_prices)
        if next_price:
            change_pct = ((next_price - current_price) / current_price) * 100
            if change_pct > 2:
                signals['price'] = 2
            elif change_pct > 0.5:
                signals['price'] = 1
            elif change_pct < -2:
                signals['price'] = -2
            elif change_pct < -0.5:
                signals['price'] = -1
        
        # Trend prediction
        trend, conf = self.trend_predictor.predict_trend(historical_prices)
        if trend == 'up':
            signals['trend'] = 1
        elif trend == 'down':
            signals['trend'] = -1
        
        # Sentiment
        if news_text:
            sentiment, _ = self.sentiment_analyzer.analyze(news_text)
            if sentiment == 'positive':
                signals['sentiment'] = 1
            elif sentiment == 'negative':
                signals['sentiment'] = -1
        
        # Technical (RSI)
        if rsi:
            if rsi < 30:
                signals['technical'] = 2
            elif rsi > 70:
                signals['technical'] = -2
            elif 40 <= rsi <= 60:
                signals['technical'] = 0.5
        
        total = sum(signals.values())
        
        if total >= 3:
            action = "STRONG BUY"
            confidence = 85
        elif total >= 1.5:
            action = "BUY"
            confidence = 70
        elif total <= -3:
            action = "STRONG SELL"
            confidence = 85
        elif total <= -1.5:
            action = "SELL"
            confidence = 70
        else:
            action = "HOLD"
            confidence = 50
        
        return {
            'symbol': symbol,
            'action': action,
            'confidence': confidence,
            'signals': signals,
            'total_score': total
        }

recommendation_engine = RecommendationEngine()